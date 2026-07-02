// App.tsx — main dashboard
import { useState, useEffect } from 'react'
import { getHealth }       from './api/client'
import { useFunds }        from './hooks/useFunds'
import { useAutoRefresh }  from './hooks/useAutoRefresh'
import FundCard            from './components/FundCard'
import AddFundModal        from './components/AddFundModal'
import RefreshControls     from './components/RefreshControls'

export default function App() {
  const { funds, loading: fundsLoading, error: fundsError, reload, remove } = useFunds()
  const {
    navMap, refreshing, lastUpdate, error: navError,
    interval, setInterval, refresh,
  } = useAutoRefresh(funds.length)

  const [showAdd,    setShowAdd]    = useState(false)
  const [masterWarn, setMasterWarn] = useState(false)

  // Check instrument master on mount
  useEffect(() => {
    getHealth().then(h => {
      if (!h.instrument_master_loaded) setMasterWarn(true)
    }).catch(() => {})
  }, [])

  const handleAdded = () => { reload(); setTimeout(refresh, 500) }

  return (
    <div className="min-h-screen flex flex-col">

      {/* Instrument master warning */}
      {masterWarn && (
        <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 text-xs text-amber-800 flex items-center gap-2">
          <span>⚠</span>
          <span>
            Instrument master is empty — run{' '}
            <code className="font-mono bg-amber-100 px-1 rounded">
              python scripts/load_instrument_master.py
            </code>{' '}
            in the backend folder, then restart the server.
          </span>
          <button onClick={() => setMasterWarn(false)} className="ml-auto text-amber-600 hover:text-amber-800">✕</button>
        </div>
      )}

      {/* Header */}
      <header className="border-b border-border bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-ink flex items-center justify-center flex-shrink-0">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F7F4EF" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
                <polyline points="16 7 22 7 22 13"/>
              </svg>
            </div>
            <div>
              <h1 className="font-display text-xl text-ink leading-tight">MF Live NAV Tracker</h1>
              <p className="text-xs text-muted hidden sm:block">Live estimated NAV for Indian mutual funds</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {funds.length > 0 && (
              <RefreshControls
                interval={interval}
                onChange={setInterval}
                refreshing={refreshing}
                lastUpdate={lastUpdate}
                onRefresh={refresh}
                error={navError}
              />
            )}
            <button onClick={() => setShowAdd(true)} className="btn-primary text-sm flex-shrink-0">
              + Add Fund
            </button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">

        {/* Loading state */}
        {fundsLoading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1,2,3].map(i => (
              <div key={i} className="card animate-fade-in">
                <div className="h-5 w-36 bg-cream rounded shimmer mb-3" />
                <div className="h-3 w-24 bg-cream rounded shimmer mb-6" />
                <div className="h-10 w-48 bg-cream rounded-lg shimmer mb-2" />
                <div className="h-4 w-32 bg-cream rounded shimmer" />
              </div>
            ))}
          </div>
        )}

        {/* Error state */}
        {fundsError && (
          <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
            <div className="text-4xl">⚠</div>
            <p className="text-loss font-medium">{fundsError}</p>
            <p className="text-muted text-sm">Make sure the backend is running on port 8000.</p>
            <button onClick={reload} className="btn-primary mt-2">Retry</button>
          </div>
        )}

        {/* Empty state */}
        {!fundsLoading && !fundsError && funds.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 gap-5 text-center max-w-md mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-cream flex items-center justify-center text-3xl">📈</div>
            <div>
              <h2 className="font-display text-2xl text-ink mb-2">No funds tracked yet</h2>
              <p className="text-muted text-sm leading-relaxed">
                Add your first mutual fund tracker by uploading the monthly portfolio disclosure Excel
                from your AMC's website.
              </p>
            </div>
            <button onClick={() => setShowAdd(true)} className="btn-primary">
              + Add Your First Fund
            </button>
            <div className="text-left w-full bg-white rounded-xl border border-border p-4 text-xs text-muted space-y-2">
              <p className="font-semibold text-ink">How it works:</p>
              <p>① Download the monthly portfolio disclosure Excel from HDFC / Nippon / any AMC</p>
              <p>② Upload it here with the official NAV from AMFI</p>
              <p>③ Live NAV is estimated from Yahoo Finance prices and auto-refreshes</p>
              <p>④ Your holdings are saved — no need to re-upload every day</p>
            </div>
          </div>
        )}

        {/* Fund cards grid */}
        {!fundsLoading && !fundsError && funds.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {funds.map(fund => (
              <FundCard
                key={fund.id}
                fund={fund}
                nav={navMap[fund.id] ?? null}
                loading={refreshing && !navMap[fund.id]}
                onDeleted={remove}
                onUpdated={() => { reload(); refresh() }}
              />
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-4 px-6 text-xs text-muted text-center">
        MF Live NAV Tracker · Powered by Yahoo Finance · For informational purposes only
      </footer>

      {/* Add fund modal */}
      {showAdd && (
        <AddFundModal onClose={() => setShowAdd(false)} onAdded={handleAdded} />
      )}
    </div>
  )
}
