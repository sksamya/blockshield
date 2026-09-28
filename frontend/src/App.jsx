import { useState } from 'react'
import EnterpriseLogin from './components/EnterpriseLogin'
import CarrierPortal from './components/CarrierPortal'
import BankPortal from './components/BankPortal'

export default function App() {
  const [session, setSession] = useState(null) // { role: 'carrier-a'|'bank-b'|'bank-c', label }

  if (!session) return <EnterpriseLogin onLogin={setSession} />

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Top bar */}
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-sm">BS</div>
          <span className="font-semibold text-slate-100">BlockShield Enterprise</span>
          <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">{session.label}</span>
        </div>
        <button
          onClick={() => setSession(null)}
          className="text-sm text-slate-400 hover:text-slate-100 transition-colors"
        >
          Sign out
        </button>
      </header>

      {session.role === 'carrier-a'
        ? <CarrierPortal session={session} />
        : <BankPortal session={session} />}
    </div>
  )
}
