import { Link } from 'react-router-dom'
import { formatPrice, type ProductSummary } from '../api'
import { useReveal } from '../useReveal'

const ALL_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

function shortDescription(text: string, max = 95) {
  if (text.length <= max) return text
  return text.slice(0, text.lastIndexOf(' ', max)) + '…'
}

/** Availability badge from live stock: sold out, or only a couple of sizes left. */
function badge(p: ProductSummary) {
  if (p.total_stock === 0) return { text: 'Sold out', cls: 'badge-out' }
  if (p.sizes_in_stock.length <= 2) return { text: `Only ${p.sizes_in_stock.join(' & ')} left`, cls: 'badge-low' }
  return null
}

export default function ProductCard({ product, index = 0 }: { product: ProductSummary; index?: number }) {
  const { ref, shown } = useReveal<HTMLAnchorElement>()
  const b = badge(product)
  return (
    <Link
      ref={ref}
      to={`/products/${product.product_id}`}
      className={`card reveal ${shown ? 'revealed' : ''}`}
      style={{ ['--i' as string]: index % 8 }}
    >
      <div className="card-img">
        {b && <span className={`card-badge ${b.cls}`}>{b.text}</span>}
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {/* Hover/focus reveal: which sizes are in stock right now */}
        <div className="card-sizes" aria-label="Sizes in stock">
          {ALL_SIZES.map((s) => (
            <span key={s} className={product.sizes_in_stock.includes(s) ? 'in' : 'out'}>
              {s}
            </span>
          ))}
        </div>
      </div>
      <div className="card-body">
        <span className="card-type">{product.garment_type}</span>
        <h3 className="card-title">{product.name}</h3>
        <p className="card-desc">{shortDescription(product.description)}</p>
        <div className="card-foot">
          <span className="card-price">{formatPrice(product.price)}</span>
          <span className="card-cta">View →</span>
        </div>
      </div>
    </Link>
  )
}
