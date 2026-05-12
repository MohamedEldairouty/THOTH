import { useState, useRef, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'
import { sendChatMessage, sendVoiceMessage } from '../services/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
  audio_base64?: string
}

const T = {
  en: { title: 'Ask THOTH', placeholder: 'Ask me anything about the museum...', send: 'Send', welcome: 'How can I help you today?', thinking: 'THOTH is thinking...', recording: 'Listening...', error: '⚠ Connection error. Please try again.' },
  ar: { title: 'اسأل تحوت', placeholder: 'اسألني أي شيء عن المتحف...', send: 'إرسال', welcome: 'كيف يمكنني مساعدتك اليوم؟', thinking: 'تحوت يفكر...', recording: 'جاري الاستماع...', error: '⚠ خطأ في الاتصال. حاول مرة أخرى.' },
  fr: { title: 'Discuter avec THOTH', placeholder: 'Posez-moi une question sur le musée...', send: 'Envoyer', welcome: 'Comment puis-je vous aider ?', thinking: 'THOTH réfléchit...', recording: 'Écoute en cours...', error: '⚠ Erreur de connexion. Veuillez réessayer.' },
}

export default function ChatPage() {
  const { lang } = useLanguage()
  const t = T[lang]
  const [searchParams] = useSearchParams()
  const exhibitId = searchParams.get('exhibit') ? Number(searchParams.get('exhibit')) : undefined

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<number | undefined>()
  const [loading, setLoading] = useState(false)
  const [recording, setRecording] = useState(false)

  const bottomRef = useRef<HTMLDivElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Play base64 audio ──────────────────────────────────────
  const playAudio = (base64: string) => {
    const audio = new Audio(`data:audio/mp3;base64,${base64}`)
    audio.play().catch(() => {})
  }

  // ── Text send ─────────────────────────────────────────────
  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setMessages(m => [...m, { role: 'user', content: text }])
    setLoading(true)
    try {
      const res = await sendChatMessage({ message: text, session_id: sessionId, language: lang, exhibit_id: exhibitId })
      setSessionId(res.session_id)
      setMessages(m => [...m, { role: 'assistant', content: res.reply, audio_base64: res.audio_base64 ?? undefined }])
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: t.error }])
    } finally {
      setLoading(false)
    }
  }

  // ── Voice record ───────────────────────────────────────────
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      audioChunksRef.current = []
      recorder.ondataavailable = e => audioChunksRef.current.push(e.data)
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        await handleVoice(blob)
      }
      mediaRecorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch {
      alert('Microphone access denied.')
    }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  const handleVoice = async (blob: Blob) => {
    setMessages(m => [...m, { role: 'user', content: '🎤 Voice message' }])
    setLoading(true)
    try {
      const res = await sendVoiceMessage(blob, sessionId, exhibitId)
      setSessionId(res.session_id)
      const msg: Message = { role: 'assistant', content: res.reply, audio_base64: res.audio_base64 ?? undefined }
      setMessages(m => [...m, msg])
      if (res.audio_base64) playAudio(res.audio_base64)
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: t.error }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 flex flex-col h-[calc(100vh-4rem)] animate-fade-in">

      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <img src="/assets/logo.png" alt="THOTH" className="h-10 w-auto" />
        <h1 className="gem-section-title">{t.title}</h1>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-4">

        {/* Welcome state */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-4 py-12">
            <img
              src="/assets/logo.png"
              alt="THOTH"
              className="h-24 w-auto opacity-90 drop-shadow-[0_0_20px_rgba(201,168,76,0.4)] animate-shimmer"
            />
            <p className="text-gem-muted text-lg">{t.welcome}</p>
            <p className="text-gem-muted/50 text-sm">
              {lang === 'ar' ? 'اكتب سؤالك أو اضغط على الميكروفون' :
               lang === 'fr' ? 'Tapez ou utilisez le microphone' :
               'Type a question or press the microphone'}
            </p>
          </div>
        )}

        {/* Message list */}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {/* THOTH avatar */}
            {msg.role === 'assistant' && (
              <img src="/assets/logo.png" alt="THOTH" className="h-7 w-7 rounded-full mr-2 mt-1 flex-shrink-0" />
            )}
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-gem-gold text-gem-navy font-medium'
                : 'gem-card text-gem-text border-gem-gold/20'
            }`}>
              {msg.role === 'assistant' && (
                <span className="text-gem-gold text-xs font-display block mb-1">THOTH</span>
              )}
              {msg.content}

              {/* Play audio button for assistant messages */}
              {msg.role === 'assistant' && msg.audio_base64 && (
                <button
                  onClick={() => playAudio(msg.audio_base64!)}
                  className="mt-2 flex items-center gap-1 text-gem-gold/60 hover:text-gem-gold text-xs transition-colors"
                >
                  🔊 {lang === 'ar' ? 'استمع' : lang === 'fr' ? 'Écouter' : 'Play audio'}
                </button>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex items-center gap-2 justify-start">
            <img src="/assets/logo.png" alt="THOTH" className="h-7 w-7 rounded-full flex-shrink-0" />
            <div className="gem-card px-4 py-3 text-gem-muted text-sm animate-pulse">
              {recording ? t.recording : t.thinking}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="flex gap-3 items-center">
        {/* Mic button */}
        <button
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={startRecording}
          onTouchEnd={stopRecording}
          disabled={loading}
          className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${
            recording
              ? 'bg-red-500 scale-110 shadow-[0_0_16px_rgba(239,68,68,0.6)]'
              : 'bg-gem-gold/10 border border-gem-gold/40 hover:bg-gem-gold/20 text-gem-gold'
          } disabled:opacity-40`}
          title={lang === 'ar' ? 'اضغط مع الاستمرار للتسجيل' : 'Hold to record'}
        >
          {recording ? (
            <span className="w-3 h-3 rounded-full bg-white animate-pulse" />
          ) : (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 1a4 4 0 0 1 4 4v7a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4zm0 2a2 2 0 0 0-2 2v7a2 2 0 0 0 4 0V5a2 2 0 0 0-2-2zm-7 9h2a5 5 0 0 0 10 0h2a7 7 0 0 1-6 6.92V21h3v2H8v-2h3v-2.08A7 7 0 0 1 5 12z"/>
            </svg>
          )}
        </button>

        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder={t.placeholder}
          className="gem-input flex-1"
          disabled={loading || recording}
        />

        <button
          onClick={send}
          disabled={loading || !input.trim() || recording}
          className="gem-btn-primary px-5 disabled:opacity-40 flex-shrink-0"
        >
          {t.send}
        </button>
      </div>

      {recording && (
        <p className="text-center text-red-400 text-xs mt-2 animate-pulse">
          {lang === 'ar' ? '● جاري التسجيل — أفلت للإيقاف' :
           lang === 'fr' ? '● Enregistrement — relâchez pour arrêter' :
           '● Recording — release to stop'}
        </p>
      )}
    </div>
  )
}
