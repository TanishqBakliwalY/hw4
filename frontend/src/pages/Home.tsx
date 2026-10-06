import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, type ProductSummary } from '../api'
import ProductCard from '../components/ProductCard'
import { CATEGORIES } from '../catalog'
import GameDayHero from '../components/GameDayHero'

const FEATURED_IDS = [
  'basic-hoodie-big-yale',
  '2025-yale-vs-harvard-t-shirt',
  'champion-reverse-weave-crewneck',
  'benjamin-franklin-1-4-zip',
]

const HIGHLIGHTS = [
  { title: 'Made in New Haven', text: 'We screen print and embroider our gear in our own shop, a few minutes from campus.' },
  { title: 'Your college, your crest', text: 'Find designs for the residential colleges, varsity teams and graduate schools.' },
  { title: 'Officially licensed', text: 'Every Bulldog design we sell is approved by Yale.' },
]

export default function Home() {
  const [featured, setFeatured] = useState<ProductSummary[]>([])
  const [error, setError] = useState(false)

  useEffect(() => {
    fetchProducts()
      .then((all) => {
        const picks = FEATURED_IDS.map((id) => all.find((p) => p.product_id === id)).filter(
          (p): p is ProductSummary => Boolean(p),
        )
        setFeatured(picks.length ? picks : all.slice(0, 4))
      })
      .catch(() => setError(true))
  }, [])

  return (
    <>
      <GameDayHero />

      <section className="container highlights">
        {HIGHLIGHTS.map((h) => (
          <div key={h.title} className="highlight">
            <h3>{h.title}</h3>
            <p>{h.text}</p>
          </div>
        ))}
      </section>

      <section className="container section">
        <div className="section-head">
          <h2>Shop by category</h2>
        </div>
        <div className="category-tiles">
          {CATEGORIES.slice(0, 5).map((c) => (
            <Link key={c.value} to={`/products?category=${encodeURIComponent(c.value)}`} className="category-tile">
              {c.label}
              <span aria-hidden>→</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="container section">
        <div className="section-head">
          <h2>Fan favourites</h2>
          <Link to="/products">View all →</Link>
        </div>
        {error ? (
          <p className="muted">Couldn't load products. Is the backend running on port 8000?</p>
        ) : (
          <div className="grid">
            {featured.map((p, i) => (
              <ProductCard key={p.product_id} product={p} index={i} />
            ))}
          </div>
        )}
      </section>

      <section className="container section cta">
        <div>
          <h2>Not sure what fits?</h2>
          <p>Tap Handsome Dan in the bottom-right corner. Our bulldog assistant checks live sizes and prices for you.</p>
        </div>
      </section>
    </>
  )
}
