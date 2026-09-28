const map = {
  APPROVED:             'bg-emerald-900 text-emerald-300 border border-emerald-700',
  APPROVED_BY_BRIDGEKEY:'bg-emerald-900 text-emerald-200 border border-emerald-600',
  BLOCKED:              'bg-red-900 text-red-300 border border-red-700',
  BLOCKED_FAILED_SIGNATURE: 'bg-red-900 text-red-200 border border-red-700',
  PENDING_VERIFICATION: 'bg-amber-900 text-amber-300 border border-amber-700',
  STEP_UP_BRIDGEKEY:    'bg-amber-900 text-amber-300 border border-amber-700',
  ALLOW:                'bg-emerald-900 text-emerald-300 border border-emerald-700',
  BLOCK:                'bg-red-900 text-red-300 border border-red-700',
}

export default function StatusBadge({ status }) {
  const cls = map[status?.toUpperCase?.()] ?? 'bg-slate-800 text-slate-400 border border-slate-600'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      {status ?? '—'}
    </span>
  )
}
