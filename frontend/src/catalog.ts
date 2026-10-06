import type { Category } from './api'

/** Shopper-facing labels for the backend's normalized categories (tools.category_of). */
export const CATEGORIES: { value: Category; label: string }[] = [
  { value: 'hoodie', label: 'Hoodies' },
  { value: 't-shirt', label: 'T-shirts' },
  { value: 'crewneck', label: 'Crewnecks' },
  { value: 'quarter-zip', label: 'Quarter-zips' },
  { value: 'jacket', label: 'Jackets' },
  { value: 'long-sleeve shirt', label: 'Long sleeve' },
  { value: 'mockneck', label: 'Mocknecks' },
]
