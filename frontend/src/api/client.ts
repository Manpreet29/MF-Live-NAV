// api/client.ts — all HTTP calls go through here
//
// In development: Vite proxy forwards /api/* → http://localhost:8000
// In production:  VITE_API_URL env variable points to Render backend URL
//   e.g. https://mf-nav-tracker-api.onrender.com

import axios, { AxiosError } from 'axios'
import type { FundSummary, NAVResult } from '../types'

// In production, VITE_API_URL is set in Vercel environment variables.
// In development, it's empty so baseURL defaults to '/' (Vite proxy handles it).
const BASE_URL = 'https://mf-live-nav-api.onrender.com'

const http = axios.create({
  baseURL: BASE_URL,
  timeout: 45_000,
})

// ---- Funds --------------------------------------------------------

export async function getFunds(): Promise<FundSummary[]> {
  const { data } = await http.get<FundSummary[]>('/api/funds')
  return data
}

export async function createFund(
  file: File,
  name: string,
  officialNav: number,
  navDate: string,
): Promise<{ id: number; name: string; total_holdings: number }> {
  const form = new FormData()
  form.append('file',         file)
  form.append('name',         name)
  form.append('official_nav', String(officialNav))
  form.append('nav_date',     navDate)
  try {
    const { data } = await http.post('/api/funds', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  } catch (e) { throw extractError(e) }
}

export async function updateFund(
  id: number,
  body: { name?: string; official_nav?: number; nav_date?: string },
): Promise<FundSummary> {
  try {
    const { data } = await http.patch<FundSummary>(`/api/funds/${id}`, body)
    return data
  } catch (e) { throw extractError(e) }
}

export async function deleteFund(id: number): Promise<void> {
  try { await http.delete(`/api/funds/${id}`) }
  catch (e) { throw extractError(e) }
}

export async function reuploadHoldings(id: number, file: File): Promise<void> {
  const form = new FormData()
  form.append('file', file)
  try {
    await http.post(`/api/funds/${id}/holdings`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  } catch (e) { throw extractError(e) }
}

// ---- NAV ----------------------------------------------------------

export async function getAllNAV(): Promise<NAVResult[]> {
  try {
    const { data } = await http.get<NAVResult[]>('/api/nav/all/batch')
    return data
  } catch (e) { throw extractError(e) }
}

export async function getOneNAV(fundId: number): Promise<NAVResult> {
  try {
    const { data } = await http.get<NAVResult>(`/api/nav/${fundId}`)
    return data
  } catch (e) { throw extractError(e) }
}

// ---- Health -------------------------------------------------------

export interface Health {
  status:                   string
  instrument_master_loaded: boolean
  instrument_master_count:  number
  tracked_funds:            number
}

export async function getHealth(): Promise<Health> {
  try {
    const { data } = await http.get<Health>('/api/health')
    return data
  } catch { throw 'Cannot reach backend.' }
}

// ---- Error helper -------------------------------------------------

function extractError(err: unknown): string {
  if (err instanceof AxiosError) {
    const d = err.response?.data
    if (d?.detail) return typeof d.detail === 'string' ? d.detail : JSON.stringify(d.detail)
    if (d?.message) return d.message
    if (!err.response) return 'Cannot reach backend. Is it running?'
    return `Server error ${err.response.status}`
  }
  return String(err)
}
