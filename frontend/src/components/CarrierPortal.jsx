import { useState, useEffect } from 'react'
import { carrier } from '../api'

export default function CarrierPortal() {
  const [phone, setPhone]           = useState('+15551234567')
  const [eventType, setEventType]   = useState('SIM_SWAP')
  const [prePhone, setPrePhone]     = useState('+15551234567')
  const [events, setEvents]         = useState([])
  const [loading, setLoading]       = useState(false)
  const [result, setResult]         = useState(null)
  const [preResult, setPreResult]   = useState(null)
  const [error, setError]           = useState('')

  async function loadEvents() {
    try {
      const d = await carrier.events()
      setEvents(d.events || [])
    } catch { /* silent */ }
  }

  useEffect(() => { loadEvents() }, [])

  async function broadcastSwap(e) {
    e.preventDefault()
    setLoading(true); setError(''); setResult(null)
    try {
      const d = await carrier.recordSwap(phone, eventType)
      setResult(d)
      loadEvents()
    } catch (err) {
      setError(err.message)
    } finally { setLoading(false) }
  }

  async function sendPreNotif(e) {
    e.preventDefault()
    setPreResult(null)
    try {
      const d = await carrier.preNotify(prePhone)
      setPreResult(d.result || d)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <main className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100">Carrier A — Control Console</h2>
        <p className="text-sm text-slate-400">Broadcast SIM-swap events and pre-notifications to the MST Blockchain consortium.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* Broadcast swap */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h3 className="font-semibold text-slate-100 mb-4">📡 Broadcast SIM Event</h3>
          <div className="flex flex-wrap gap-2 mb-3">
            <span className="text-xs text-slate-400 self-center">Demo:</span>
            <button
              type="button"
              onClick={() => setPhone('+15551234567')}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors cursor-pointer ${
                phone === '+15551234567'
                  ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200'
                  : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              Alice Johnson (+15551234567)
            </button>
            <button
              type="button"
              onClick={() => setPhone('+15557654321')}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors cursor-pointer ${
                phone === '+15557654321'
                  ? 'bg-indigo-600/30 border-indigo-500 text-indigo-200'
                  : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              Bob Smith (+15557654321)
            </button>
          </div>
          <form onSubmit={broadcastSwap} className="space-y-3">
            <Field label="Phone (E.164)" value={phone} onChange={setPhone} placeholder="+15551234567" />
            <div>
              <label className="text-xs text-slate-400 block mb-1">Event Type</label>
              <select
                value={eventType} onChange={e => setEventType(e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100"
              >
                <option value="SIM_SWAP">SIM_SWAP</option>
                <option value="PORT_OUT">PORT_OUT</option>
                <option value="ESIM_TRANSFER">ESIM_TRANSFER</option>
              </select>
            </div>
            <button type="submit" disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white py-2 rounded-lg text-sm font-semibold transition-colors">
              {loading ? 'Broadcasting…' : 'Broadcast Event'}
            </button>
          </form>
          {result && (
            <div className="mt-4 bg-emerald-900/30 border border-emerald-700 rounded-lg p-3 text-xs text-emerald-300">
              <p className="font-semibold mb-1">✅ Event recorded on MST Blockchain</p>
              <p className="mb-1">
                TX: <a
                  href={`https://testnet.mstscan.com/tx/${result.tx_hash}`}
                  target="_blank"
                  rel="noreferrer"
                  className="font-mono text-emerald-300 hover:text-emerald-100 underline break-all"
                >
                  {result.tx_hash} ↗
                </a>
              </p>
              <p>Pre-notified: {result.pre_notified ? 'Yes' : 'No'}</p>
            </div>
          )}
          {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
        </div>

        {/* Pre-notification */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h3 className="font-semibold text-slate-100 mb-1">🔔 Pre-Notification</h3>
          <p className="text-xs text-slate-400 mb-3">Register an upcoming swap so banks reduce risk score (lower fraud alert).</p>
          <div className="flex flex-wrap gap-2 mb-3">
            <span className="text-xs text-slate-400 self-center">Demo:</span>
            <button
              type="button"
              onClick={() => setPrePhone('+15551234567')}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors cursor-pointer ${
                prePhone === '+15551234567'
                  ? 'bg-amber-600/30 border-amber-500 text-amber-200'
                  : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              Alice Johnson (+15551234567)
            </button>
            <button
              type="button"
              onClick={() => setPrePhone('+15557654321')}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors cursor-pointer ${
                prePhone === '+15557654321'
                  ? 'bg-amber-600/30 border-amber-500 text-amber-200'
                  : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              Bob Smith (+15557654321)
            </button>
          </div>
          <form onSubmit={sendPreNotif} className="space-y-3">
            <Field label="Phone (E.164)" value={prePhone} onChange={setPrePhone} placeholder="+15551234567" />
            <button type="submit"
              className="w-full bg-amber-600 hover:bg-amber-500 text-white py-2 rounded-lg text-sm font-semibold transition-colors">
              Register Pre-Notification
            </button>
          </form>
          {preResult && (
            <div className="mt-4 bg-amber-900/30 border border-amber-700 rounded-lg p-3 text-xs text-amber-300">
              <p className="font-semibold mb-1">{preResult.is_onchain ? '✅ Pre-notification confirmed on MST Testnet' : '✅ Pre-notification registered locally'}</p>
              <p>Valid until: {new Date(preResult.valid_until * 1000).toLocaleString()}</p>
              {preResult.tx_hash && <p className="font-mono break-all">TX: {preResult.tx_hash}</p>}
            </div>
          )}
        </div>
      </div>

      {/* Event Feed */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-slate-100">📋 Recorded Swap Events</h3>
          <button onClick={loadEvents} className="text-xs text-slate-400 hover:text-slate-100 transition-colors">↻ Refresh</button>
        </div>
        {events.length === 0
          ? <p className="text-sm text-slate-500 text-center py-4">No events recorded yet. Broadcast one above.</p>
          : (
            <div className="space-y-2">
              {events.map((ev, i) => (
                <div key={i} className="bg-slate-900 rounded-lg px-4 py-3 flex flex-wrap items-center gap-3 text-sm">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${ev.pre_notified ? 'bg-amber-900 text-amber-300' : 'bg-red-900 text-red-300'}`}>
                    {ev.pre_notified ? 'Pre-notified' : 'Unnotified'}
                  </span>
                  <span className="font-mono text-slate-400 text-xs">{ev.token?.substring(0, 20)}…</span>
                  <span className="text-slate-300">{ev.event_type}</span>
                  <span className="text-slate-500 ml-auto text-xs">{new Date(ev.timestamp * 1000).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )
        }
      </div>
    </main>
  )
}

function Field({ label, value, onChange, placeholder }) {
  return (
    <div>
      <label className="text-xs text-slate-400 block mb-1">{label}</label>
      <input
        className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
        value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
      />
    </div>
  )
}
