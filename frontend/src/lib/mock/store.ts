import {
  ActivityEvent,
  JournalEntry,
  PipelineCandidate,
  Position,
} from "@/lib/api/types";

// In-memory mock of the batch JSON files the FastAPI wrapper (Section M) would
// normally parse from local disk. This lets the frontend be demoed end-to-end
// against the exact response shapes defined in the API Contract (Section F)
// before the real backend wrapper exists. Swap NEXT_PUBLIC_API_BASE_URL to
// point at the real service once it's available -- no frontend code changes.

function minutesAgo(mins: number): string {
  return new Date(Date.now() - mins * 60_000).toISOString();
}

function daysAgo(days: number): string {
  return new Date(Date.now() - days * 86_400_000).toISOString();
}

export const seedActivity: ActivityEvent[] = [
  {
    id: "evt_1",
    timestamp: minutesAgo(2),
    type: "REJECT",
    message: "Risk Engine rejected TSLA: Daily Loss Capacity Exceeded",
    symbol: "TSLA",
  },
  {
    id: "evt_2",
    timestamp: minutesAgo(14),
    type: "FILL",
    message: "NVDA bull call spread filled at $3.10",
    symbol: "NVDA",
  },
  {
    id: "evt_3",
    timestamp: minutesAgo(31),
    type: "EXIT",
    message: "AAPL position closed: Take Profit target reached",
    symbol: "AAPL",
  },
  {
    id: "evt_4",
    timestamp: minutesAgo(47),
    type: "TRADE",
    message: "Decision Agent approved MSFT iron condor for Risk review",
    symbol: "MSFT",
  },
  {
    id: "evt_5",
    timestamp: minutesAgo(63),
    type: "SYSTEM",
    message: "Pipeline scan completed: 42 candidates processed",
  },
];

export const candidates: PipelineCandidate[] = [
  {
    symbol: "NVDA",
    updated_at: minutesAgo(14),
    stage: "DONE",
    scores: { trend: 0.87, momentum: 0.72, volume: 1.4, filter_passed: true },
    analysis: {
      direction: "BULLISH",
      ai_confidence: 0.81,
      summary:
        "Strong uptrend intact above 20/50 EMA with accelerating volume ahead of earnings.",
    },
    news: {
      sentiment: "POSITIVE",
      news_score: 0.64,
      headlines: [
        "NVDA raises data center revenue guidance",
        "Analysts lift price targets ahead of print",
      ],
    },
    strategy: {
      type: "Bull Call Spread",
      legs: [
        {
          side: "BUY",
          option_type: "CALL",
          strike: 850,
          expiration: "2026-10-16",
          occ_symbol: "NVDA261016C00850000",
        },
        {
          side: "SELL",
          option_type: "CALL",
          strike: 880,
          expiration: "2026-10-16",
          occ_symbol: "NVDA261016C00880000",
        },
      ],
      max_loss: 2450,
      max_profit: 550,
      breakeven: [852.45],
    },
    decisions: [
      {
        decision: "TRADE",
        reasoning:
          "Bullish technical + news alignment with defined-risk structure. Directional bias confirmed by both sentiment score (0.64) and trend score (0.87).",
        confidence: 0.81,
      },
    ],
    evaluations: [
      {
        decision: "ACCEPT",
        checks: {
          per_trade_capacity: "PASS",
          exposure_capacity: "PASS",
          account_risk_capacity: "PASS",
          daily_loss_capacity: "PASS",
          buying_power_capacity: "PASS",
          open_position_capacity: "PASS",
        },
        order: { contracts: 10, capital_at_risk: 2450 },
        binding_constraint: "exposure_capacity",
        rejection_reasons: [],
      },
    ],
    execution: {
      status: "FILLED",
      order_id: "ord_8f21ac",
      filled_at: minutesAgo(13),
    },
  },
  {
    symbol: "TSLA",
    updated_at: minutesAgo(2),
    stage: "DONE",
    scores: { trend: 0.61, momentum: 0.55, volume: 1.1, filter_passed: true },
    analysis: {
      direction: "BULLISH",
      ai_confidence: 0.58,
      summary:
        "Moderate bullish setup with elevated IV; risk/reward acceptable but crowded trade.",
    },
    news: {
      sentiment: "POSITIVE",
      news_score: 0.41,
      headlines: ["TSLA deliveries beat estimates for the quarter"],
    },
    strategy: {
      type: "Bull Put Spread",
      legs: [
        {
          side: "SELL",
          option_type: "PUT",
          strike: 240,
          expiration: "2026-10-09",
          occ_symbol: "TSLA261009P00240000",
        },
        {
          side: "BUY",
          option_type: "PUT",
          strike: 230,
          expiration: "2026-10-09",
          occ_symbol: "TSLA261009P00230000",
        },
      ],
      max_loss: 6200,
      max_profit: 800,
      breakeven: [238.0],
    },
    decisions: [
      {
        decision: "TRADE",
        reasoning:
          "Directional bias is bullish with sufficient news confirmation to warrant a defined-risk credit spread.",
        confidence: 0.58,
      },
    ],
    evaluations: [
      {
        decision: "REJECT",
        checks: {
          per_trade_capacity: "PASS",
          exposure_capacity: "PASS",
          account_risk_capacity: "PASS",
          daily_loss_capacity: "FAIL",
          buying_power_capacity: "PASS",
          open_position_capacity: "PASS",
        },
        order: null,
        binding_constraint: "daily_loss_capacity",
        rejection_reasons: [
          "Daily Loss Capacity Exceeded: realized + open risk of $6,200 would breach remaining daily loss budget of $4,150",
        ],
      },
    ],
    execution: {
      status: "NOT_SUBMITTED",
      order_id: null,
      filled_at: null,
    },
  },
  {
    symbol: "MSFT",
    updated_at: minutesAgo(47),
    stage: "RISK",
    scores: { trend: 0.52, momentum: 0.3, volume: 0.9, filter_passed: true },
    analysis: {
      direction: "NEUTRAL",
      ai_confidence: 0.49,
      summary:
        "Range-bound price action following guidance reset; low realized volatility favors premium selling.",
    },
    news: {
      sentiment: "NEUTRAL",
      news_score: 0.05,
      headlines: ["MSFT Azure growth roughly in line with expectations"],
    },
    strategy: {
      type: "Iron Condor",
      legs: [
        {
          side: "SELL",
          option_type: "PUT",
          strike: 400,
          expiration: "2026-10-16",
          occ_symbol: "MSFT261016P00400000",
        },
        {
          side: "BUY",
          option_type: "PUT",
          strike: 390,
          expiration: "2026-10-16",
          occ_symbol: "MSFT261016P00390000",
        },
        {
          side: "SELL",
          option_type: "CALL",
          strike: 450,
          expiration: "2026-10-16",
          occ_symbol: "MSFT261016C00450000",
        },
        {
          side: "BUY",
          option_type: "CALL",
          strike: 460,
          expiration: "2026-10-16",
          occ_symbol: "MSFT261016C00460000",
        },
      ],
      max_loss: 8500,
      max_profit: 1500,
      breakeven: [398.5, 451.5],
    },
    decisions: [
      {
        decision: "TRADE",
        reasoning:
          "Low directional conviction combined with compressed realized volatility supports a neutral, defined-risk premium sale.",
        confidence: 0.49,
      },
    ],
    evaluations: [],
    execution: { status: "NOT_SUBMITTED", order_id: null, filled_at: null },
  },
  {
    symbol: "AMD",
    updated_at: minutesAgo(58),
    stage: "DECISION",
    scores: { trend: 0.34, momentum: -0.12, volume: 0.7, filter_passed: true },
    analysis: {
      direction: "BEARISH",
      ai_confidence: 0.44,
      summary:
        "Momentum rolling over below key moving averages; sentiment mixed heading into competitor earnings.",
    },
    news: {
      sentiment: "NEGATIVE",
      news_score: -0.22,
      headlines: ["AMD faces margin pressure amid pricing competition"],
    },
    strategy: null,
    decisions: [
      {
        decision: "PASS",
        reasoning:
          "Directional signal is weak and inconsistent across timeframes; insufficient conviction to size a defined-risk trade.",
        confidence: 0.44,
      },
    ],
    evaluations: [],
    execution: { status: "NOT_SUBMITTED", order_id: null, filled_at: null },
  },
  {
    symbol: "AAPL",
    updated_at: minutesAgo(65),
    stage: "MARKET_NEWS",
    scores: { trend: 0.71, momentum: 0.4, volume: 1.05, filter_passed: true },
    analysis: {
      direction: "BULLISH",
      ai_confidence: 0.67,
      summary:
        "Steady accumulation pattern with supportive breadth across the sector.",
    },
    news: {
      sentiment: "POSITIVE",
      news_score: 0.38,
      headlines: ["AAPL services revenue hits new record"],
    },
    strategy: null,
    decisions: [],
    evaluations: [],
    execution: { status: "NOT_SUBMITTED", order_id: null, filled_at: null },
  },
  {
    symbol: "PLTR",
    updated_at: minutesAgo(71),
    stage: "DATA_PROCESSING",
    scores: {
      trend: 0.18,
      momentum: -0.35,
      volume: 0.6,
      filter_passed: false,
    },
    analysis: { direction: null, ai_confidence: null, summary: null },
    news: { sentiment: null, news_score: null, headlines: [] },
    strategy: null,
    decisions: [],
    evaluations: [],
    execution: { status: "NOT_SUBMITTED", order_id: null, filled_at: null },
  },
];

export const positions: Position[] = [
  {
    strategy_id: "pos_nvda_bcs_01",
    symbol: "NVDA",
    strategy_type: "Bull Call Spread",
    quantity: 10,
    legs: [
      {
        side: "BUY",
        option_type: "CALL",
        strike: 850,
        expiration: "2026-10-16",
        occ_symbol: "NVDA261016C00850000",
      },
      {
        side: "SELL",
        option_type: "CALL",
        strike: 880,
        expiration: "2026-10-16",
        occ_symbol: "NVDA261016C00880000",
      },
    ],
    entry_price: 2.45,
    current_value: 3.1,
    unrealized_pnl: 650.0,
    return_pct: 26.5,
    max_loss: 2450.0,
    max_profit: 550.0,
    breakeven: [852.45],
    dte: 21,
    days_held: 4,
    exit_status: "HOLDING",
    entry_time: daysAgo(4),
  },
  {
    strategy_id: "pos_msft_ic_02",
    symbol: "MSFT",
    strategy_type: "Iron Condor",
    quantity: 5,
    legs: [
      {
        side: "SELL",
        option_type: "PUT",
        strike: 400,
        expiration: "2026-10-16",
        occ_symbol: "MSFT261016P00400000",
      },
      {
        side: "BUY",
        option_type: "PUT",
        strike: 390,
        expiration: "2026-10-16",
        occ_symbol: "MSFT261016P00390000",
      },
      {
        side: "SELL",
        option_type: "CALL",
        strike: 450,
        expiration: "2026-10-16",
        occ_symbol: "MSFT261016C00450000",
      },
      {
        side: "BUY",
        option_type: "CALL",
        strike: 460,
        expiration: "2026-10-16",
        occ_symbol: "MSFT261016C00460000",
      },
    ],
    entry_price: 3.0,
    current_value: 4.9,
    unrealized_pnl: -950.0,
    return_pct: -63.3,
    max_loss: 8500.0,
    max_profit: 1500.0,
    breakeven: [398.5, 451.5],
    dte: 21,
    days_held: 6,
    exit_status: "PENDING_EXIT",
    entry_time: daysAgo(6),
  },
  {
    strategy_id: "pos_amzn_bps_03",
    symbol: "AMZN",
    strategy_type: "Bull Put Spread",
    quantity: 8,
    legs: [
      {
        side: "SELL",
        option_type: "PUT",
        strike: 180,
        expiration: "2026-10-02",
        occ_symbol: "AMZN261002P00180000",
      },
      {
        side: "BUY",
        option_type: "PUT",
        strike: 175,
        expiration: "2026-10-02",
        occ_symbol: "AMZN261002P00175000",
      },
    ],
    entry_price: 1.2,
    current_value: 0.55,
    unrealized_pnl: 520.0,
    return_pct: 54.2,
    max_loss: 2800.0,
    max_profit: 960.0,
    breakeven: [178.8],
    dte: 7,
    days_held: 11,
    exit_status: "HOLDING",
    entry_time: daysAgo(11),
  },
];

export const journal: JournalEntry[] = [
  {
    strategy_id: "pos_aapl_bcs_00",
    symbol: "AAPL",
    strategy_type: "Bull Call Spread",
    entry_time: daysAgo(9),
    entry_price: 1.85,
    quantity: 12,
    exit_time: minutesAgo(31),
    exit_price: 3.4,
    realized_pnl: 1860.0,
    return_pct: 83.8,
    exit_reason: "Take Profit (>50%)",
    status: "CLOSED",
  },
  {
    strategy_id: "pos_googl_ic_00",
    symbol: "GOOGL",
    strategy_type: "Iron Condor",
    entry_time: daysAgo(15),
    entry_price: 2.6,
    quantity: 6,
    exit_time: daysAgo(9),
    exit_price: 4.9,
    realized_pnl: -1380.0,
    return_pct: -88.5,
    exit_reason: "Stop Loss Triggered",
    status: "CLOSED",
  },
  {
    strategy_id: "pos_tsla_bps_00",
    symbol: "TSLA",
    strategy_type: "Bull Put Spread",
    entry_time: daysAgo(20),
    entry_price: 1.1,
    quantity: 10,
    exit_time: daysAgo(13),
    exit_price: 0.2,
    realized_pnl: 900.0,
    return_pct: 81.8,
    exit_reason: "Expired Worthless",
    status: "CLOSED",
  },
  {
    strategy_id: "pos_meta_bcs_00",
    symbol: "META",
    strategy_type: "Bull Call Spread",
    entry_time: daysAgo(24),
    entry_price: 3.2,
    quantity: 4,
    exit_time: daysAgo(20),
    exit_price: 1.4,
    realized_pnl: -720.0,
    return_pct: -56.3,
    exit_reason: "Stop Loss Triggered",
    status: "CLOSED",
  },
];

export const dashboardState = {
  equity: 128450.32,
  buying_power: 64200.11,
  daily_loss_used: 2050.0,
  daily_loss_limit: 6200.0,
  exposure_used: 18400.0,
  exposure_limit: 30000.0,
  open_positions: positions.length,
  max_positions: 8,
  updated_at: minutesAgo(1),
};

export function closePosition(strategyId: string) {
  const idx = positions.findIndex((p) => p.strategy_id === strategyId);
  if (idx === -1) return null;
  const pos = positions[idx];
  positions.splice(idx, 1);
  journal.unshift({
    strategy_id: pos.strategy_id,
    symbol: pos.symbol,
    strategy_type: pos.strategy_type,
    entry_time: pos.entry_time,
    entry_price: pos.entry_price,
    quantity: pos.quantity,
    exit_time: new Date().toISOString(),
    exit_price: pos.current_value,
    realized_pnl: pos.unrealized_pnl,
    return_pct: pos.return_pct,
    exit_reason: "Manual Close (User Initiated)",
    status: "CLOSED",
  });
  dashboardState.open_positions = positions.length;
  seedActivity.unshift({
    id: `evt_${Date.now()}`,
    timestamp: new Date().toISOString(),
    type: "EXIT",
    message: `${pos.symbol} position manually closed by user`,
    symbol: pos.symbol,
  });
  return pos;
}
