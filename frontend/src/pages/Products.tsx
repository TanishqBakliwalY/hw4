import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchProducts, type Category, type ProductSummary, type SortOrder } from '../api'
import { CATEGORIES } from '../catalog'
import ProductCard from '../components/ProductCard'

// Problem 9: category chips, "in stock in my size" and sort, all stored in the URL
// (e.g. /products?category=hoodie&size=M&sort=price_asc) so filtered views can be shared.
const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const SORTS: { value: SortOrder; label: string }[] = [
  { value: 'relevance', label: 'Featured' },
  { value: 'price_asc', label: 'Price: low to high' },
  { value: 'price_desc', label: 'Price: high to low' },
  { value: 'name', label: 'Name: A–Z' },
]

export default function Products() {
  const [params, setParams] = useSearchParams()
  const query = params.get('q') ?? ''
  const category = (params.get('category') as Category | null) ?? undefined
  const size = params.get('size') ?? undefined
  const sort = (params.get('sort') as SortOrder | null) ?? 'relevance'
  const [input, setInput] = useState(query)
  const [products, setProducts] = useState<ProductSummary[] | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => setInput(query), [query])

  useEffect(() => {
    setProducts(null)
    setError(false)
    fetchProducts({ q: query || undefined, category, size, sort })
      .then(setProducts)
      .catch(() => setError(true))
  }, [query, category, size, sort])

  /** Update one filter in the URL, keeping the others. Reads the browser's *current* URL (not the
   *  hook's render-time copy), so quick successive changes (chip, size, sort) build on each other
   *  instead of overwriting one another. */
  function setFilter(key: string, value: string | undefined) {
    const next = new URLSearchParams(window.location.search)
    if (value) next.set(key, value)
    else next.delete(key)
    if (key === 'sort' && value === 'relevance') next.delete('sort')
    setParams(next, { replace: key !== 'q' })
  }

  const activeFilters = [query, category, size].filter(Boolean).length + (sort !== 'relevance' ? 1 : 0)
  const categoryLabel = CATEGORIES.find((c) => c.value === category)?.label

  return (
    <div className="container section">
      <div className="page-head">
        <div>
          <h1>{categoryLabel ? `Shop ${categoryLabel}` : 'Shop Campus Customs'}</h1>
          <p className="muted">Yale apparel for game days, study days and every day in between.</p>
        </div>
        <form
          className="search"
          onSubmit={(e) => {
            e.preventDefault()
            setFilter('q', input.trim() || undefined)
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Search colleges, sports, colours…"
            aria-label="Search products"
          />
          <button className="btn" type="submit">
            Search
          </button>
        </form>
      </div>

      <div className="filters" role="group" aria-label="Filter products">
        <div className="chips-row" role="radiogroup" aria-label="Category">
          <button
            className={`filter-chip ${!category ? 'active' : ''}`}
            role="radio"
            aria-checked={!category}
            onClick={() => setFilter('category', undefined)}
          >
            All
          </button>
          {CATEGORIES.map((c) => (
            <button
              key={c.value}
              className={`filter-chip ${category === c.value ? 'active' : ''}`}
              role="radio"
              aria-checked={category === c.value}
              onClick={() => setFilter('category', category === c.value ? undefined : c.value)}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="filter-controls">
          <label>
            In stock in
            <select value={size ?? ''} onChange={(e) => setFilter('size', e.target.value || undefined)}>
              <option value="">Any size</option>
              {SIZES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label>
            Sort by
            <select value={sort} onChange={(e) => setFilter('sort', e.target.value)}>
              {SORTS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          {activeFilters > 0 && (
            <button
              className="link-btn"
              onClick={() => {
                setInput('')
                setParams({})
              }}
            >
              Clear all filters
            </button>
          )}
        </div>
      </div>

      {error && <p className="muted">Couldn't load products. Is the backend running on port 8000?</p>}
      {!error && products === null && <p className="muted">Loading products…</p>}
      {products && (
        <>
          <p className="result-count">
            {products.length} {products.length === 1 ? 'item' : 'items'}
            {categoryLabel && <> · {categoryLabel}</>}
            {query && <> · matching “{query}”</>}
            {size && <> · in stock in {size}</>}
          </p>
          {products.length === 0 ? (
            <div className="empty-state">
              <p>No products match these filters.</p>
              <p className="muted">
                Try another size or category, or ask our assistant (bottom-right) to find something similar.
              </p>
            </div>
          ) : (
            <div className="grid">
              {products.map((p, i) => (
                <ProductCard key={p.product_id} product={p} index={i} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
