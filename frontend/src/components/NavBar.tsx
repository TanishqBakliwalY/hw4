import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const [open, setOpen] = useState(false)
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const close = () => setOpen(false)

  async function handleLogout() {
    close()
    await logout()
    navigate('/')
  }

  return (
    <header className="nav">
      {/* Scrolling ticker (pauses on hover; static for reduced-motion users) */}
      <div className="announce" aria-label="Store news">
        <div className="ticker">
          {[0, 1].map((k) => (
            <span key={k} aria-hidden={k === 1}>
              🏈 The Game · Sat, Nov 21 at Fenway <b>·</b> Printed &amp; embroidered on Broadway since 1973 <b>·</b> Unworn
              items with tags can be returned within 30 days <b>·</b> Officially licensed Yale apparel <b>·</b>{' '}
            </span>
          ))}
        </div>
      </div>
      <nav className="nav-inner container">
        <Link to="/" className="brand" onClick={close}>
          <span className="brand-mark">CC</span>
          <span className="brand-text">
            Campus Customs
            <small>Bulldog Blue · New Haven</small>
          </span>
        </Link>

        <button
          className="nav-toggle"
          aria-label="Toggle navigation"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          ☰
        </button>

        <div className={`nav-links ${open ? 'open' : ''}`}>
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} onClick={close}>
              {l.label}
            </NavLink>
          ))}
          <span className="nav-sep" />
          {loading ? null : user ? (
            <>
              <span className="nav-user">Hi, {user.first_name}</span>
              <button className="btn btn-small btn-outline" onClick={handleLogout}>
                Log Out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" onClick={close}>
                Log In
              </NavLink>
              <NavLink to="/create-account" className="btn btn-small" onClick={close}>
                Create Account
              </NavLink>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
