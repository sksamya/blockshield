// Central API helper – all calls proxy through Vite -> Flask :5000
const BASE = '/api'

async function req(method, path, body, headers = {}) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', ...headers },
  }
  if (body) opts.body = JSON.stringify(body)
  const res = await fetch(`${BASE}${path}`, opts)
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(data.error || 'Request failed'), { data, status: res.status })
  return data
}

// ── Carrier ──────────────────────────────────────────────────────────────────
export const carrier = {
  recordSwap: (phone, eventType = 'SIM_SWAP', carrierId = 'carrier-a') =>
    req('POST', '/carrier/event', { phone_number: phone, event_type: eventType, carrier_id: carrierId }),
  preNotify: (phone, duration = 86400, carrierId = 'carrier-a') =>
    req('POST', '/carrier/pre-notify', { phone_number: phone, carrier_id: carrierId, duration_seconds: duration }),
  events: () => req('GET', '/carrier/events'),
}

// ── Bank ─────────────────────────────────────────────────────────────────────
export const bank = {
  transfer: (bankId, payload) => req('POST', `/bank/${bankId}/transfer`, payload),
  stepUp: (bankId, transferId, signature, txHash) =>
    req('POST', `/bank/${bankId}/step-up`, { transfer_id: transferId, signature, tx_hash: txHash }),
  linkAccount: (bankId, customerId, phone) =>
    req('POST', `/bank/${bankId}/link-account`, { customer_id: customerId, phone_number: phone }),
  passwordReset: (bankId, payload) => req('POST', `/bank/${bankId}/password-reset`, payload),
  customers: (bankId) => req('GET', `/bank/${bankId}/customers`),
}

// ── Wallet / BridgeKey ───────────────────────────────────────────────────────
export const wallet = {
  getChallenge: (challengeId) => req('GET', `/wallet/challenge/${challengeId}`),
  verify: (challengeId, signature) => req('POST', '/wallet/verify', { challenge_id: challengeId, signature }),
  testSign: (challengeId, privateKey) =>
    req('POST', '/wallet/test-sign', { challenge_id: challengeId, private_key: privateKey }),
}

// ── Consortium ───────────────────────────────────────────────────────────────
export const consortium = {
  flagMule: (accountNumber, bankId, reason) =>
    req('POST', '/consortium/mule', { account_number: accountNumber, bank_id: bankId, reason }),
  checkMule: (accountNumber) => req('GET', `/consortium/mule/${accountNumber}`),
  anchors: () => req('GET', '/consortium/anchors'),
  audit: (bankId, eventRef) => req('GET', `/consortium/audit/${bankId}/${eventRef}`),
}

// ── Simulator ────────────────────────────────────────────────────────────────
export const simulator = {
  run: (scenario) => req('POST', '/simulator/run', { scenario }),
  summary: () => req('GET', '/simulator/summary'),
}
