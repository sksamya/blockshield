import { useState } from 'react'
import { wallet } from '../api'

/**
 * BridgeKey Signer Modal
 *
 * Critical fix: we ALWAYS fetch message_text from the backend
 * (GET /api/wallet/challenge/<id>) before signing, so the
 * string passed to personal_sign matches what the backend stored.
 *
 * Props:
 *   challengeId  – string
 *   onSuccess    – fn(signature)
 *   onClose      – fn()
 */
export default function BridgeKeySignerModal({ challengeId, onSuccess, onClose }) {
  const [step, setStep]       = useState('idle') // idle | fetching | signing | done | error
  const [msg, setMsg]         = useState('')
  const [sig, setSig]         = useState('')

  async function handleSign() {
    try {
      setStep('fetching')
      setMsg('')

      // Step 1 – fetch the canonical message_text from the backend
      const challenge = await wallet.getChallenge(challengeId)
      const messageText = challenge.message_text
      if (!messageText) throw new Error('Backend challenge has no message_text')

      setStep('signing')

      // Step 2 – ask BridgeKey (window.ethereum) to sign EXACTLY that string
      if (!window.ethereum) throw new Error('BridgeKey extension not detected. Install it from the Chrome Web Store.')

      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' })
      const walletAddress = accounts[0]

      // EIP-191 personal_sign: params are [message, address]
      const signature = await window.ethereum.request({
        method: 'personal_sign',
        params: [messageText, walletAddress],
      })

      setSig(signature)
      setStep('done')
      onSuccess(signature)
    } catch (err) {
      setMsg(err.message || 'Unknown error')
      setStep('error')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-xl">🔑</div>
          <div>
            <h2 className="font-bold text-slate-100">BridgeKey Biometric Sign</h2>
            <p className="text-xs text-slate-400">Step-up authentication required</p>
          </div>
        </div>

        {/* Challenge ID */}
        <div className="bg-slate-900 rounded-lg px-3 py-2 mb-6">
          <p className="text-xs text-slate-500">Challenge ID</p>
          <p className="text-xs text-slate-300 font-mono break-all">{challengeId}</p>
        </div>

        {step === 'idle' && (
          <div className="space-y-4">
            <p className="text-sm text-slate-300">
              Your transfer requires biometric verification via the <strong>BridgeKey</strong> extension.
              Click below to approve with your hardware-backed wallet.
            </p>
            <p className="text-xs text-slate-500 bg-slate-900 rounded-lg p-3">
              ⚠️ The exact challenge message is fetched from the server and signed via <code>personal_sign</code> — your private key never leaves your device.
            </p>
            <button
              onClick={handleSign}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 rounded-xl transition-colors"
            >
              Sign with BridgeKey
            </button>
          </div>
        )}

        {step === 'fetching' && (
          <div className="text-center py-6">
            <div className="animate-spin w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-3" />
            <p className="text-sm text-slate-400">Fetching challenge from server…</p>
          </div>
        )}

        {step === 'signing' && (
          <div className="text-center py-6">
            <div className="animate-spin w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full mx-auto mb-3" />
            <p className="text-sm text-slate-400">Waiting for BridgeKey approval…</p>
            <p className="text-xs text-slate-500 mt-1">Check your browser extension</p>
          </div>
        )}

        {step === 'done' && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-emerald-400">
              <span className="text-xl">✅</span>
              <span className="font-semibold">Signature captured</span>
            </div>
            <div className="bg-slate-900 rounded-lg px-3 py-2">
              <p className="text-xs text-slate-500 mb-1">Signature</p>
              <p className="text-xs text-slate-300 font-mono break-all">{sig}</p>
            </div>
          </div>
        )}

        {step === 'error' && (
          <div className="space-y-4">
            <div className="bg-red-900/40 border border-red-700 rounded-lg px-4 py-3">
              <p className="text-sm text-red-300">⚠️ {msg}</p>
            </div>
            <button
              onClick={() => setStep('idle')}
              className="w-full bg-slate-700 hover:bg-slate-600 text-white py-2 rounded-lg text-sm transition-colors"
            >
              Try again
            </button>
          </div>
        )}

        <button
          onClick={onClose}
          className="mt-4 w-full text-sm text-slate-500 hover:text-slate-300 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
