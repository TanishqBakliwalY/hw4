import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'

/**
 * Lets any page open the chat panel and hand it a question (Problem 9 "Ask about this item").
 * The ChatWidget owns the conversation; this context only carries open/closed state and a
 * pending request, which the widget picks up and either sends or puts in the input box.
 */
export interface ChatRequestIntent {
  text: string
  /** true = send immediately; false = pre-fill the input so the shopper can finish typing. */
  send: boolean
  id: number
}

interface ChatUiState {
  open: boolean
  setOpen: (open: boolean | ((o: boolean) => boolean)) => void
  pending: ChatRequestIntent | null
  /** Open the chat and send (or pre-fill) a message. */
  ask: (text: string, send?: boolean) => void
  consumePending: () => void
}

const ChatUiContext = createContext<ChatUiState | null>(null)

export function ChatUiProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState<ChatRequestIntent | null>(null)

  const ask = useCallback((text: string, send = true) => {
    setOpen(true)
    setPending({ text, send, id: Date.now() })
  }, [])
  const consumePending = useCallback(() => setPending(null), [])

  return (
    <ChatUiContext.Provider value={{ open, setOpen, pending, ask, consumePending }}>{children}</ChatUiContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatUi(): ChatUiState {
  const ctx = useContext(ChatUiContext)
  if (!ctx) throw new Error('useChatUi must be used inside <ChatUiProvider>')
  return ctx
}
