import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useChatUi } from '../chatUi'
import HandsomeDan from './HandsomeDan'

// The 142nd Game: Harvard vs Yale, Sat Nov 21 2026, Fenway Park, Boston (listed 3:30 PM ET).
// Source: gocrimson.com / mlb.com announcements (Aug 2025).
const GAME = {
  kickoff: new Date('2026-11-21T15:30:00-05:00'),
  label: 'The 142nd Game · Sat, Nov 21 · Fenway Park, Boston',
}

function useCountdown(target: Date) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [])
  const ms = Math.max(0, target.getTime() - now)
  return {
    over: ms === 0,
    parts: [
      { label: 'Days', value: Math.floor(ms / 86_400_000) },
      { label: 'Hrs', value: Math.floor(ms / 3_600_000) % 24 },
      { label: 'Min', value: Math.floor(ms / 60_000) % 60 },
      { label: 'Sec', value: Math.floor(ms / 1000) % 60 },
    ],
  }
}

export default function GameDayHero() {
  const { over, parts } = useCountdown(GAME.kickoff)
  const { ask } = useChatUi()

  return (
    <section className="hero game-hero">
      <div className="container game-hero-inner">
        <div className="game-hero-copy">
          <p className="eyebrow">{GAME.label}</p>
          <h1>
            Beat Harvard.
            <br />
            <span className="h1-accent">Look good doing it.</span>
          </h1>
          <p className="hero-sub">
            Hoodies, crewnecks and tees, printed and embroidered by a family-run shop across the street from Yale since
            1973.
          </p>

          {over ? (
            <p className="countdown-done">Thanks for cheering, Bulldogs! Gear up for next season.</p>
          ) : (
            <div className="countdown" role="timer" aria-label="Countdown to The Game">
              {parts.map((p) => (
                <div key={p.label} className="countdown-cell">
                  <span className="countdown-num">{String(p.value).padStart(2, '0')}</span>
                  <span className="countdown-label">{p.label}</span>
                </div>
              ))}
            </div>
          )}

          <div className="hero-actions">
            <Link to="/products?q=game%20football" className="btn btn-gold">
              Shop game-day gear
            </Link>
            <button className="btn btn-ghost" onClick={() => ask('What should I wear to The Game at Fenway?')}>
              <HandsomeDan size={22} /> Ask Handsome Dan
            </button>
          </div>
        </div>

        {/* Felt pennant that waves gently (CSS animation; disabled for reduced-motion users) */}
        <div className="pennant-wrap" aria-hidden="true">
          <div className="pennant-pole" />
          <div className="pennant">
            <span>YALE</span>
          </div>
          <HandsomeDan size={132} className="hero-dan" />
        </div>
      </div>
    </section>
  )
}
