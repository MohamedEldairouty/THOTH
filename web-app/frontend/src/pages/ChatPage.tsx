import { useState, useRef, useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'
import { sendChatMessage, sendVoiceMessage, getExhibit, ttsSay } from '../services/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
  audio_base64?: string
}

const T = {
  en: {
    title: 'Ask THOTH',
    placeholder: 'Ask me anything about the museum...',
    send: 'Send',
    welcome: 'How can I help you today?',
    thinking: 'THOTH is thinking...',
    recording: 'Listening...',
    error: '⚠ Connection error. Please try again.',
    feelFree: 'Feel free to ask me anything about {name}.',
    feelFreeGeneral: "Hi there! I'm THOTH, your friendly tour guide at the Grand Egyptian Museum. Feel free to ask me anything about our exhibits or ancient Egyptian history — I'd love to help!",
    backTour: '← Back to tour',
    backExhibit: '← Back to exhibit',
    backExhibits: '← Back to exhibits',
  },
  ar: {
    title: 'اسأل تحوت',
    placeholder: 'اسألني أي شيء عن المتحف...',
    send: 'إرسال',
    welcome: 'كيف يمكنني مساعدتك اليوم؟',
    thinking: 'تحوت يفكر...',
    recording: 'جاري الاستماع...',
    error: '⚠ خطأ في الاتصال. حاول مرة أخرى.',
    feelFree: 'لا تتردد في سؤالي عن أي شيء يخص {name}.',
    feelFreeGeneral: 'مرحباً! أنا تحوت، مرشدك الودود في المتحف المصري الكبير. لا تتردد في سؤالي عن أي معروض أو عن تاريخ مصر القديمة — سيسعدني مساعدتك!',
    backTour: '← العودة إلى الجولة',
    backExhibit: '← العودة إلى المعروض',
    backExhibits: '← العودة إلى المعروضات',
  },
  fr: {
    title: 'Discuter avec THOTH',
    placeholder: 'Posez-moi une question sur le musée...',
    send: 'Envoyer',
    welcome: 'Comment puis-je vous aider ?',
    thinking: 'THOTH réfléchit...',
    recording: 'Écoute en cours...',
    error: '⚠ Erreur de connexion. Veuillez réessayer.',
    feelFree: 'N\'hésitez pas à me poser toutes vos questions sur {name}.',
    feelFreeGeneral: "Bonjour ! Je suis THOTH, votre guide au Grand Musée Égyptien. N'hésitez pas à me poser vos questions sur nos expositions ou sur l'histoire de l'Égypte ancienne — je serai ravi de vous aider !",
    backTour: '← Retour à la visite',
    backExhibit: '← Retour à l\'exposition',
    backExhibits: '← Retour aux expositions',
  },
}

export default function ChatPage() {
  const { lang } = useLanguage()
  const t = T[lang]
  const [searchParams] = useSearchParams()
  const exhibitId = searchParams.get('exhibit') ? Number(searchParams.get('exhibit')) : undefined
  const returnTo = searchParams.get('returnTo') ?? null   // "tour" | null

  // Where the back button goes + what it says
  const backLink =
    returnTo === 'tour'
      ? { to: '/tour/run', label: t.backTour }
    : exhibitId != null
      ? { to: `/exhibits/${exhibitId}`, label: t.backExhibit }
      : { to: '/exhibits', label: t.backExhibits }

  const [exhibitTitle, setExhibitTitle] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<number | undefined>()
  const [loading, setLoading] = useState(false)
  const [recording, setRecording] = useState(false)

  // ── Auto-greeting on first load when an exhibit is in context ────────
  useEffect(() => {
    setMessages([])           // clear when lang or exhibit changes
    setSessionId(undefined)
    setExhibitTitle(null)
    let alive = true
    ;(async () => {
      try {
        let greeting: string
        if (exhibitId != null) {
          const ex = await getExhibit(exhibitId, lang)
          if (!alive) return
          setExhibitTitle(ex.title)
          greeting = t.feelFree.replace('{name}', ex.title)
        } else {
          greeting = t.feelFreeGeneral
        }
        // Generate TTS for the greeting (fire and forget — text is shown
        // immediately; audio attaches when ready)
        const tts = await ttsSay(greeting, lang).catch(() => null)
        if (!alive) return
        setMessages([{
          role: 'assistant',
          content: greeting,
          audio_base64: tts?.audio_base64 ?? undefined,
        }])
        // Auto-play
        if (tts?.audio_base64) {
          setTimeout(() => togglePlay(0, tts.audio_base64!), 50)
        }
      } catch { /* ignore */ }
    })()
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exhibitId, lang])

  const bottomRef = useRef<HTMLDivElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  // ── Audio playback state (one shared player) ───────────────
  const audioRef = useRef<HTMLAudioElement | null>(null)
  // Track which message index is currently the active audio, and if paused
  const [audio, setAudio] = useState<{ idx: number; paused: boolean } | null>(null)

  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.src = ''
      audioRef.current = null
    }
    setAudio(null)
  }

  const togglePlay = (idx: number, base64: string) => {
    // Same message — toggle pause/resume against the actual element
    if (audio?.idx === idx && audioRef.current) {
      if (audioRef.current.paused) audioRef.current.play().catch(() => {})
      else audioRef.current.pause()
      return
    }
    // Different message — stop current, start new
    stopAudio()
    const el = new Audio(`data:audio/mp3;base64,${base64}`)
    // Bind the play/pause state to the actual audio element so the button
    // icon always reflects reality (fixes the "reversed" play/pause bug).
    el.onplay  = () => setAudio({ idx, paused: false })
    el.onpause = () => setAudio({ idx, paused: true })
    el.onended = () => { audioRef.current = null; setAudio(null) }
    audioRef.current = el
    setAudio({ idx, paused: true })   // start as paused; onplay flips to playing
    el.play().catch(() => setAudio({ idx, paused: true }))
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-stop audio on unmount / page leave
  useEffect(() => {
    const handler = () => stopAudio()
    window.addEventListener('beforeunload', handler)
    return () => {
      window.removeEventListener('beforeunload', handler)
      stopAudio()
    }
  }, [])

  // ── Text send ─────────────────────────────────────────────
  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    stopAudio()                       // stop any currently-playing audio
    setInput('')
    setMessages(m => [...m, { role: 'user', content: text }])
    setLoading(true)
    try {
      const res = await sendChatMessage({ message: text, session_id: sessionId, language: lang, exhibit_id: exhibitId })
      setSessionId(res.session_id)
      setMessages(m => {
        const next = [...m, { role: 'assistant' as const, content: res.reply, audio_base64: res.audio_base64 ?? undefined }]
        // Auto-play the new TTS reply
        if (res.audio_base64) {
          // Defer so the message list has rendered
          setTimeout(() => togglePlay(next.length - 1, res.audio_base64!), 0)
        }
        return next
      })
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: t.error }])
    } finally {
      setLoading(false)
    }
  }

  // ── Voice record ───────────────────────────────────────────
  // Track when recording started so we can enforce a minimum duration
  const recordStartRef = useRef<number>(0)

  const startRecording = async () => {
    console.log('[mic] startRecording called')
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setMessages(m => [...m, { role: 'assistant', content: '⚠ Your browser does not support microphone access. Use Chrome, Edge or Firefox on localhost/HTTPS.' }])
        return
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      console.log('[mic] got stream')

      // Pick the first supported mime type — Chrome/Edge support opus, Safari uses mp4
      const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', '']
      const mimeType = candidates.find(t => !t || MediaRecorder.isTypeSupported(t)) || ''
      console.log('[mic] using mimeType:', mimeType || 'browser default')

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      audioChunksRef.current = []

      recorder.ondataavailable = e => {
        if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(audioChunksRef.current, { type: mimeType || 'audio/webm' })
        const duration = Date.now() - recordStartRef.current
        console.log(`[mic] stopped — duration=${duration}ms, size=${blob.size}`)

        if (duration < 500 || blob.size < 2000) {
          setMessages(m => [...m, { role: 'assistant', content: lang === 'ar' ? 'التسجيل قصير جداً. حاول مرة أخرى.' : lang === 'fr' ? 'Enregistrement trop court. Réessayez.' : 'Recording too short. Please speak for at least 1 second.' }])
          return
        }
        await handleVoice(blob)
      }
      recorder.onerror = (e: Event) => {
        console.error('[mic] recorder error:', e)
        setMessages(m => [...m, { role: 'assistant', content: '⚠ Recording error. Check console.' }])
      }

      mediaRecorderRef.current = recorder
      recorder.start(250)
      recordStartRef.current = Date.now()
      setRecording(true)
      console.log('[mic] recording started')
    } catch (err: any) {
      console.error('[mic] getUserMedia error:', err)
      const reason = err?.name || err?.message || 'Unknown'
      setMessages(m => [...m, { role: 'assistant', content: `⚠ Microphone access failed: ${reason}. Click the lock icon in the address bar and allow microphone, then refresh.` }])
    }
  }

  const stopRecording = () => {
    console.log('[mic] stopRecording called, state:', mediaRecorderRef.current?.state)
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop()
      }
    } catch (e) {
      console.error('[mic] stop error:', e)
    }
    setRecording(false)
  }

  const handleVoice = async (blob: Blob) => {
    stopAudio()                       // stop any currently-playing audio
    setMessages(m => [...m, { role: 'user', content: '🎤 Voice message' }])
    setLoading(true)
    try {
      const res = await sendVoiceMessage(blob, sessionId, exhibitId)
      setSessionId(res.session_id)
      const reply = res.reply || (lang === 'ar' ? 'لم أسمع شيئاً، حاول مرة أخرى.' : lang === 'fr' ? 'Je n\'ai rien entendu, réessayez.' : "I didn't catch that, please try again.")
      const msg: Message = { role: 'assistant', content: reply, audio_base64: res.audio_base64 ?? undefined }
      setMessages(m => {
        const next = [...m, msg]
        if (res.audio_base64) {
          setTimeout(() => togglePlay(next.length - 1, res.audio_base64!), 0)
        }
        return next
      })
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: t.error }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 flex flex-col h-[calc(100vh-4rem)] animate-fade-in">

      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <img src="/assets/logo.png" alt="THOTH" className="h-10 w-auto" />
        <h1 className="gem-section-title">{t.title}</h1>
        {exhibitTitle && (
          <span className="text-gem-muted text-xs italic ml-2">· {exhibitTitle}</span>
        )}
      </div>

      {/* Back button — destination depends on where the user came from */}
      <div className="mb-4">
        <Link to={backLink.to} className="text-gem-gold/70 hover:text-gem-gold text-xs inline-block transition-colors">
          {backLink.label}
        </Link>
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

              {/* Play / pause audio button for assistant messages */}
              {msg.role === 'assistant' && msg.audio_base64 && (() => {
                const isActive = audio?.idx === i
                const isPlaying = isActive && !audio!.paused
                const isPaused = isActive && audio!.paused
                const label = isPlaying
                  ? (lang === 'ar' ? 'إيقاف مؤقت' : lang === 'fr' ? 'Pause' : 'Pause')
                  : isPaused
                    ? (lang === 'ar' ? 'متابعة' : lang === 'fr' ? 'Reprendre' : 'Resume')
                    : (lang === 'ar' ? 'استمع' : lang === 'fr' ? 'Écouter' : 'Play')
                return (
                  <button
                    onClick={() => togglePlay(i, msg.audio_base64!)}
                    className="mt-2 inline-flex items-center gap-1.5 text-gem-gold/70 hover:text-gem-gold text-xs transition-colors"
                  >
                    {isPlaying ? (
                      <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>
                    ) : (
                      <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                    )}
                    {label}
                  </button>
                )
              })()}
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
        {/* Mic button — click to toggle */}
        <button
          type="button"
          onClick={recording ? stopRecording : startRecording}
          disabled={loading}
          className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${
            recording
              ? 'bg-red-500 scale-110 shadow-[0_0_16px_rgba(239,68,68,0.6)]'
              : 'bg-gem-gold/10 border border-gem-gold/40 hover:bg-gem-gold/20 text-gem-gold'
          } disabled:opacity-40`}
          title={recording ? 'Click to stop' : 'Click to start recording'}
          aria-label={recording ? 'Stop recording' : 'Start recording'}
        >
          {recording ? (
            <span className="w-3 h-3 rounded-sm bg-white" />
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
          {lang === 'ar' ? '● جاري التسجيل — اضغط مرة أخرى للإيقاف' :
           lang === 'fr' ? '● Enregistrement — cliquez pour arrêter' :
           '● Recording — click the mic again to stop'}
        </p>
      )}
    </div>
  )
}
