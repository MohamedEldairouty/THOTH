import { useState, useRef, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'
import { sendChatMessage } from '../services/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatPage() {
  const { lang } = useLanguage()
  const [searchParams] = useSearchParams()
  const exhibitId = searchParams.get('exhibit') ? Number(searchParams.get('exhibit')) : undefined

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<number | undefined>()
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setMessages(m => [...m, { role: 'user', content: text }])
    setLoading(true)
    try {
      const res = await sendChatMessage({ message: text, session_id: sessionId, language: lang, exhibit_id: exhibitId })
      setSessionId(res.session_id)
      setMessages(m => [...m, { role: 'assistant', content: res.reply }])
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: '⚠ Connection error. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  const placeholder = lang === 'ar' ? 'اكتب رسالتك...' : lang === 'fr' ? 'Tapez votre message...' : 'Ask me anything about the museum...'

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 flex flex-col h-[calc(100vh-4rem)] animate-fade-in">
      <h1 className="gem-section-title mb-6">
        {lang === 'ar' ? 'اسأل تحوت' : lang === 'fr' ? 'Discuter avec THOTH' : 'Ask THOTH'}
      </h1>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-4">
        {messages.length === 0 && (
          <div className="text-center text-gem-muted py-12">
            <div className="text-5xl mb-4">𓅓</div>
            <p>{lang === 'ar' ? 'كيف يمكنني مساعدتك اليوم؟' : lang === 'fr' ? 'Comment puis-je vous aider ?' : 'How can I help you today?'}</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-gem-gold text-gem-navy font-medium'
                  : 'gem-card text-gem-text border-gem-gold/20'
              }`}
            >
              {msg.role === 'assistant' && (
                <span className="text-gem-gold text-xs font-display block mb-1">𓅓 THOTH</span>
              )}
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="gem-card px-4 py-3 text-gem-muted text-sm animate-pulse">
              𓅓 THOTH {lang === 'ar' ? 'يفكر...' : lang === 'fr' ? 'réfléchit...' : 'is thinking...'}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-3">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder={placeholder}
          className="gem-input flex-1"
          disabled={loading}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="gem-btn-primary px-5 disabled:opacity-40"
        >
          {lang === 'ar' ? 'إرسال' : lang === 'fr' ? 'Envoyer' : 'Send'}
        </button>
      </div>
    </div>
  )
}
