// types/index.ts

export interface FundSummary {
  id:             number
  name:           string
  official_nav:   number
  nav_date:       string
  portfolio_date: string
  total_holdings: number
  created_at:     string
  updated_at:     string
}

export interface HoldingResult {
  name:             string
  isin:             string
  industry:         string
  quantity:         number
  pct_to_nav:       number
  trading_symbol:   string
  disclosed_price:  number
  prev_close:       number | null
  live_price:       number | null
  price_change_pct: number | null
  nav_impact_pct:   number
  status:           'priced' | 'unpriced'
}

export interface NAVResult {
  fund_id:            number
  fund_name:          string
  nav_date:           string
  portfolio_date:     string
  official_nav:       number
  estimated_nav:      number
  nav_change_abs:     number
  nav_change_pct:     number
  price_coverage_pct: number
  total_holdings:     number
  priced_count:       number
  unpriced_count:     number
  calculated_at:      string
  holdings:           HoldingResult[]
}

// null means auto-refresh is OFF
export type RefreshInterval = 15 | 30 | 60 | 300 | null