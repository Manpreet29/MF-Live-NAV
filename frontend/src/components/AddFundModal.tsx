// AddFundModal.tsx — slide-in modal to add a new fund tracker
import { useState, useCallback, useRef } from 'react'
import { createFund } from '../api/client'

interface Props {
  onClose:  () => void
  onAdded:  () => void
}

export default function AddFundModal({ onClose, onAdded }: Props) {
  const [file,       setFile]       = useState<File | null>(null)
  const [name,       setName]       = useState('')
  const [nav,        setNav]        = useState('')
  const [navDate,    setNavDate]    = useState('')
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState<string | null>(null)
  const [dragging,   setDragging]   = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f?.name.endsWith('.xlsx')) setFile(f)
  }, [])

  const isValid = file && name.trim() && Number(nav) > 0 && navDate

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid || loading) return
    setLoading(true); setError(null)
    try {
      await createFund(file!, name.trim(), Number(nav), navDate)
      onAdded()
      onClose()
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-border">
          <div>
            <h2 className="font-display text-xl text-ink">Add Fund Tracker</h2>
            <p className="text-xs text-muted mt-0.5">Upload holdings once — tracked forever</p>
          </div>
          <button onClick={onClose} className="text-muted hover:text-ink transition-colors p-1">
            <XIcon />
          </button>
        </div>

        <form onSubmit={submit} className="px-6 py-5 flex flex-col gap-5">

          {/* File drop */}
          <div>
            <label className="label">Holdings Disclosure (.xlsx)</label>
            <div
              onClick={() => inputRef.current?.click()}
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              className={[
                'flex flex-col items-center justify-center gap-2 min-h-[110px]',
                'rounded-xl border-2 border-dashed cursor-pointer transition-all duration-150',
                dragging      ? 'border-gold bg-gold/5'
                : file        ? 'border-gold/60 bg-gold/5'
                : 'border-border hover:border-gold/40 hover:bg-cream/60',
              ].join(' ')}
            >
              <input ref={inputRef} type="file" accept=".xlsx,.xls" className="hidden"
                onChange={e => setFile(e.target.files?.[0] ?? null)} />
              {file ? (
                <>
                  <div className="w-8 h-8 rounded-full bg-gold/15 flex items-center justify-center text-gold-dark">
                    <FileOkIcon />
                  </div>
                  <p className="text-sm font-medium text-ink truncate max-w-[260px]">{file.name}</p>
                  <p className="text-xs text-muted">{(file.size/1024).toFixed(0)} KB · click to change</p>
                </>
              ) : (
                <>
                  <div className="w-8 h-8 rounded-full bg-cream flex items-center justify-center text-muted">
                    <UploadIcon />
                  </div>
                  <p className="text-sm text-ink font-medium">Drop .xlsx file here</p>
                  <p className="text-xs text-muted">HDFC monthly portfolio disclosure format</p>
                </>
              )}
            </div>
          </div>

          {/* Fund name */}
          <div>
            <label className="label">Fund Name</label>
            <input className="field" placeholder="e.g. HDFC Flexi Cap Fund"
              value={name} onChange={e => setName(e.target.value)} disabled={loading} />
          </div>

          {/* NAV + Date */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Official NAV (₹)</label>
              <input className="field" type="number" step="0.0001" min="0.0001"
                placeholder="e.g. 2118.33"
                value={nav} onChange={e => setNav(e.target.value)} disabled={loading} />
            </div>
            <div>
              <label className="label">NAV Date</label>
              <input className="field" type="date"
                value={navDate} onChange={e => setNavDate(e.target.value)} disabled={loading} />
            </div>
          </div>

          <p className="text-xs text-muted -mt-2">
            Enter yesterday's official NAV from{' '}
            <a href="https://www.amfiindia.com/nav-history-download"
               target="_blank" rel="noopener noreferrer"
               className="text-gold-dark underline">AMFI</a>.
            Update it daily for best accuracy.
          </p>

          {error && (
            <div className="flex gap-2 p-3 rounded-lg bg-loss-bg border border-loss/20 text-loss text-xs">
              <span className="flex-shrink-0">⚠</span>{error}
            </div>
          )}

          <button type="submit"
            disabled={!isValid || loading}
            className="btn-primary w-full"
          >
            {loading ? <><SpinIcon />Adding fund…</> : <>+ Add Fund Tracker</>}
          </button>
        </form>
      </div>
    </div>
  )
}

const XIcon      = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
const UploadIcon = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
const FileOkIcon = () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><polyline points="9 15 11 17 15 13"/></svg>
const SpinIcon   = () => <svg className="animate-spin-slow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
