import { useState, useEffect } from 'react'
import { bank, consortium } from '../api'
import StatusBadge from './StatusBadge'
import BridgeKeySignerModal from './BridgeKeySignerModal'
import AuditInspector from './AuditInspector'

export default function BankPortal({ session }) {
  const bankId = session.role   // 'bank-b' or 'bank-c'

  // Customers state
  const [customerList, setCustomerList] = useState([])
  const [customerId, setCustomerId] = useState('CUST-1001')

  // Transfer form state
  const [recipient, setRecipient]   = useState('ACC-DEST-001')
  const [amount, setAmount]         = useState('100.00')
  const [deviceId, setDeviceId]     = useState('unknown_device')
  const [location, setLocation]     = useState('unusual_location')
  const [hadReset, setHadReset]     = useState(false)

  // SIM detection state
  const [simDetection, setSimDetection] = useState(null)
  const [loadingSim, setLoadingSim]     = useState(false)
  const criticalSwapAlert = Boolean(simDetection?.swap_detected && !simDetection?.is_pre_notified)

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

  // Load customer list
  async function loadCustomers() {
    try {
      const data = await bank.customers(bankId)
      if (data.customers && data.customers.length > 0) {
        setCustomerList(data.customers)
      }
    } catch {
      // fallback
    }
  }

  // Check SIM status on MST Blockchain
  async function checkSimStatus(cId) {
    if (!cId) return
    setLoadingSim(true)
    try {
      const res = await bank.detectSwap(bankId, cId)
      setSimDetection(res)
    } catch (err) {
      console.error('SIM detection error:', err)
    } finally {
      setLoadingSim(false)
    }
  }

  useEffect(() => {
    loadCustomers()
  }, [bankId])

  useEffect(() => {
    checkSimStatus(customerId)
  }, [customerId, bankId])

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
      // Re-check SIM status to stay in sync
      checkSimStatus(customerId)
    } catch (err) {
      setTxError(err.message)
    } finally { setLoading(false) }
  }

  async function completeStepUp(result) {
    if (!txResult?.transfer_id) { setShowSigner(false); return }
    const signature = typeof result === 'object' ? result.signature : result
    const txHash = typeof result === 'object' ? result.txHash : null

    try {
      const data = await bank.stepUp(bankId, txResult.transfer_id, signature, txHash)
      setTxResult(prev => ({
        ...prev,
        status: data.transfer_status || 'APPROVED_BY_BRIDGEKEY',
        transfer_status: data.transfer_status,
        step_up_anchor: data.anchor,
        step_up_message: data.message,
        onchain_tx_hash: txHash || data.onchain_tx_hash,
        tx_hash: data.tx_hash || txHash || prev?.tx_hash,
        anchor_hash: data.anchor?.decision_hash || prev?.anchor_hash,
      }))
      setTxError('')
    } catch (err) {
      setTxError(`Step-up failed: ${err.message}`)
    } finally {
      setShowSigner(false)
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
  const activeCustomer = customerList.find(c => c.customer_id === customerId || c.id === customerId) || {
    customer_id: customerId,
    phone: customerId === 'CUST-1002' ? '+15557654321' : '+15551234567',
    wallet_address: customerId === 'CUST-1002' ? '0xa61efceef6debe10a029af2bf7e37220b6dae22f' : '0x19515982e62f9fc03f4e43498ce18028a4cb650e'
  }

  return (
    <main className="max-w-5xl mx-auto p-6 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100">{session.label} — Transfer Gateway</h2>
        <p className="text-sm text-slate-400">Initiate transfers with real-time SIM-swap fraud detection and BridgeKey step-up auth on MST Blockchain.</p>
      </div>

      {/* Real-time Phone-to-Wallet & SIM Swap Detection Banner */}
      <div className={`border rounded-xl p-4 transition-all ${criticalSwapAlert ? 'bg-red-950/40 border-red-700/80 text-red-200' : 'bg-slate-800 border-slate-700 text-slate-200'}`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{criticalSwapAlert ? '🚨' : '🛡️'}</span>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm">
                  {criticalSwapAlert ? 'CRITICAL FRAUD ALERT: Un-notified SIM Swap' : simDetection?.swap_detected ? 'Verified SIM Swap Detected' : 'SIM Integrity Normal'}
                </span>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${simDetection?.sms_otp_allowed === false ? 'bg-red-900 text-red-100' : 'bg-emerald-900 text-emerald-200'}`}>
                  {simDetection?.sms_otp_allowed === false ? 'SMS OTP REFUSED' : 'SMS OTP ALLOWED'}
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5">
                Customer: <strong className="font-mono text-white">{activeCustomer.customer_id || customerId}</strong> •
                Phone: <strong className="font-mono text-white">{activeCustomer.phone}</strong> •
                Bound Wallet: <strong className="font-mono text-indigo-300">{activeCustomer.wallet_address?.substring(0, 10)}…{activeCustomer.wallet_address?.substring(activeCustomer.wallet_address.length - 6)}</strong>
              </p>
            </div>
          </div>

          <button
            onClick={() => checkSimStatus(customerId)}
            disabled={loadingSim}
            className="self-start sm:self-auto text-xs bg-slate-900 hover:bg-slate-700 text-slate-200 border border-slate-600 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 shrink-0 cursor-pointer"
          >
            <span>{loadingSim ? 'Checking…' : '↻ Query MST Chain'}</span>
          </button>
        </div>

        {simDetection?.swap_detected && (
          <div className={`mt-3 pt-3 border-t text-xs space-y-1 ${criticalSwapAlert ? 'border-red-800/60 text-red-300' : 'border-slate-700 text-slate-300'}`}>
            <p>
              {simDetection.is_pre_notified ? '✅ Carrier A recorded a pre-notified' : '⚠️ Carrier A broadcast an un-notified'} <strong>{simDetection.swap_event?.event_type || 'SIM_SWAP'}</strong> event {simDetection.swap_age_hours}h ago on the MST Blockchain.
            </p>
            {criticalSwapAlert && <p className="text-red-400 font-semibold">
              Bank B Policy: SMS OTP intercepted risk is high. SMS OTP is disabled. All transfers require biometric authorization via BridgeKey (bound to {activeCustomer.wallet_address?.substring(0, 10)}…).
            </p>}
          </div>
        )}
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* Transfer form */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h3 className="font-semibold text-slate-100 mb-4">💸 Initiate Transfer</h3>
          <form onSubmit={initiateTransfer} className="space-y-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Customer</label>
              <select
                value={customerId}
                onChange={e => setCustomerId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 font-medium"
              >
                <option value="CUST-1001">CUST-1001 — Alice Johnson (+15551234567)</option>
                <option value="CUST-1002">CUST-1002 — Bob Smith (+15557654321)</option>
                <option value="cust_victim">cust_victim (Legacy alias: Alice Johnson)</option>
                <option value="cust_legit">cust_legit (Legacy alias: Bob Smith)</option>
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
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-semibold transition-colors cursor-pointer">
              {loading ? 'Evaluating Risk…' : 'Submit Transfer'}
            </button>
          </form>
          {txError && <p className="mt-3 text-xs text-red-400 bg-red-900/30 rounded-lg p-2">{txError}</p>}
        </div>

        {/* Transfer result */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h3 className="font-semibold text-slate-100 mb-4">📊 Transfer Result</h3>
          {!txResult ? (
            <div className="text-center py-10 text-slate-500 text-sm">Submit a transfer to see real-time fraud risk and on-chain detection</div>
          ) : (
            <div className="space-y-3 text-sm">
              {/* Success banner */}
              {(txResult.status === 'APPROVED_BY_BRIDGEKEY' || txResult.transfer_status === 'APPROVED_BY_BRIDGEKEY') && (
                <div className="bg-emerald-900/40 border border-emerald-600 rounded-xl p-4 mb-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-2xl">✅</span>
                    <span className="font-bold text-emerald-300">Transfer Approved via BridgeKey!</span>
                  </div>
                  <p className="text-xs text-emerald-400 ml-8">
                    {txResult.step_up_message || 'Biometric verification successful. Transfer executed.'}
                  </p>
                  {(txResult.onchain_tx_hash || txResult.tx_hash) && (
                    <p className="text-xs text-emerald-500 mt-1 ml-8">
                      On-chain authorization:{' '}
                      <a
                        href={`https://testnet.mstscan.com/tx/${txResult.onchain_tx_hash || txResult.tx_hash}`}
                        target="_blank" rel="noreferrer"
                        className="font-mono text-emerald-400 underline hover:text-emerald-200"
                      >
                        {(txResult.onchain_tx_hash || txResult.tx_hash).substring(0, 22)}… ↗
                      </a>
                    </p>
                  )}
                </div>
              )}

              <Row label="Status"     value={<StatusBadge status={txResult.status} />} />
              <Row label="Transfer ID" value={txResult.transfer_id} mono />
              <Row label="Customer"   value={txResult.customer_display_id || customerId} />
              <Row label="Bound Wallet" value={txResult.wallet_address || activeCustomer.wallet_address} mono small />
              <Row label="Risk Score" value={
                <span className={`font-bold ${txResult.risk_score >= 80 ? 'text-red-400' : txResult.risk_score >= 50 ? 'text-amber-400' : 'text-emerald-400'}`}>
                  {txResult.risk_score}/100
                </span>
              } />
              <Row label="Action"     value={<StatusBadge status={txResult.action} />} />
              <Row label="Risk Reason" value={txResult.risk_reason || txResult.reason} />
              <Row label="Mule Flag"  value={txResult.has_mule_flag ? '⚠️ Destination is mule' : '✅ Clean'} />
              <Row label="Anchor Hash" value={txResult.anchor_hash} mono small />

              {(txResult.onchain_tx_hash || txResult.tx_hash) && (
                <Row
                  label="MST Explorer"
                  value={
                    <a
                      href={`https://testnet.mstscan.com/tx/${txResult.onchain_tx_hash || txResult.tx_hash}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-mono text-indigo-400 underline"
                    >
                      {(txResult.onchain_tx_hash || txResult.tx_hash).substring(0, 18)}… ↗
                    </a>
                  }
                />
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

              {/* BridgeKey step-up button — only when still pending */}
              {txResult.requires_bridgekey && challengeId && txResult.status === 'PENDING_VERIFICATION' && (
                <button
                  onClick={() => setShowSigner(true)}
                  className="w-full bg-amber-600 hover:bg-amber-500 text-white py-2 rounded-lg text-sm font-semibold transition-colors mt-2 cursor-pointer"
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
            className="bg-red-700 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors cursor-pointer">
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
