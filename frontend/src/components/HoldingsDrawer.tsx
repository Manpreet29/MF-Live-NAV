// HoldingsDrawer.tsx — slide-in panel showing full holdings breakdown
import { useState, useMemo } from 'react'
import type { HoldingResult } from '../types'

interface Props {
  fundName: string
  holdings: HoldingResult[]
  onClose:  () => void
}

export default function HoldingsDrawer({ fundName, holdings, onClose }: Props) {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'priced' | 'unpriced'>('all')
  const [sortBy, setSortBy] = useState<'pct_to_nav' | 'price_change_pct' | 'nav_impact_pct'>('pct_to_nav')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const list = useMemo(() => {
    let l = [...holdings]
    if (filter !== 'all') l = l.filter(h => h.status === filter)
    if (search.trim()) {
      const q = search.toLowerCase()
      l = l.filter(h => h.name.toLowerCase().includes(q) || h.isin.toLowerCase().includes(q))
    }
    l.sort((a, b) => {
      const av = (a as any)[sortBy] ?? (sortDir === 'asc' ? Infinity : -Infinity)
      const bv = (b as any)[sortBy] ?? (sortDir === 'asc' ? Infinity : -Infinity)
      return sortDir === 'asc' ? av - bv : bv - av
    })
    return l
  }, [holdings, filter, search, sortBy, sortDir])

  const toggle = (field: typeof sortBy) => {
    if (sortBy === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortBy(field); setSortDir('desc') }
  }

  const fmt = (n: number | null, d = 2) =>
    n == null ? '—' : n.toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d })

  const fmtChg = (n: number | null) =>
    n == null ? '—' : `${n >= 0 ? '+' : ''}${n.toFixed(4)}%`

  const th = (label: string, field?: typeof sortBy) => (
    <th
      key={label}
      onClick={() => field && toggle(field)}
      className={[
        'px-3 py-2.5 text-left text-xs font-semibold tracking-wide text-muted uppercase whitespace-nowrap',
        field ? 'cursor-pointer hover:text-ink select-none' : '',
      ].join(' ')}
    >
      {label}
      {field && sortBy === field && (sortDir === 'asc' ? ' ↑' : ' ↓')}
    </th>
  )

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-ink/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white w-full max-w-3xl h-full flex flex-col shadow-2xl animate-slide-up">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border flex-shrink-0">
          <div>
            <h3 className="font-display text-lg text-ink">{fundName}</h3>
            <p className="text-xs text-muted mt-0.5">{list.length} of {holdings.length} holdings shown</p>
          </div>
          <button onClick={onClose} className="text-muted hover:text-ink p-1.5 rounded-lg hover:bg-cream transition-colors">
            <XIcon />
          </button>
        </div>

        {/* Toolbar */}
        <div className="px-6 py-3 border-b border-border flex gap-3 flex-shrink-0">
          <div className="relative flex-1">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted">
              <SearchIcon />
            </span>
            <input
              type="text" placeholder="Search company or ISIN…"
              className="field pl-8 text-xs py-2"
              value={search} onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="flex rounded-lg border border-border overflow-hidden text-xs">
            {(['all','priced','unpriced'] as const).map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`px-3 py-2 capitalize transition-colors ${filter===f ? 'bg-ink text-paper' : 'bg-white text-muted hover:bg-cream'}`}>
                {f === 'all' ? `All (${holdings.length})`
                 : f === 'priced' ? `✓ ${holdings.filter(h=>h.status==='priced').length}`
                 : `— ${holdings.filter(h=>h.status==='unpriced').length}`}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto">
          <table className="w-full text-xs border-collapse">
            <thead className="sticky top-0 bg-cream border-b border-border">
              <tr>
                {th('Company')}
                {th('% NAV', 'pct_to_nav')}
                <th className="px-3 py-2.5 text-right text-xs font-semibold tracking-wide text-muted uppercase">Prev Close</th>
                <th className="px-3 py-2.5 text-right text-xs font-semibold tracking-wide text-muted uppercase">Live</th>
                {th('Change %', 'price_change_pct')}
                {th('NAV Impact', 'nav_impact_pct')}
              </tr>
            </thead>
            <tbody>
              {list.map((h, i) => (
                <tr key={h.isin}
                  className={`border-b border-border last:border-0 hover:bg-cream/40 transition-colors ${i%2===0 ? 'bg-white' : 'bg-paper/30'}`}>
                  <td className="px-3 py-2.5">
                    <div className="flex items-start gap-2">
                      <div className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${h.status==='priced' ? 'bg-gain' : 'bg-border'}`} />
                      <div>
                        <p className="font-medium text-ink">{h.name}</p>
                        <p className="font-mono text-muted">{h.isin}</p>
                        {h.trading_symbol && <p className="text-muted/60">{h.trading_symbol}.NS</p>}
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono text-ink">{h.pct_to_nav.toFixed(2)}%</td>
                  <td className="px-3 py-2.5 text-right font-mono text-ink">
                    {h.prev_close != null ? `₹${fmt(h.prev_close)}` : <span className="text-muted">—</span>}
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono text-ink">
                    {h.live_price != null ? `₹${fmt(h.live_price)}` : <span className="text-muted">—</span>}
                  </td>
                  <td className={`px-3 py-2.5 text-right font-mono font-medium ${
                    h.price_change_pct == null ? 'text-muted' :
                    h.price_change_pct >= 0    ? 'text-gain'  : 'text-loss'}`}>
                    {fmtChg(h.price_change_pct)}
                  </td>
                  <td className={`px-3 py-2.5 text-right font-mono font-medium ${
                    h.nav_impact_pct >= 0.001  ? 'text-gain' :
                    h.nav_impact_pct <= -0.001 ? 'text-loss' : 'text-muted'}`}>
                    {h.status === 'priced' ? `${h.nav_impact_pct >= 0 ? '+' : ''}${h.nav_impact_pct.toFixed(4)}` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="px-6 py-3 border-t border-border text-xs text-muted flex-shrink-0">
          Change % measured from yesterday's closing price · NAV Impact in percentage points (pp)
        </div>
      </div>
    </div>
  )
}

const XIcon      = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
const SearchIcon = () => <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
