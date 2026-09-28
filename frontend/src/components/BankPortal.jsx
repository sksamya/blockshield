import { useState } from 'react'
import { bank, consortium } from '../api'
import StatusBadge from './StatusBadge'
import BridgeKeySignerModal from './BridgeKeySignerModal'
import AuditInspector from './AuditInspector'

export default function BankPortal({ session }) {
  const bankId = session.role   // 'bank-b' or 'bank-c'

  // Transfer form state
  const [customerId, setCustomerId] = useState('cust_victim')
  const [recipient, setRecipient]   = useState('ACC-DEST-001')
  const [amount, setAmount]         = useState('100.00')
  const [deviceId, setDeviceId]     = useState('unknown_device')
  const [location, setLocation]     = useState('unusual_location')
  const [hadReset, setHadReset]     = useState(false)

  // Transfer result
  const [txResult, setTxResult] = useState(null)
  const [loading, setLoading]   = useState(false)
  const [txError, setTxError]   = useState('')

  // Step-up modal
  const [showSigner, setShowSigner] = useState(false)

  // Mule flag
  const [muleAccount, setMuleAccount] = useState('')
  const [muleReason, setMuleReason]   = useState('Suspected mule account')
  const [muleResult, setMuleResult]   = useState(null)

  async function initiateTransfer(e) {
    e.preventDefault()
    setLoading(true); setTxError(''); setTxResult(null)
    const cents = Math.round(parseFloat(amount) * 100)
    try {
      const data = await bank.transfer(bankId, {
        customer_id: customerId,
        recipient_account: recipient,
        amount_cents: cents,
        device_id: deviceId,
        ip_location: location,
        had_recent_password_reset: hadReset,
      })
      setTxResult(data)
      // Auto-open BridgeKey modal if step-up required
      if (data.requires_bridgekey && data.challenge?.challenge_id) {
        setShowSigner(true)
      }
    } catch (err) {
      setTxError(err.message)
    } finally { setLoading(false) }
  }

  async function completeStepUp(result) {
    setShowSigner(false)
    if (!txResult?.transfer_id) return
    const signature = typeof result === 'object' ? result.signature : result
    const txHash = typeof result === 'object' ? result.txHash : null

    try {
      const data = await bank.stepUp(bankId, txResult.transfer_id, signature, txHash)
      setTxResult(prev => ({
        ...prev,
        status: data.transfer_status,
        step_up_anchor: data.anchor,
        onchain_tx_hash: txHash || data.onchain_tx_hash
      }))
    } catch (err) {
      setTxError(`Step-up failed: ${err.message}`)
    }
  }

  async function flagMule(e) {
    e.preventDefault()
    setMuleResult(null)
    try {
      const data = await consortium.flagMule(muleAccount, bankId, muleReason)
      setMuleResult(data)
    } catch (err) {
      setMuleResult({ error: err.message })
    }
  }

  const challengeId = txResult?.challenge?.challenge_id

  return (
    <main className="max-w-5xl mx-auto p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100">{session.label} — Transfer Gateway</h2>
        <p className="text-sm text-slate-400">Initiate transfers with real-time SIM-swap fraud detection and BridgeKey step-up auth.</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* Transfer form */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h3 className="font-semibold text-slate-100 mb-4">💸 Initiate Transfer</h3>
          <form onSubmit={initiateTransfer} className="space-y-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Customer</label>
              <select value={customerId} onChange={e => setCustomerId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100">
                <option value="cust_victim">cust_victim — Alice Johnson (high-risk)</option>
                <option value="cust_legit">cust_legit — Bob Smith (low-risk)</option>
              </select>
            </div>
            <Field label="Recipient Account" value={recipient} onChange={setRecipient} placeholder="ACC-DEST-001" />
            <Field label="Amount ($)" value={amount} onChange={setAmount} placeholder="100.00" />
            <Field label="Device ID" value={deviceId} onChange={setDeviceId} placeholder="device_id" />
            <div>
              <label className="text-xs text-slate-400 block mb-1">IP Location</label>
              <select value={location} onChange={e => setLocation(e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100">
                <option value="unusual_location">Unusual location ⚠️</option>
                <option value="usual_home_location">Usual home location ✅</option>
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
              <input type="checkbox" checked={hadReset} onChange={e => setHadReset(e.target.checked)}
                className="w-4 h-4 rounded" />
              Had recent password reset
            </label>
            <button type="submit" disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-semibold transition-colors">
              {loading ? 'Evaluating…' : 'Submit Transfer'}
            </button>
          </form>
          {txError && <p className="mt-3 text-xs text-red-400 bg-red-900/30 rounded-lg p-2">{txError}</p>}
        </div>

        {/* Transfer result */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h3 className="font-semibold text-slate-100 mb-4">📊 Transfer Result</h3>
          {!txResult ? (
            <div className="text-center py-10 text-slate-500 text-sm">Submit a transfer to see results</div>
          ) : (
            <div className="space-y-3 text-sm">
              <Row label="Status"     value={<StatusBadge status={txResult.status} />} />
              <Row label="Transfer ID" value={txResult.transfer_id} mono />
              <Row label="Customer"   value={txResult.customer_display_id} />
              <Row label="Wallet"     value={txResult.wallet_address} mono small />
              <Row label="Risk Score" value={
                <span className={`font-bold ${txResult.risk_score >= 80 ? 'text-red-400' : txResult.risk_score >= 50 ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {txResult.risk_score}/100
                </span>
              } />
              <Row label="Action"     value={<StatusBadge status={txResult.action} />} />
              <Row label="Risk Reason" value={txResult.risk_reason} />
              <Row label="Mule Flag"  value={txResult.has_mule_flag ? '⚠️ Destination is mule' : '✅ Clean'} />
              <Row label="Anchor Hash" value={txResult.anchor_hash} mono small />
              {txResult.onchain_tx_hash && (
                <div className="bg-indigo-950/40 border border-indigo-700/60 rounded-lg p-2.5 my-2">
                  <p className="text-xs text-indigo-300 font-semibold mb-0.5">🔗 Live MST Blockchain Transaction:</p>
                  <a
                    href={`https://testnet.mstscan.com/tx/${txResult.onchain_tx_hash}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-indigo-400 hover:text-indigo-200 underline font-mono break-all"
                  >
                    {txResult.onchain_tx_hash} ↗
                  </a>
                </div>
              )}

              {/* Risk factors */}
              {txResult.factors?.length > 0 && (
                <div className="bg-slate-900 rounded-lg p-3 mt-2">
                  <p className="text-xs text-slate-500 mb-2 font-semibold uppercase tracking-wide">Risk Factors</p>
                  {txResult.factors.map((f, i) => (
                    <div key={i} className="flex items-start gap-2 mb-1">
                      <span className={`text-xs px-1.5 py-0.5 rounded font-mono ${f.weight >= 40 ? 'bg-red-900 text-red-300' : f.weight >= 20 ? 'bg-amber-900 text-amber-300' : 'bg-slate-800 text-slate-400'}`}>
                        +{f.weight}
                      </span>
                      <span className="text-xs text-slate-300">{f.description}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* BridgeKey step-up */}
              {txResult.requires_bridgekey && challengeId && txResult.status === 'PENDING_VERIFICATION' && (
                <button
                  onClick={() => setShowSigner(true)}
                  className="w-full bg-amber-600 hover:bg-amber-500 text-white py-2 rounded-lg text-sm font-semibold transition-colors mt-2"
                >
                  🔑 Open BridgeKey Signer
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Mule Flagging */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h3 className="font-semibold text-slate-100 mb-1">🚨 Flag Mule Account</h3>
        <p className="text-xs text-slate-400 mb-4">Report a confirmed mule account to the MST FraudRegistry (consortium-shared).</p>
        <form onSubmit={flagMule} className="flex flex-wrap gap-3">
          <input value={muleAccount} onChange={e => setMuleAccount(e.target.value)}
            placeholder="Account number (e.g. ACC-DEST-001)"
            className="flex-1 min-w-40 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-red-500"
          />
          <input value={muleReason} onChange={e => setMuleReason(e.target.value)}
            placeholder="Reason"
            className="flex-1 min-w-40 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-red-500"
          />
          <button type="submit"
            className="bg-red-700 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
            Flag Mule
          </button>
        </form>
        {muleResult && !muleResult.error && (
          <div className="mt-3 bg-red-900/30 border border-red-700 rounded-lg p-3 text-xs text-red-300">
            <p className="font-semibold mb-1">✅ Mule account flagged on MST Blockchain</p>
            <p>TX hash: <span className="font-mono">{muleResult.tx_hash}</span></p>
            <p>Token: <span className="font-mono">{muleResult.account_token?.substring(0, 20)}…</span></p>
          </div>
        )}
        {muleResult?.error && <p className="mt-3 text-xs text-red-400">{muleResult.error}</p>}
      </div>

      {/* Audit Inspector — calls backend */}
      <AuditInspector bankId={bankId} />

      {/* BridgeKey signer modal */}
      {showSigner && challengeId && (
        <BridgeKeySignerModal
          challengeId={challengeId}
          onSuccess={completeStepUp}
          onClose={() => setShowSigner(false)}
        />
      )}
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

function Row({ label, value, mono, small }) {
  return (
    <div className="flex items-start gap-2 py-1 border-b border-slate-700/50 last:border-0">
      <span className="text-slate-500 min-w-28 shrink-0 text-xs mt-0.5">{label}</span>
      <span className={mono ? `font-mono break-all ${small ? 'text-xs' : 'text-sm'} text-slate-300` : 'text-slate-300 text-sm'}>{value}</span>
    </div>
  )
}
