/** 后端实体类型（金额字段为 Decimal 字符串）。 */

export interface Stock {
  id: number;
  symbol: string;
  market: string;
  name: string;
  name_en?: string | null;
  industry?: string | null;
  sector?: string | null;
  currency: string;
  is_etf: boolean;
}

/** 从外部数据源发现的候选股票（尚未或已登记） */
export interface DiscoverCandidate {
  symbol: string;
  market: string;
  name: string;
  currency: string;
  exchange: string;
  quote_type: string;
  yf_symbol: string;
  registered: boolean;
  stock_id: number | null;
}

export interface Holding {
  stock_id: number;
  symbol: string;
  market: string;
  name: string;
  currency: string;
  shares: string;
  avg_cost: string;
  cost_basis: string;
  last_price: string | null;
  market_value: string | null;
  unrealized_pnl: string | null;
  realized_pnl: string;
}

export interface PortfolioSummary {
  positions: number;
  total_cost: string;
  total_market_value: string | null;
  total_unrealized_pnl: string | null;
  total_realized_pnl: string;
  market_value_available: boolean;
}

export interface Transaction {
  id: number;
  stock_id: number;
  type: string;
  trade_date: string;
  quantity: string;
  price: string;
  currency: string;
  commission: string;
  tax: string;
  other_fees: string;
  journal_id: number | null;
  is_imported: boolean;
  notes?: string | null;
}

export interface Journal {
  id: number;
  stock_id: number;
  decision_type: string;
  thesis_category?: string | null;
  expected_horizon?: string | null;
  target_price?: string | null;
  stop_loss_price?: string | null;
  exit_condition?: string | null;
  confidence?: number | null;
  emotion?: string | null;
  thesis: string;
  risks?: string | null;
  tags?: string[] | null;
  is_locked: boolean;
  is_imported: boolean;
  locked_at?: string | null;
  created_at?: string | null;
}

export interface Review {
  id: number;
  journal_id: number;
  review_date: string;
  days_since_decision?: number | null;
  price_at_review?: string | null;
  pnl_pct?: string | null;
  benchmark_pnl_pct?: string | null;
  thesis_held?: boolean | null;
  luck_vs_skill?: string | null;
  lessons?: string | null;
  notes?: string | null;
}

/** 交易录入入参（含强制日志） */
export interface TransactionCreate {
  stock_id: number;
  type: "BUY" | "SELL";
  trade_date: string;
  quantity: string;
  price: string;
  currency: string;
  commission?: string;
  tax?: string;
  other_fees?: string;
  broker?: string;
  notes?: string;
  journal: {
    decision_type: string;
    thesis_category?: string;
    expected_horizon?: string;
    target_price?: string;
    stop_loss_price?: string;
    exit_condition?: string;
    confidence?: number;
    emotion?: string;
    thesis: string;
    risks?: string;
    tags?: string[];
  };
}
