import { useState } from 'react'

const PORTALS = [
  { role: 'carrier-a', label: 'Carrier A', icon: '📡', color: 'indigo', desc: 'SIM-swap event broadcasting & pre-notification console' },
  { role: 'bank-b',    label: 'Bank B',    icon: '🏦', color: 'emerald', desc: 'Transfer gateway, BridgeKey auth, fraud detection (Bank B)' },
  { role: 'bank-c',    label: 'Bank C',    icon: '🏛️', color: 'violet',  desc: 'Transfer gateway, BridgeKey auth, fraud detection (Bank C)' },
]

const colorMap = {
  indigo:  { ring: 'ring-indigo-500',  btn: 'bg-indigo-600 hover:bg-indigo-500',  badge: 'bg-indigo-900 text-indigo-300' },
  emerald: { ring: 'ring-emerald-500', btn: 'bg-emerald-600 hover:bg-emerald-500', badge: 'bg-emerald-900 text-emerald-300' },
  violet:  { ring: 'ring-violet-500',  btn: 'bg-violet-600 hover:bg-violet-500',  badge: 'bg-violet-900 text-violet-300' },
}

// Simple mock credential check (enterprise systems use SSO; this simulates that gate)
const CREDS = {
  'carrier-a': { user: 'carrier_admin', pass: 'BlockShield#2025' },
  'bank-b':    { user: 'bankb_admin',   pass: 'BlockShield#2025' },
  'bank-c':    { user: 'bankc_admin',   pass: 'BlockShield#2025' },
}

export default function EnterpriseLogin({ onLogin }) {
  const [selected, setSelected] = useState(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    setError('')
    const expected = CREDS[selected]
    if (username === expected.user && password === expected.pass) {
      onLogin({ role: selected, label: PORTALS.find(p => p.role === selected).label })
    } else {
      setError('Invalid credentials. Access denied.')
    }
  }

  const portal = selected ? PORTALS.find(p => p.role === selected) : null
  const c = portal ? colorMap[portal.color] : null

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-6">
      {/* Logo */}
      <div className="mb-8 text-center">
        <div className="w-16 h-16 rounded-2xl bg-indigo-600 flex items-center justify-center text-white text-2xl font-bold mx-auto mb-4">BS</div>
        <h1 className="text-2xl font-bold text-slate-100">BlockShield Enterprise</h1>
        <p className="text-sm text-slate-400 mt-1">Authorized personnel only — SIM-swap fraud prevention network</p>
      </div>

      {!selected ? (
        /* Portal selector */
        <div className="w-full max-w-lg">
          <p className="text-xs text-slate-500 uppercase tracking-widest mb-4 text-center">Select your portal</p>
          <div className="grid gap-3">
            {PORTALS.map(p => {
              const cl = colorMap[p.color]
              return (
                <button
                  key={p.role}
                  onClick={() => { setSelected(p.role); setUsername(''); setPassword(''); setError('') }}
                  className={`flex items-center gap-4 p-4 rounded-xl bg-slate-800 border border-slate-700 hover:border-slate-500 text-left transition-all ring-0 hover:ring-2 ${cl.ring}`}
                >
                  <span className="text-3xl">{p.icon}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-100">{p.label}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${cl.badge}`}>{p.role}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">{p.desc}</p>
                  </div>
                  <span className="text-slate-500">›</span>
                </button>
              )
            })}
          </div>
        </div>
      ) : (
        /* Credential form */
        <div className="w-full max-w-sm">
          <button onClick={() => setSelected(null)} className="text-sm text-slate-400 hover:text-slate-100 mb-6 flex items-center gap-1">
            ← Back
          </button>
          <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6">
            <div className="flex items-center gap-3 mb-6">
              <span className="text-2xl">{portal.icon}</span>
              <div>
                <h2 className="font-semibold text-slate-100">{portal.label} Portal</h2>
                <p className="text-xs text-slate-400">Enterprise authentication</p>
              </div>
            </div>
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Username</label>
                <input
                  className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  value={username} onChange={e => setUsername(e.target.value)}
                  placeholder={CREDS[selected].user} autoComplete="username"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Password</label>
                <input
                  type="password"
                  className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  value={password} onChange={e => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
              {error && <p className="text-xs text-red-400 bg-red-900/30 rounded-lg px-3 py-2">{error}</p>}
              <button type="submit" className={`${c.btn} text-white font-semibold py-2 rounded-lg transition-colors`}>
                Access Portal
              </button>
            </form>
            <p className="text-xs text-slate-600 mt-4 text-center">🔒 Credentials issued during onboarding. Contact IT for access.</p>
          </div>
        </div>
      )}
    </div>
  )
}
