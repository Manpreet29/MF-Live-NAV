// RefreshControls.tsx — interval picker with Off option + manual refresh
import type { RefreshInterval } from '../types'

interface Props {
  interval:   RefreshInterval
  onChange:   (v: RefreshInterval) => void
  refreshing: boolean
  lastUpdate: Date | null
  onRefresh:  () => void
  error:      string | null
}

const OPTIONS: { value: RefreshInterval; label: string }[] = [
  { value: 15,   label: '15s' },
  { value: 30,   label: '30s' },
  { value: 60,   label: '1m'  },
  { value: 300,  label: '5m'  },
  { value: null, label: 'Off' },
]

export default function RefreshControls({
  interval, onChange, refreshing, lastUpdate, onRefresh, error,
}: Props) {
  const timeStr = lastUpdate
    ? lastUpdate.toLocaleTimeString('en-IN', {
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        timeZone: 'Asia/Kolkata', hour12: true,
      })
    : null

  return (
    <div className="flex flex-wrap items-center gap-3">

      {/* Interval selector */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted">Auto-refresh:</span>
        <div className="flex rounded-lg border border-border overflow-hidden">
          {OPTIONS.map(o => {
            const isActive = interval === o.value
            const isOff    = o.value === null
            return (
              <button
                key={String(o.value)}
                onClick={() => onChange(o.value)}
                className={[
                  'px-3 py-1.5 text-xs font-medium transition-colors',
                  isActive && isOff
                    ? 'bg-loss text-white'
                    : isActive
                    ? 'bg-ink text-paper'
                    : isOff
                    ? 'bg-white text-muted hover:bg-loss-bg hover:text-loss'
                    : 'bg-white text-muted hover:bg-cream',
                ].join(' ')}
              >
                {o.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Manual refresh button */}
      <button
        onClick={onRefresh}
        disabled={refreshing}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs text-muted hover:text-ink hover:border-ink/30 transition-all disabled:opacity-50"
      >
        <span className={refreshing ? 'animate-spin-slow inline-block' : 'inline-block'}>
          ⟳
        </span>
        {refreshing ? 'Fetching…' : 'Refresh now'}
      </button>

      {/* Status line */}
      {interval === null && !refreshing && (
        <span className="text-xs text-muted italic">
          Auto-refresh off — use Refresh now to update
        </span>
      )}
      {timeStr && interval !== null && !error && (
        <span className="text-xs text-muted">Updated {timeStr} IST</span>
      )}
      {timeStr && interval === null && !error && (
        <span className="text-xs text-muted">Last updated {timeStr} IST</span>
      )}
      {error && (
        <span className="text-xs text-loss">⚠ {error}</span>
      )}
    </div>
  )
}