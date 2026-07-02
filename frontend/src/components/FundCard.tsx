// FundCard.tsx — one card per tracked fund on the dashboard
import { useState } from 'react'
import type { FundSummary, NAVResult } from '../types'
import { updateFund, reuploadHoldings, deleteFund } from '../api/client'
import HoldingsDrawer from './HoldingsDrawer'

interface Props {
  fund:      FundSummary
  nav:       NAVResult | null
  loading:   boolean
  onDeleted: (id: number) => void
  onUpdated: () => void
}

export default function FundCard({ fund, nav, loading, onDeleted, onUpdated }: Props) {
  const [showDrawer,  setShowDrawer]  = useState(false)
  const [editNav,     setEditNav]     = useState(false)
  const [navInput,    setNavInput]    = useState(String(fund.official_nav))
  const [dateInput,   setDateInput]   = useState(fund.nav_date)
  const [saving,      setSaving]      = useState(false)
  const [uploading,   setUploading]   = useState(false)
  const [confirm,     setConfirm]     = useState(false)

  const isGain = nav ? nav.nav_change_pct >= 0 : null

  const fmtNav = (n: number) =>
    n.toLocaleString('en-IN', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
  const fmt2 = (n: number) =>
    n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

  const saveNav = async () => {
    if (!navInput || !dateInput) return
    setSaving(true)
    try {
      await updateFund(fund.id, {
        official_nav: Number(navInput),
        nav_date:     dateInput,
      })
      onUpdated()
      setEditNav(false)
    } finally { setSaving(false) }
  }

  const handleReupload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      await reuploadHoldings(fund.id, file)
      onUpdated()
    } finally { setUploading(false) }
  }

  const handleDelete = async () => {
    if (!confirm) { setConfirm(true); setTimeout(() => setConfirm(false), 3000); return }
    await deleteFund(fund.id)
    onDeleted(fund.id)
  }

  return (
    <>
      <div className="card flex flex-col gap-4 animate-fade-in relative">

        {/* Fund name + actions */}
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-display text-lg text-ink leading-tight">{fund.name}</h3>
            <p className="text-xs text-muted mt-0.5">
              {fund.total_holdings} holdings · {fund.portfolio_date || 'No disclosure uploaded'}
            </p>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            {/* Re-upload holdings */}
            <label title="Re-upload holdings statement"
              className="p-1.5 rounded-lg text-muted hover:text-ink hover:bg-cream cursor-pointer transition-colors">
              <input type="file" accept=".xlsx" className="hidden" onChange={handleReupload} />
              {uploading ? <SpinIcon /> : <UploadIcon />}
            </label>
            {/* Edit NAV */}
            <button onClick={() => setEditNav(v => !v)} title="Update official NAV"
              className={`p-1.5 rounded-lg transition-colors ${editNav ? 'bg-gold/15 text-gold-dark' : 'text-muted hover:text-ink hover:bg-cream'}`}>
              <EditIcon />
            </button>
            {/* Delete */}
            <button onClick={handleDelete} title={confirm ? 'Click again to confirm delete' : 'Delete fund'}
              className={`p-1.5 rounded-lg transition-colors ${confirm ? 'bg-loss-bg text-loss' : 'text-muted hover:text-loss hover:bg-loss-bg'}`}>
              <TrashIcon />
            </button>
          </div>
        </div>

        {/* Edit NAV panel */}
        {editNav && (
          <div className="flex gap-2 items-end p-3 bg-cream rounded-xl border border-border animate-fade-in">
            <div className="flex-1">
              <label className="label">Official NAV (₹)</label>
              <input className="field text-xs" type="number" step="0.0001"
                value={navInput} onChange={e => setNavInput(e.target.value)} />
            </div>
            <div className="flex-1">
              <label className="label">NAV Date</label>
              <input className="field text-xs" type="date"
                value={dateInput} onChange={e => setDateInput(e.target.value)} />
            </div>
            <button onClick={saveNav} disabled={saving}
              className="btn-primary text-xs px-4 py-2.5 mb-0.5 flex-shrink-0">
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        )}

        {/* Divider */}
        <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent" />

        {/* NAV display */}
        {loading && !nav ? (
          <div className="flex flex-col gap-2">
            <div className="h-10 w-48 bg-cream rounded-lg shimmer" />
            <div className="h-4 w-32 bg-cream rounded shimmer" />
          </div>
        ) : nav ? (
          <div>
            {/* Estimated NAV */}
            <p className="text-xs font-medium tracking-widest text-muted uppercase mb-1">
              Estimated Live NAV
            </p>
            <p className={`font-display text-4xl tracking-tight ${isGain ? 'text-gain' : 'text-loss'}`}>
              ₹{fmtNav(nav.estimated_nav)}
            </p>

            {/* Change badges */}
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span className={`chip text-xs font-medium ${isGain ? 'bg-gain-bg text-gain' : 'bg-loss-bg text-loss'}`}>
                {isGain ? '▲' : '▼'} {Math.abs(nav.nav_change_pct).toFixed(4)}%
              </span>
              <span className={`text-sm font-mono font-medium ${isGain ? 'text-gain' : 'text-loss'}`}>
                {isGain ? '+' : ''}₹{fmtNav(nav.nav_change_abs)}
              </span>
              <span className="text-xs text-muted">vs ₹{fmtNav(nav.official_nav)}</span>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-2 mt-4">
              {[
                ['Coverage',  `${fmt2(nav.price_coverage_pct)}%`],
                ['Priced',    `${nav.priced_count}/${nav.total_holdings}`],
                ['Updated',   new Date(nav.calculated_at).toLocaleTimeString('en-IN', {
                                hour: '2-digit', minute: '2-digit', second: '2-digit',
                                timeZone: 'Asia/Kolkata', hour12: true })],
              ].map(([label, value]) => (
                <div key={label} className="bg-cream rounded-lg p-2 text-center">
                  <p className="text-xs text-muted uppercase tracking-wide">{label}</p>
                  <p className="text-xs font-mono font-medium text-ink mt-0.5">{value}</p>
                </div>
              ))}
            </div>

            {/* Coverage bar */}
            <div className="mt-3">
              <div className="h-1 bg-border rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    nav.price_coverage_pct >= 90 ? 'bg-gain'
                    : nav.price_coverage_pct >= 70 ? 'bg-gold' : 'bg-loss'
                  }`}
                  style={{ width: `${Math.min(nav.price_coverage_pct, 100)}%` }}
                />
              </div>
            </div>

            {/* Holdings breakdown button */}
            <button
              onClick={() => setShowDrawer(true)}
              className="mt-3 w-full text-xs text-muted hover:text-ink border border-border hover:border-ink/30 rounded-lg py-2 transition-all"
            >
              View {nav.total_holdings} holdings breakdown →
            </button>
          </div>
        ) : (
          <div className="text-center py-4 text-sm text-muted">
            Waiting for first refresh…
          </div>
        )}
      </div>

      {/* Holdings drawer */}
      {showDrawer && nav && (
        <HoldingsDrawer
          fundName={fund.name}
          holdings={nav.holdings}
          onClose={() => setShowDrawer(false)}
        />
      )}
    </>
  )
}

const UploadIcon = () => <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
const EditIcon   = () => <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
const TrashIcon  = () => <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
const SpinIcon   = () => <svg className="animate-spin-slow" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"/></svg>
