// hooks/useAutoRefresh.ts
// Polls getAllNAV() at the chosen interval.
// Supports turning auto-refresh off entirely.
import { useState, useEffect, useRef, useCallback } from 'react'
import { getAllNAV } from '../api/client'
import type { NAVResult, RefreshInterval } from '../types'

export function useAutoRefresh(fundCount: number) {
  const [navMap,     setNavMap]     = useState<Record<number, NAVResult>>({})
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [error,      setError]      = useState<string | null>(null)
  const [interval,   setInterval_]  = useState<RefreshInterval | null>(30) // null = off

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }

  const refresh = useCallback(async () => {
    if (fundCount === 0) return
    setRefreshing(true)
    setError(null)
    try {
      const results = await getAllNAV()
      const map: Record<number, NAVResult> = {}
      results.forEach(r => { map[r.fund_id] = r })
      setNavMap(map)
      setLastUpdate(new Date())
    } catch (e) {
      setError(String(e))
    } finally {
      setRefreshing(false)
    }
  }, [fundCount])

  // Auto-refresh loop — only runs when interval is not null
  useEffect(() => {
    clearTimer()

    if (fundCount === 0 || interval === null) return

    refresh() // immediate first fetch

    const schedule = () => {
      timerRef.current = setTimeout(() => {
        if (!document.hidden) refresh()
        schedule()
      }, interval * 1000)
    }
    schedule()

    return clearTimer
  }, [interval, fundCount, refresh])

  return {
    navMap,
    refreshing,
    lastUpdate,
    error,
    interval,
    setInterval: setInterval_,
    refresh,
  }
}