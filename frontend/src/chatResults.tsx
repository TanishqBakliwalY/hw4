import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import type { PageMatches } from './api'

/**
 * Products the chat agent found, shared between the ChatWidget (which receives them from
 * POST /api/chat) and the ChatResultsPanel (which renders them on the page).
 * Kept in sessionStorage so the cards survive navigating to a product page and reloads.
 */
export interface ChatResults extends PageMatches {
  /** Bumps on every new result set so the panel can scroll into view / animate. */
  version: number
}

interface ChatResultsState {
  results: ChatResults | null
  showResults: (matches: PageMatches) => void
  clearResults: () => void
}

const STORAGE_KEY = 'cc_chat_results'
const ChatResultsContext = createContext<ChatResultsState | null>(null)

function load(): ChatResults | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as ChatResults) : null
  } catch {
    return null
  }
}

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatResults | null>(load)

  useEffect(() => {
    if (results) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(results))
    else sessionStorage.removeItem(STORAGE_KEY)
  }, [results])

  const showResults = useCallback(
    (matches: PageMatches) => setResults((prev) => ({ ...matches, version: (prev?.version ?? 0) + 1 })),
    [],
  )
  const clearResults = useCallback(() => setResults(null), [])

  return (
    <ChatResultsContext.Provider value={{ results, showResults, clearResults }}>{children}</ChatResultsContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
