import { useEffect, useState, type MouseEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, type ProductDetail as Product } from '../api'
import { useChatUi } from '../chatUi'
import HandsomeDan from '../components/HandsomeDan'

const LOW_STOCK = 5

function stockLabel(qty: number) {
  if (qty === 0) return { text: 'Sold out', cls: 'out' }
  if (qty <= LOW_STOCK) return { text: `Only ${qty} left`, cls: 'low' }
  return { text: `${qty} in stock`, cls: 'ok' }
}

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [status, setStatus] = useState<'loading' | 'ok' | 'missing' | 'error'>('loading')
  const { ask } = useChatUi()
  const [size, setSize] = useState<string | null>(null)
  const [zoom, setZoom] = useState<{ x: number; y: number } | null>(null)

  function onZoom(e: MouseEvent<HTMLDivElement>) {
    const r = e.currentTarget.getBoundingClientRect()
    setZoom({ x: ((e.clientX - r.left) / r.width) * 100, y: ((e.clientY - r.top) / r.height) * 100 })
  }

  useEffect(() => {
    window.scrollTo({ top: 0 }) // cards can be clicked from far down a grid; start the item page at the top
    setStatus('loading')
    setSize(null)
    fetchProduct(productId)
      .then((p) => {
        setProduct(p)
        setStatus('ok')
      })
      .catch((e: Error) => setStatus(e.message.startsWith('404') ? 'missing' : 'error'))
  }, [productId])

  if (status === 'loading') return <div className="container section muted">Loading…</div>
  if (status !== 'ok' || !product)
    return (
      <div className="container section">
        <h1>{status === 'missing' ? 'Product not found' : 'Something went wrong'}</h1>
        <Link to="/products">← Back to all products</Link>
      </div>
    )

  return (
    <div className="container section">
      <Link to="/products" className="back">
        ← All products
      </Link>
      <div className="detail">
        <div
          className={`detail-img ${zoom ? 'zooming' : ''}`}
          onMouseMove={onZoom}
          onMouseLeave={() => setZoom(null)}
          title="Hover to zoom"
        >
          <img
            src={product.image_url}
            alt={product.name}
            style={zoom ? { transformOrigin: `${zoom.x}% ${zoom.y}%` } : undefined}
          />
          <span className="zoom-hint">🔍 Hover to zoom</span>
        </div>

        <div className="detail-info">
          <span className="card-type">{product.garment_type}</span>
          <h1>{product.name}</h1>
          <div className="detail-price">{formatPrice(product.price)}</div>

          <p className="detail-desc">{product.description}</p>

          <h4>Colours</h4>
          <div className="chips">
            {product.colors.map((c) => (
              <span key={c} className="chip">
                {c}
              </span>
            ))}
          </div>

          <h4>Pick your size · live stock</h4>
          {/* Size picker: every size with live stock; sold-out sizes are crossed out */}
          <div className="size-picker" role="radiogroup" aria-label="Choose a size">
            {product.inventory.map((s) => {
              const label = stockLabel(s.quantity)
              return (
                <button
                  key={s.size}
                  role="radio"
                  aria-checked={size === s.size}
                  className={`size-btn ${label.cls} ${size === s.size ? 'selected' : ''}`}
                  onClick={() => setSize(s.size)}
                >
                  <span className="size-name">{s.size}</span>
                  <span className="size-stock">{s.quantity === 0 ? 'Sold out' : s.quantity <= LOW_STOCK ? `${s.quantity} left` : 'In stock'}</span>
                </button>
              )
            })}
          </div>
          {size &&
            (() => {
              const qty = product.inventory.find((s) => s.size === size)?.quantity ?? 0
              const label = stockLabel(qty)
              return (
                <div className={`size-status ${label.cls}`} aria-live="polite">
                  {qty === 0 ? (
                    <>
                      <span>
                        <b>{size}</b> is sold out.
                      </span>
                      <button className="ask-chip" onClick={() => ask(`This is sold out in ${size}. Anything similar in stock in ${size}?`)}>
                        <HandsomeDan size={18} /> Find me something similar in {size}
                      </button>
                    </>
                  ) : (
                    <span>
                      <b>{size}</b>: {label.text}
                      {qty <= LOW_STOCK && <span className="pulse-dot" aria-hidden />}
                    </span>
                  )}
                </div>
              )
            })()}
          <p className="muted small">Stock is live from our inventory database · {product.total_stock} units total</p>

          {/* Problem 9: open the chat about this exact item (the page context tells the agent which one). */}
          <div className="ask-box">
            <div>
              <strong>Questions about this {product.category}?</strong>
              <span className="muted small">Handsome Dan, our bulldog assistant, checks live sizes, prices and similar styles.</span>
            </div>
            <div className="ask-actions">
              <button className="btn btn-small btn-dan" onClick={() => ask(`About the ${product.name}: `, false)}>
                <HandsomeDan size={22} /> Ask Handsome Dan
              </button>
              <button className="ask-chip" onClick={() => ask('Is this in stock in my size? I wear ', false)}>
                Is my size in stock?
              </button>
              <button className="ask-chip" onClick={() => ask('Anything similar to this that is in stock?')}>
                Show similar items
              </button>
            </div>
          </div>

          {product.search_tags.length > 0 && (
            <div className="chips tags">
              {product.search_tags.map((t) => (
                <Link key={t} to={`/products?q=${encodeURIComponent(t)}`} className="chip chip-tag">
                  #{t}
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
