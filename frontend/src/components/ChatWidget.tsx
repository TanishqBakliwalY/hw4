import { useEffect, useRef, useState, type FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import { matchPath, useLocation } from 'react-router-dom'
import { clearChatHistory, fetchChatHistory, sendChatMessage, type ChatMessage, type PageContext } from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'
import { useChatUi } from '../chatUi'
import HandsomeDan from './HandsomeDan'

const PAGE_TYPES: Record<string, PageContext['page_type']> = {
  '/': 'home',
  '/products': 'products',
  '/about': 'about',
  '/login': 'login',
  '/create-account': 'create-account',
}

/** Describes the page the shopper is on, sent with every message so "this" can be resolved. */
function usePageContext(resultsTitle?: string): PageContext {
  const { pathname, search } = useLocation()
  const product = matchPath('/products/:productId', pathname)
  return {
    path: pathname,
    page_type: product ? 'product' : (PAGE_TYPES[pathname] ?? 'other'),
    product_id: product?.params.productId ?? null,
    search_query: pathname === '/products' ? new URLSearchParams(search).get('q') : null,
    chat_results_title: resultsTitle ?? null,
  }
}

const greeting = (name?: string): ChatMessage => ({
  role: 'assistant',
  content: `Woof${name ? `, ${name}` : ''}! I'm **Handsome Dan**, Yale's bulldog and your Campus Customs shopping buddy. Ask me about hoodies, sizes, prices or game-day gear.`,
})

// Problem 9: one-tap starter questions. On a product page they're about that item.
const GENERAL_STARTERS = [
  'What hoodies do you have?',
  'Gift ideas under $40',
  'Show me residential college gear',
  "What's in stock in XL?",
]
const PRODUCT_STARTERS = ['Is this in stock in M?', 'What colours does this come in?', 'Anything similar in stock?']

const BLOCKED_NOTE = '🔒 Message hidden: it looked like it contained private information, so it was not sent or saved.'

export default function ChatWidget() {
  const { user } = useAuth()
  const { results, showResults } = useChatResults()
  const { open, setOpen, pending, consumePending } = useChatUi()
  const page = usePageContext(results?.title)
  // The greeting is UI-only; it's not sent to the agent as history.
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  // Dan "peeks" with a speech bubble once per browser session, a few seconds after arriving.
  const [peek, setPeek] = useState(false)
  useEffect(() => {
    if (sessionStorage.getItem('cc_dan_peeked')) return
    const t = window.setTimeout(() => {
      setPeek(true)
      sessionStorage.setItem('cc_dan_peeked', '1')
    }, 4000)
    return () => window.clearTimeout(t)
  }, [])
  useEffect(() => {
    if (open) setPeek(false)
  }, [open])

  // Logged in: reload the conversation saved to the account. Guest: start fresh (nothing is saved).
  useEffect(() => {
    setMessages([])
    if (!user) return
    let cancelled = false
    setLoadingHistory(true)
    fetchChatHistory()
      .then((h) => !cancelled && setMessages(h))
      .catch(() => {})
      .finally(() => !cancelled && setLoadingHistory(false))
    return () => {
      cancelled = true
    }
  }, [user?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  async function startNewChat() {
    if (user && !window.confirm('Start a new chat? This deletes your saved chat history.')) return
    if (user) await clearChatHistory().catch(() => {})
    setMessages([])
  }

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending, open])

  async function send(raw: string) {
    const text = raw.trim()
    if (!text || sending) return
    const history = messages
    setMessages([...history, { role: 'user', content: text }])
    setInput('')
    setSending(true)
    try {
      const reply = await sendChatMessage(text, history, page)
      setMessages((m) => {
        // Guardrail: the server refused a message with card/password/ID data, so hide it on screen
        // too (and so it isn't re-sent as guest history).
        const kept = reply.blocked
          ? m.map((msg, i) => (i === m.length - 1 && msg.role === 'user' ? { ...msg, content: BLOCKED_NOTE } : msg))
          : m
        return [...kept, reply]
      })
      // API contract: product matches from the agent are rendered as cards on the page.
      if (reply.matches) showResults(reply.matches)
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: (err as Error).message || 'Sorry, something went wrong. Please try again.' },
      ])
    } finally {
      setSending(false)
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    void send(input)
  }

  // "Ask about this item" (and similar buttons elsewhere): send now, or pre-fill and focus the input.
  useEffect(() => {
    if (!pending || loadingHistory || sending) return
    consumePending()
    if (pending.send) void send(pending.text)
    else {
      setInput(pending.text)
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [pending, loadingHistory, sending]) // eslint-disable-line react-hooks/exhaustive-deps

  const shown = [greeting(user?.first_name), ...messages]
  const onProductPage = page.page_type === 'product'
  const starters = onProductPage ? PRODUCT_STARTERS : GENERAL_STARTERS
  const showStarters = !sending && !loadingHistory && (messages.length === 0 || onProductPage)

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Campus Customs chat">
          <header className="chat-header">
            <div className="chat-ident">
              <HandsomeDan size={44} className="chat-header-dan" />
              <div>
                <strong>Handsome Dan</strong>
                <small>
                  <span className="online-dot" aria-hidden /> Campus Customs bulldog ·{' '}
                  {user ? `saved to ${user.first_name}'s account` : 'guest chat'}
                </small>
              </div>
            </div>
            <div className="chat-header-actions">
              {messages.length > 0 && (
                <button className="chat-new" onClick={startNewChat} title="Start a new chat">
                  New chat
                </button>
              )}
              <button className="chat-close" aria-label="Close chat" onClick={() => setOpen(false)}>
                ×
              </button>
            </div>
          </header>

          <div className="chat-messages" ref={listRef}>
            {loadingHistory && <p className="chat-note">Loading your saved chat…</p>}
            {shown.map((m, i) => (
              <div key={i} className={`chat-turn ${m.role}`}>
                <div className="bubble-row">
                  {m.role === 'assistant' && <HandsomeDan size={28} className="bubble-dan" />}
                  <div className={`bubble ${m.role}`}>
                    {m.role === 'assistant' ? <ReactMarkdown>{m.content}</ReactMarkdown> : m.content}
                  </div>
                </div>
                {m.matches && (
                  <button className="chat-matches-chip" onClick={() => showResults(m.matches!)}>
                    🛍️ Showing {m.matches.products.length} on the page: {m.matches.title}
                  </button>
                )}
              </div>
            ))}
            {sending && (
              <div className="bubble-row">
                <HandsomeDan size={28} className="bubble-dan" />
                <div className="bubble assistant typing paws" aria-label="Handsome Dan is sniffing out an answer">
                  <span>🐾</span>
                  <span>🐾</span>
                  <span>🐾</span>
                </div>
              </div>
            )}
          </div>

          {showStarters && (
            <div className="chat-starters" aria-label="Suggested questions">
              {onProductPage && <span className="chat-starters-label">Ask Dan about this item:</span>}
              {starters.map((q) => (
                <button key={q} className="starter-chip" onClick={() => void send(q)}>
                  {q}
                </button>
              ))}
            </div>
          )}

          <form className="chat-input" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={onProductPage ? 'Ask Dan about this item…' : 'Ask Handsome Dan anything…'}
              aria-label="Chat message"
              maxLength={2000}
              autoFocus
            />
            <button type="submit" className="btn" disabled={!input.trim() || sending}>
              Send
            </button>
          </form>
        </section>
      )}

      {peek && !open && (
        <div className="dan-peek" role="status">
          <button className="dan-peek-close" aria-label="Dismiss" onClick={() => setPeek(false)}>
            ×
          </button>
          <b>Woof!</b> Need help finding your size? I can check live stock.
        </div>
      )}
      <button
        className={`chat-launcher ${open ? 'is-open' : 'dan-launcher'}`}
        aria-label={open ? 'Close chat' : 'Chat with Handsome Dan'}
        onClick={() => setOpen((o) => !o)}
      >
        {open ? '×' : <HandsomeDan size={60} />}
      </button>
    </div>
  )
}
