import { PRIORITY_CLASSES, STATUS_LABELS } from '../lib/constants'
import type { EmergencyStatus, Priority } from '../lib/types'

export function PriorityBadge({ priority }: { priority: Priority }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold ring-1 ring-inset ${PRIORITY_CLASSES[priority]}`}
    >
      {priority}
    </span>
  )
}

const STATUS_CLASSES: Record<string, string> = {
  RECEIVED: 'bg-slate-100 text-slate-700',
  TRIAGED: 'bg-indigo-100 text-indigo-800',
  ASSIGNED: 'bg-sky-100 text-sky-800',
  IN_PROGRESS: 'bg-amber-100 text-amber-900',
  RESOLVED: 'bg-emerald-100 text-emerald-800',
  CANCELLED: 'bg-slate-200 text-slate-500 line-through',
}

export function StatusBadge({ status }: { status: EmergencyStatus | string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
        STATUS_CLASSES[status] ?? 'bg-slate-100 text-slate-700'
      }`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}
