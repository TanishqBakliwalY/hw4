import { useEffect, useRef, useState } from 'react'

/** Adds a one-time "revealed" state when the element scrolls into view (staggered card fade-in). */
export function useReveal<T extends Element>() {
  const ref = useRef<T>(null)
  const [shown, setShown] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el || shown) return
    if (!('IntersectionObserver' in window)) {
      setShown(true)
      return
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true)
          io.disconnect()
        }
      },
      { rootMargin: '0px 0px -40px 0px' },
    )
    io.observe(el)
    // Safety net: never leave a product hidden if the observer doesn't fire (e.g. print, odd layouts).
    const fallback = window.setTimeout(() => setShown(true), 1500)
    return () => {
      io.disconnect()
      window.clearTimeout(fallback)
    }
  }, [shown])
  return { ref, shown }
}
