# AGENTS.md

Guidance for AI coding agents (and humans) working on **SIM-Swap Shield** (`blockshield`).
Read this file first, then `README.md` for the full design.

## Project summary

Cross-carrier, cross-bank SIM-swap fraud prevention on the **MST Blockchain** (public, EVM-compatible L1), with **BridgeKey** as the trusted-device signer.

Core flow:

1. A carrier signs a SIM-swap event and records it on-chain as a keyed token plus metadata. No phone numbers or PII go on-chain.
2. Banks read the event, combine it with local signals (new device, location, password reset, amount), and score risk.
3. On a high score the bank refuses SMS OTP and requires a **trusted-device signature** (BridgeKey wallet signing a bank challenge).
4. The bank blocks or steps up, alerts the victim by email, stores the decision record off-chain, and anchors its `keccak256` hash on-chain.
5. Banks share mule/fraud flags through a shared registry so one bank's finding raises risk at the others.

This is a **prototype**. Carrier events, device and location signals, and ML risk scores are **simulated**. Never present them as real, and never make fraud-detection accuracy claims.

## Repository layout

The repo may not contain every directory yet. Create them as needed, following this structure:

```
contracts/   Solidity contracts and Foundry tests
carrier/     Simulated carrier core, signing gateway, pre-notification API
bank/        Auth gateway, risk engine, chain reader, alerts, decision log
wallet/      BridgeKey integration and fallback test signer
simulator/   Scenario runner (scripted timelines)
dashboard/   Live timeline, per-bank panels, chain view, audit page
deploy/      Docker Compose, deployment scripts, example configs
docs/        Architecture, threat model, demo script
```

The bank stack is **one codebase deployed twice** (Bank B and Bank C), each with its own config, database, and identity. Do not fork it into two implementations.

## Tech stack

| Layer | Choice |
|---|---|
| Chain | MST Blockchain testnet (primary), Anvil or Besu for local dev and CI |
| Contracts | Solidity + Foundry |
| Services | TypeScript (Node.js 20+) **or** Python 3.11+ (FastAPI). Pick one language for all services and stay consistent. |
| Wallet | BridgeKey (Chrome extension first, Android later); ethers.js test wallet as fallback |
| Cache | Redis or SQLite |
| Mail capture | MailHog |

Do not introduce a second service language, a second chain, or a new database without asking the maintainers.

## Setup and commands

```bash
cp deploy/.env.example deploy/.env
docker compose -f deploy/docker-compose.yml up -d     # local chain, Redis, MailHog
forge test --root contracts                            # contract tests
./deploy/scripts/deploy-local.sh                       # deploy locally
./simulator/run.sh fraud-swap                          # main demo scenario
```

MST testnet:

```bash
./deploy/scripts/deploy-mst-testnet.sh
docker compose -f deploy/docker-compose.yml --profile mst up -d
./simulator/run.sh fraud-swap
```

Dashboard: `http://localhost:3000`. MailHog: `http://localhost:8025`.

If a script or path above does not exist yet, create it rather than working around it, and update this file and the README.

## Smart contracts

| Contract | Responsibility |
|---|---|
| `SwapRegistry` | Carrier allowlist and public keys. `recordEvent()` verifies the carrier signature and rejects replayed nonces. Stores pre-notification entries with expiry. Emits `SwapRecorded(token, carrier, ts, preNotified)`. |
| `FraudRegistry` | Allowlisted banks flag mule accounts (keyed identifier, reporter, evidence hash, timestamp). Other banks can query flags. |
| `PolicyContract` | Governance-set parameters: recent-swap window (e.g. 72h), pre-notified window, step-up thresholds, whether SMS OTP is allowed after a swap. |
| `DecisionLog` | `anchor(bankId, eventRef, decisionHash, ts)`. Only registered banks can write. |

Invariants that must always hold (add or keep tests for each):

- Only allowlisted **carrier** addresses can write swap events. Only allowlisted **bank** addresses can write flags and decision anchors. Carrier, bank, and governance roles use separate addresses.
- A forged carrier signature is rejected.
- A replayed event nonce is rejected.
- An unregistered bank cannot write to `DecisionLog`.
- Nothing personal is ever stored or emitted on-chain.

Swap event schema (canonical JSON, **sorted keys** so hashes are reproducible):

```json
{
  "token": "0x...",
  "carrier_id": "carrier-a",
  "event_type": "SIM_SWAP | ESIM | PORT_OUT",
  "timestamp": 1790000000,
  "pre_notified": false,
  "notification_ref": "optional",
  "nonce": "0x...",
  "signature": "0x..."
}
```

Use the same canonical serialization everywhere a hash is computed (carrier signing, decision records, audit recompute). Put it in one shared module and import it.

## Privacy rules (non-negotiable)

- **MST is a public chain.** Assume everything written is world-readable forever. Permissioning is enforced in the contracts, not by the chain.
- Never write phone numbers, names, account numbers, or any PII on-chain, in logs, or in LLM prompts.
- The lookup token is `HMAC-SHA256(carrier_key, E.164 number)`. Never use a plain hash of a phone number, because the number space is small enough to brute-force.
- Decision records stay **off-chain**. Only `keccak256(canonical JSON)` is anchored.
- The wallet flow carries no PII: the wallet signs a nonce and returns a signature. The bank holds the address-to-customer binding.
- Known residual leak: timing, event frequency, and per-token history are visible. Do not claim otherwise in docs or demos.

## Trusted-device flow

1. **Enroll:** the customer verifies identity with the bank, connects BridgeKey, and signs an enrollment message. The bank stores `customer_id -> wallet address`.
2. **Challenge:** on `STEP_UP`, the bank issues a single-use nonce with a short expiry.
3. **Sign:** the customer approves in BridgeKey; the wallet signs the challenge (EIP-191 `personal_sign` or EIP-712).
4. **Verify:** the bank recovers the signer and compares it to the enrolled address. Match means proceed; anything else means deny.

Rules:

- Challenges are single-use and expire. Expired or reused challenges must be rejected (write a negative test).
- The signed message must bind the specific action (amount, payee, nonce, expiry) so a signature cannot be reused for a different action.
- BridgeKey's exact signing and connection method (deep link, WalletConnect, extension provider) is **unconfirmed**. Code to standard EVM message signing behind a small interface so the signer can be swapped, and keep the ethers.js test-wallet fallback working for CI.

## Risk engine conventions

- The decision (allow, step-up, block) must be **deterministic and rule-driven**. An ML score may be one input, but it is simulated and must be labeled as such.
- **Fail closed:** if a recent swap might exist but is not yet in the bank's cache (block time is about 3s, confirmations are configurable), high-value actions must step up rather than proceed.
- If an LLM is used to explain decisions, it explains only. It never makes or changes the decision, runs asynchronously (never blocks a transfer), receives only signal labels and hashes (no PII), and has a template fallback if the call fails.
- Legitimate swaps: a pre-notified swap lowers the score but never bypasses step-up for high-value or new-payee actions. Any mechanism that lets a customer pre-register a swap must itself require the trusted-device signature, not SMS OTP.
- Fraud flags are **risk signals, not verdicts**. They raise scores at other banks and should not auto-block on their own. Flags should expire, since phone numbers are recycled.

## Secrets and configuration

- All config comes from `deploy/.env`. Commit only `deploy/.env.example` with empty values. `.env` must stay in `.gitignore`.
- **Never commit** private keys, signing keys, token keys, RPC credentials, LLM API keys, or the MST MCP client secret. Keys in `.env.example` must be blank placeholders.
- Prototype keys are for testnet only. Do not reuse a key that ever held real funds.
- Contract addresses are written by deploy scripts. Do not hand-edit them into source files.

## Testing requirements

Run before every PR:

```bash
forge test --root contracts
# plus the end-to-end scenario suite against the local chain
```

Required coverage:

- **Contracts:** signature validation, replay protection, access control, gas.
- **End-to-end scenarios:** fraud swap (Bank B and Bank C), pre-notified swap, un-notified legitimate swap, old swap outside the window, mule-flag sharing, tampered decision record (recomputed hash must not match the on-chain anchor).
- **Negative tests:** forged carrier signature, replayed event, unregistered bank writing to `DecisionLog`, tampered decision record, expired or reused wallet challenge.
- **Performance targets** (measure on MST testnet, not just local): chain event to bank cache within a few seconds; risk decision under 200 ms.

Any change to a contract or a risk rule needs a test in the same PR.

## MST Buildathon requirements (if submitting to the track)

These are mandatory for prize eligibility, so do not break them:

- The project must deploy to **MST Testnet** and use MST as an integral part of the product, not a single isolated transaction.
- Keep a record of every MST Testnet **contract address** and at least one **real, verifiable transaction hash** (check on `testnet.mstscan.com`).
- The public repo must include contracts, frontend/backend code, and a README with MST integration details, contract addresses, and setup instructions. Keep the README's address table current after every deploy.
- **No fake or misleading deployment or transaction data.** Simulated carrier/device/location data is fine only when it is clearly labeled as simulated in the README, the UI, and any demo. Every tx hash or address shown must be real.
- BridgeKey integration is strongly recommended and should be the primary wallet in the demo.
- Everyone on the team must be able to explain the code. Keep the code simple and readable enough to defend.

## Code style and workflow

- Small, focused PRs. Add tests for behavior changes.
- Prefer clear, boring code over clever code. Comment the **why** for anything security-relevant (signature checks, replay protection, fail-closed logic).
- Do not add dependencies casually. Justify any new one in the PR description.
- Keep `README.md`, this file, and `docs/` in sync with behavior changes.
- Use conventional, descriptive commit messages.

## Do not

- Do not put PII, raw phone numbers, or plain phone hashes on-chain.
- Do not let SMS OTP satisfy a step-up requirement after a recent un-notified swap.
- Do not let an AI/LLM component make or alter a fraud decision.
- Do not commit secrets or hand-edit generated contract addresses.
- Do not present simulated data or vendor performance claims (MST ~3s blocks, ~0.001 MSTC fees, BridgeKey features) as independently verified.
- Do not silently expand scope. Ask before adding chains, languages, or major features.

## Open questions (do not guess, ask or verify)

- BridgeKey's exact signing and connection API.
- MST testnet RPC URL, chain ID, and finality/confirmation guidance (take from the official MST docs, do not invent values).
- Whether MST offers a permissioned deployment or private channel for production.
- Governance for `PolicyContract` parameters beyond the prototype multisig.
- Carrier-key discovery in production (the prototype tries all registered carrier keys; production should use a number-portability lookup).
