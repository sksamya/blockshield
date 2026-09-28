import { useState } from 'react'
import { consortium } from '../api'

/**
 * Audit Inspector — wired to GET /api/consortium/audit/<bank_id>/<event_ref>
 * Previously computed integrity check client-side; now delegates to backend.
 */
export default function AuditInspector({ bankId }) {
  const [eventRef, setEventRef] = useState('')
  const [result, setResult]     = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')

  async function inspect() {
    if (!eventRef.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const data = await consortium.audit(bankId, eventRef.trim())
      setResult(data)
    } catch (err) {
      setError(err.message || 'Audit request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
      <h3 className="font-semibold text-slate-100 mb-1">🔍 Audit Inspector</h3>
      <p className="text-xs text-slate-400 mb-4">
        Verify on-chain decision anchor integrity for any transfer or password-reset event.
      </p>

      <div className="flex gap-2 mb-4">
        <input
          value={eventRef}
          onChange={e => setEventRef(e.target.value)}
          placeholder="Event ref / Transfer ID (e.g. tx_abc123)"
          className="flex-1 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
        />
        <button
          onClick={inspect}
          disabled={loading || !eventRef.trim()}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
        >
          {loading ? '…' : 'Inspect'}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/40 border border-red-700 rounded-lg px-4 py-3 text-sm text-red-300 mb-3">
          ⚠️ {error}
        </div>
      )}

      {result && (
        <div className={`rounded-lg border p-4 text-sm ${result.is_valid ? 'bg-emerald-900/30 border-emerald-700' : 'bg-red-900/30 border-red-700'}`}>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">{result.is_valid ? '✅' : '❌'}</span>
            <span className={`font-semibold ${result.is_valid ? 'text-emerald-300' : 'text-red-300'}`}>
              {result.is_valid ? 'Integrity verified — record matches on-chain anchor' : 'INTEGRITY FAILURE — tampering detected!'}
            </span>
          </div>
          <div className="space-y-1.5 text-slate-300">
            {result.event_ref  && <Row label="Event ref"  value={result.event_ref} mono />}
            {result.computed_hash && <Row label="Computed hash" value={result.computed_hash} mono />}
            {result.anchored_hash && <Row label="On-chain hash" value={result.anchored_hash} mono />}
            {result.anchored_at  && <Row label="Anchored at" value={new Date(result.anchored_at * 1000).toLocaleString()} />}
            {result.bank_id      && <Row label="Bank" value={result.bank_id} />}
            {result.tx_hash      && <Row label="TX hash" value={result.tx_hash} mono />}
          </div>
        </div>
      )}
    </div>
  )
}

function Row({ label, value, mono }) {
  return (
    <div className="flex flex-col sm:flex-row sm:gap-2">
      <span className="text-slate-500 min-w-28">{label}:</span>
      <span className={mono ? 'font-mono text-xs break-all text-slate-300' : 'text-slate-300'}>{value}</span>
    </div>
  )
}
