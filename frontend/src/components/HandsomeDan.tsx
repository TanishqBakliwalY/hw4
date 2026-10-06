import { useId } from 'react'

/**
 * Original illustration of Handsome Dan, Yale's bulldog mascot, drawn as inline SVG
 * (no photo, so no image-rights issues; scales crisply from 24px to hero size).
 * Decorative by default (hidden from screen readers, since nearby text names Dan);
 * pass `label` when the illustration stands alone.
 */
export default function HandsomeDan({ size = 40, className = '', label }: { size?: number; className?: string; label?: string }) {
  const clip = useId()
  return (
    <svg
      viewBox="0 0 120 120"
      width={size}
      height={size}
      className={`dan ${className}`}
      {...(label ? { role: 'img', 'aria-label': label } : { 'aria-hidden': true, focusable: false })}
    >
      <defs>
        <clipPath id={clip}>
          <circle cx="60" cy="60" r="60" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clip})`}>
        <circle cx="60" cy="60" r="60" fill="#dbe6f3" />
        {/* collar + gold "Y" tag */}
        <path d="M18 100 Q60 122 102 100 L104 120 L16 120Z" fill="#00356b" />
        {/* ears */}
        <path d="M22 44 Q10 22 30 22 Q42 26 40 40Z" fill="#a8774b" />
        <path d="M98 44 Q110 22 90 22 Q78 26 80 40Z" fill="#a8774b" />
        {/* jowly head */}
        <path d="M20 62 Q20 26 60 26 Q100 26 100 62 Q102 96 60 100 Q18 96 20 62Z" fill="#f6f0e6" />
        {/* fawn eye patch */}
        <path d="M28 46 Q36 34 52 42 Q55 58 42 63 Q28 61 28 46Z" fill="#dcb48c" />
        {/* brow wrinkles */}
        <path d="M46 36 Q60 31 74 36" stroke="#cdbca4" strokeWidth="2.2" fill="none" strokeLinecap="round" />
        <path d="M50 42 Q60 39 70 42" stroke="#cdbca4" strokeWidth="2" fill="none" strokeLinecap="round" />
        {/* eyes */}
        <circle cx="43" cy="54" r="5.2" fill="#1f1f22" />
        <circle cx="77" cy="54" r="5.2" fill="#1f1f22" />
        <circle cx="44.8" cy="52.3" r="1.6" fill="#fff" />
        <circle cx="78.8" cy="52.3" r="1.6" fill="#fff" />
        {/* muzzle */}
        <ellipse cx="60" cy="78" rx="27" ry="16" fill="#fffaf3" />
        {/* nose */}
        <path d="M50 64 Q60 59 70 64 Q69 72 60 73 Q51 72 50 64Z" fill="#2a2a2e" />
        <ellipse cx="56" cy="64.5" rx="2.4" ry="1.2" fill="#56565c" />
        {/* mouth + jowls */}
        <path d="M60 73 L60 79" stroke="#2a2a2e" strokeWidth="2.2" strokeLinecap="round" />
        <path d="M60 79 Q49 87 38 80" stroke="#2a2a2e" strokeWidth="2.2" fill="none" strokeLinecap="round" />
        <path d="M60 79 Q71 87 82 80" stroke="#2a2a2e" strokeWidth="2.2" fill="none" strokeLinecap="round" />
        {/* classic bulldog underbite with two little teeth */}
        <path d="M47 86 Q60 96 73 86 Q60 91 47 86Z" fill="#d98b8b" />
        <path d="M50.5 87 l2 -5 l2 5Z" fill="#fff" />
        <path d="M65.5 87 l2 -5 l2 5Z" fill="#fff" />
        <circle cx="60" cy="109" r="6.5" fill="#b4975a" />
        <text x="60" y="112.2" fontSize="9" fontWeight="700" textAnchor="middle" fill="#00244a" fontFamily="Georgia, serif">
          Y
        </text>
      </g>
    </svg>
  )
}
