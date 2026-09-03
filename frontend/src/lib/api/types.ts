// Types mirror Section F (API Contract) and Section G (JSON UI Mapping Matrix)
// of the Frontend Design & UX Specification. The frontend never derives or
// computes these values -- it only renders what the backend provides.

export type Direction = "BULLISH" | "BEARISH" | "NEUTRAL";
export type Sentiment = "POSITIVE" | "NEGATIVE" | "NEUTRAL";
export type AgentDecision = "TRADE" | "PASS";
export type RiskDecision = "ACCEPT" | "REJECT";
export type CheckResult = "PASS" | "FAIL";
export type ExecutionStatus =
  | "NOT_SUBMITTED"
  | "SUBMITTED"
  | "FILLED"
  | "REJECTED";
export type ExitStatus = "HOLDING" | "PENDING_EXIT" | "CLOSED";
export type PipelineStage =
  | "DATA_PROCESSING"
  | "MARKET_NEWS"
  | "OPTIONS"
  | "DECISION"
  | "RISK"
  | "EXECUTION"
  | "DONE";

export interface OptionLeg {
  side: "BUY" | "SELL";
  option_type: "CALL" | "PUT";
  strike: number;
  expiration: string;
  occ_symbol: string;
}

export interface DashboardResponse {
  equity: number | null;
  buying_power: number | null;
  daily_loss_used: number | null;
  daily_loss_limit: number | null;
  exposure_used: number | null;
  exposure_limit: number | null;
  open_positions: number | null;
  max_positions: number | null;
  updated_at: string | null;
  recent_activity: ActivityEvent[];
}

export interface ActivityEvent {
  id: string;
  timestamp: string;
  type: "TRADE" | "REJECT" | "EXIT" | "FILL" | "SYSTEM";
  message: string;
  symbol?: string;
}

export interface RiskChecks {
  [checkName: string]: CheckResult;
}

export interface PipelineCandidate {
  symbol: string;
  updated_at: string;
  stage: PipelineStage;
  scores: {
    trend: number | null;
    momentum: number | null;
    volume: number | null;
    filter_passed: boolean;
  };
  analysis: {
    direction: Direction | null;
    ai_confidence: number | null;
    summary: string | null;
  };
  news: {
    sentiment: Sentiment | null;
    news_score: number | null;
    headlines: string[];
  };
  strategy: {
    type: string | null;
    legs: OptionLeg[];
    max_loss: number | null;
    max_profit: number | null;
    breakeven: number[];
  } | null;
  decisions: Array<{
    decision: AgentDecision;
    reasoning: string;
    confidence: number | null;
  }>;
  evaluations: Array<{
    decision: RiskDecision;
    checks: RiskChecks;
    order: {
      contracts: number;
      capital_at_risk: number;
    } | null;
    binding_constraint: string | null;
    rejection_reasons: string[];
  }>;
  execution: {
    status: ExecutionStatus;
    order_id: string | null;
    filled_at: string | null;
  };
}

export type PositionLeg = OptionLeg;

export interface Position {
  strategy_id: string;
  symbol: string;
  strategy_type: string;
  quantity: number;
  legs: PositionLeg[];
  entry_price: number;
  current_value: number | null;
  unrealized_pnl: number | null;
  return_pct: number | null;
  max_loss: number | null;
  max_profit: number | null;
  breakeven: number[];
  dte: number | null;
  days_held: number;
  exit_status: ExitStatus;
  entry_time: string;
}

export interface JournalEntry {
  strategy_id: string;
  symbol: string;
  strategy_type: string;
  entry_time: string;
  entry_price: number;
  quantity: number;
  exit_time: string | null;
  exit_price: number | null;
  realized_pnl: number | null;
  return_pct: number | null;
  exit_reason: string | null;
  status: "OPEN" | "CLOSED";
}

export interface CloseTradeRequest {
  strategy_id: string;
}

export interface CloseTradeResponse {
  strategy_id: string;
  status: "SUBMITTED" | "FAILED";
  message: string;
}

export interface PipelineStatusResponse {
  is_running: boolean;
}
