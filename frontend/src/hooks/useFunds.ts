// hooks/useFunds.ts — fund CRUD state
import { useState, useEffect, useCallback } from 'react'
import { getFunds, deleteFund } from '../api/client'
import type { FundSummary } from '../types'

export function useFunds() {
  const [funds,   setFunds]   = useState<FundSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setFunds(await getFunds())
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const remove = useCallback(async (id: number) => {
    await deleteFund(id)
    setFunds(prev => prev.filter(f => f.id !== id))
  }, [])

  return { funds, loading, error, reload: load, remove }
}
