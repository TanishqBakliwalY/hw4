// Thin client for the FastAPI backend (backend/main.py).
// In dev, Vite proxies /api and /images to http://127.0.0.1:8000.

export interface SizeStock {
  size: string
  quantity: number
}

export type Category = 't-shirt' | 'long-sleeve shirt' | 'crewneck' | 'mockneck' | 'hoodie' | 'quarter-zip' | 'jacket'

export interface ProductSummary {
  product_id: string
  name: string
  garment_type: string
  category: Category
  description: string
  colors: string[]
  price: number
  image_url: string
  total_stock: number
  sizes_in_stock: string[]
}

export interface ProductDetail extends ProductSummary {
  search_tags: string[]
  inventory: SizeStock[]
}

/** Products the agent matched, rebuilt from live DB rows by the API, to be shown on the page. */
export interface PageMatches {
  title: string
  products: ProductSummary[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  /** Product matches attached to an assistant reply. */
  matches?: PageMatches | null
  /** Set when the input guardrail refused the shopper's message (never sent to the model or saved). */
  blocked?: 'card' | 'password' | 'ssn' | null
}

/** Where the shopper is when they send a message (backend models.PageContext). */
export interface PageContext {
  path: string
  page_type: 'home' | 'products' | 'product' | 'about' | 'login' | 'create-account' | 'other'
  product_id?: string | null
  search_query?: string | null
  chat_results_title?: string | null
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export type SortOrder = 'relevance' | 'name' | 'price_asc' | 'price_desc'

export interface ProductFilters {
  q?: string
  category?: Category
  size?: string
  sort?: SortOrder
}

/** GET /api/products with optional search, category, in-stock size and sort (all server-side). */
export function fetchProducts(filters: ProductFilters = {}): Promise<ProductSummary[]> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value)
  const qs = params.toString()
  return getJson<ProductSummary[]>(`/api/products${qs ? `?${qs}` : ''}`)
}

export function fetchProduct(productId: string): Promise<ProductDetail> {
  return getJson<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`)
}

// ---------- auth ----------

export interface User {
  id: number
  first_name: string
  last_name: string
  name: string
  email: string
}

export interface RegisterInput {
  first_name: string
  last_name: string
  email: string
  password: string
}

/** Turns FastAPI error bodies ({detail: string | [{msg}]}) into one readable message. */
async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail))
      return body.detail.map((d: { msg: string }) => d.msg.replace(/^Value error, /, '')).join(' ')
  } catch {
    /* fall through */
  }
  return `Request failed (${res.status})`
}

async function postJson<T>(url: string, data?: unknown): Promise<T> {
  // The session lives in an HttpOnly cookie, so the browser sends it automatically (same origin via the Vite proxy).
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: data === undefined ? undefined : JSON.stringify(data),
  })
  if (!res.ok) throw new Error(await errorMessage(res))
  return (res.status === 204 ? undefined : await res.json()) as T
}

export const register = (input: RegisterInput) => postJson<User>('/api/auth/register', input)
export const login = (email: string, password: string) => postJson<User>('/api/auth/login', { email, password })
export const logout = () => postJson<void>('/api/auth/logout')

export async function fetchMe(): Promise<User | null> {
  const res = await fetch('/api/auth/me')
  return res.ok ? ((await res.json()) as User) : null
}

// ---------- chat ----------

/** POST /api/chat response (backend models.ChatResponse). */
interface ChatResponse {
  reply: string
  matches: PageMatches | null
  /** True when the turn was saved to the logged-in shopper's history. */
  saved: boolean
  blocked: 'card' | 'password' | 'ssn' | null
}

const MAX_HISTORY = 20

/**
 * Sends the shopper's message, the page they're on, and (for guests) recent prior turns to the
 * agent (POST /api/chat). The session cookie goes along automatically; for logged-in shoppers the
 * server ignores `history` and uses the conversation saved in the database instead.
 */
export async function sendChatMessage(message: string, history: ChatMessage[], page: PageContext): Promise<ChatMessage> {
  const res = await postJson<ChatResponse>('/api/chat', {
    message,
    page,
    history: history.slice(-MAX_HISTORY).map(({ role, content, matches }) => ({
      role,
      content,
      product_ids: matches?.products.map((p) => p.product_id) ?? [],
    })),
  })
  return { role: 'assistant', content: res.reply, matches: res.matches, blocked: res.blocked }
}

/** Saved conversation for the logged-in shopper (empty for guests). */
export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const rows = await getJson<{ role: 'user' | 'assistant'; content: string; matches: PageMatches | null }[]>(
    '/api/chat/history',
  )
  return rows.map(({ role, content, matches }) => ({ role, content, matches }))
}

export async function clearChatHistory(): Promise<void> {
  const res = await fetch('/api/chat/history', { method: 'DELETE' })
  if (!res.ok) throw new Error(await errorMessage(res))
}

export const formatPrice = (price: number) =>
  price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
