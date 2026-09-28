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
  const [step, setStep]           = useState('idle') // idle | fetching | signing | done | error
  const [msg, setMsg]             = useState('')
  const [sig, setSig]             = useState('')
  const [onChainTx, setOnChainTx] = useState('')

  async function handleSign() {
    try {
      setStep('fetching')
      setMsg('')

      // Step 1 – fetch canonical challenge
      const challenge = await wallet.getChallenge(challengeId)
      const messageText = challenge.message_text
      if (!messageText) throw new Error('Backend challenge has no message_text')

      if (!window.ethereum) throw new Error('BridgeKey extension not detected. Install it from the Chrome Web Store.')

      setStep('signing')

      // Switch to MST Testnet (Chain ID: 91562037 -> 0x5752035)
      try {
        await window.ethereum.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: '0x5752035' }],
        })
      } catch (switchError) {
        if (switchError.code === 4902 || switchError?.data?.originalError?.code === 4902) {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [{
              chainId: '0x5752035',
              chainName: 'MST Testnet',
              nativeCurrency: { name: 'MST', symbol: 'MST', decimals: 18 },
              rpcUrls: ['https://testnetrpc.mstblockchain.com'],
              blockExplorerUrls: ['https://testnet.mstscan.com'],
            }],
          })
        }
      }

      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' })
      const walletAddress = accounts[0]

      // Step 2 – Submit a REAL on-chain authorization transaction directly from BridgeKey
      // This creates a permanent transaction in BridgeKey's Activity tab and on MSTScan
      let liveTxHash = ''
      try {
        const authDataHex = '0x' + Array.from(new TextEncoder().encode(`BlockShield:StepUp:${challengeId}`)).map(b => b.toString(16).padStart(2, '0')).join('')
        liveTxHash = await window.ethereum.request({
          method: 'eth_sendTransaction',
          params: [{
            from: walletAddress,
            to: walletAddress,
            value: '0x0',
            data: authDataHex,
          }],
        })
        setOnChainTx(liveTxHash)
      } catch (txErr) {
        console.warn('On-chain tx declined or error:', txErr)
      }

      // Step 3 – Get the EIP-191 biometric personal_sign signature
      const signature = await window.ethereum.request({
        method: 'personal_sign',
        params: [messageText, walletAddress],
      })

      setSig(signature)
      setStep('done')
      onSuccess({ signature, txHash: liveTxHash })
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
              <span className="font-semibold">Authentication Successful!</span>
            </div>
            {onChainTx && (
              <div className="bg-indigo-950/60 border border-indigo-700/60 rounded-lg px-3 py-2">
                <p className="text-xs text-indigo-300 font-semibold mb-1">🔗 On-Chain MST Transaction:</p>
                <a
                  href={`https://testnet.mstscan.com/tx/${onChainTx}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-indigo-400 hover:text-indigo-200 underline font-mono break-all block"
                >
                  {onChainTx} ↗
                </a>
              </div>
            )}
            <div className="bg-slate-900 rounded-lg px-3 py-2">
              <p className="text-xs text-slate-500 mb-1">Biometric Signature</p>
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
