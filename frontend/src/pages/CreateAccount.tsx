import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const MIN_PASSWORD = 8

export default function CreateAccount() {
  const { user, register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ firstName: '', lastName: '', email: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user && !submitting) return <Navigate to="/" replace />

  const update = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (form.password.length < MIN_PASSWORD) return setError(`Password must be at least ${MIN_PASSWORD} characters.`)
    if (form.password !== form.confirm) return setError('Passwords do not match.')
    setError('')
    setSubmitting(true)
    try {
      await register({
        first_name: form.firstName.trim(),
        last_name: form.lastName.trim(),
        email: form.email.trim(),
        password: form.password,
      })
      navigate('/', { replace: true, state: { welcome: true } })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="container section auth">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Create your account</h1>
        <p className="muted">Save your conversations with our assistant and pick up where you left off.</p>
        <div className="row">
          <label>
            First name
            <input required maxLength={50} value={form.firstName} onChange={update('firstName')} autoComplete="given-name" />
          </label>
          <label>
            Last name
            <input required maxLength={50} value={form.lastName} onChange={update('lastName')} autoComplete="family-name" />
          </label>
        </div>
        <label>
          Email
          <input type="email" required value={form.email} onChange={update('email')} autoComplete="email" />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            minLength={MIN_PASSWORD}
            maxLength={128}
            value={form.password}
            onChange={update('password')}
            autoComplete="new-password"
          />
          <span className="hint">At least {MIN_PASSWORD} characters.</span>
        </label>
        <label>
          Confirm password
          <input type="password" required value={form.confirm} onChange={update('confirm')} autoComplete="new-password" />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button className="btn btn-block" type="submit" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create Account'}
        </button>
        <p className="muted small">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  )
}
