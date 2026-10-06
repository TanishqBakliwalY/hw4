import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useChatResults } from '../chatResults'
import ProductCard from './ProductCard'

/**
 * Renders the chat agent's product matches on the page, using the same ProductCard as the
 * Products page, so every card links to /products/:productId (the single-item page).
 * On a product page the panel collapses to a slim bar so the item itself stays front and centre.
 */
export default function ChatResultsPanel() {
  const { results, clearResults } = useChatResults()
  const { pathname } = useLocation()
  const onProductPage = pathname.startsWith('/products/')
  const [expanded, setExpanded] = useState(!onProductPage)
  const ref = useRef<HTMLElement>(null)

  // Collapse when the shopper opens a product page; expand again elsewhere.
  useEffect(() => setExpanded(!onProductPage), [onProductPage, pathname])

  // New results from the agent: expand and bring them into view. Skipped on first render, so a
  // reload restoring saved results doesn't expand the panel over a product page.
  const seenVersion = useRef(results?.version)
  useEffect(() => {
    if (!results || results.version === seenVersion.current) return
    seenVersion.current = results.version
    setExpanded(true)
    requestAnimationFrame(() => ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }, [results?.version]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!results || results.products.length === 0) return null
  const count = results.products.length

  return (
    <section
      ref={ref}
      className={`chat-results ${expanded ? '' : 'collapsed'}`}
      aria-live="polite"
      aria-label="Products from your chat"
    >
      <div className="container">
        <div className="chat-results-head">
          <div>
            <span className="eyebrow">From your chat with our assistant</span>
            <h2>
              {results.title}{' '}
              <span className="chat-results-count">
                · {count} {count === 1 ? 'item' : 'items'}
              </span>
            </h2>
          </div>
          <div className="chat-results-actions">
            <button className="btn btn-small btn-outline" onClick={() => setExpanded((e) => !e)} aria-expanded={expanded}>
              {expanded ? 'Hide' : onProductPage ? 'Back to chat results' : 'Show'}
            </button>
            <button className="link-btn" onClick={clearResults}>
              Clear
            </button>
          </div>
        </div>
        {expanded && (
          <div className="grid" key={results.version}>
            {results.products.map((p, i) => (
              <ProductCard key={p.product_id} product={p} index={i} />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
