import { useState, useEffect, useCallback } from 'react';
import LoadingSpinner from '../components/LoadingSpinner';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
  BarChart,
  Bar,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis
} from 'recharts';
import { formatIndianCurrency, formatPercent } from '../services/api';
import {
  getPortfolioOverview,
  getPnLBreakdown,
  getSectorAnalysis,
  getRiskMetrics,
  getAccountComparison,
  getPerformanceSummary,
  getTradingActivity
} from '../services/api';

const COLORS = ['#6366f1', '#22c55e', '#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4', '#f97316', '#84cc16', '#ec4899', '#14b8a6'];
const PERIOD_OPTIONS = [
  { label: '7D', value: 7 },
  { label: '30D', value: 30 },
  { label: '90D', value: 90 },
];

// ── Circular Score Gauge ──────────────────────────────────────────────────────
function ScoreGauge({ score, label, color }) {
  const radius = 54;
  const circ = 2 * Math.PI * radius;
  const progress = (score / 100) * circ;

  return (
    <div className="score-gauge">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r={radius} fill="none" stroke="#1e2535" strokeWidth="10" />
        <circle
          cx="70" cy="70" r={radius} fill="none"
          stroke={color}
          strokeWidth="10"
          strokeDasharray={`${progress} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 70 70)"
          style={{ transition: 'stroke-dasharray 1s ease' }}
        />
        <text x="70" y="66" textAnchor="middle" fontSize="26" fontWeight="bold" fill={color}>{score}</text>
        <text x="70" y="84" textAnchor="middle" fontSize="11" fill="#9ca3af">{label}</text>
      </svg>
    </div>
  );
}

// ── Metric Tile ───────────────────────────────────────────────────────────────
function MetricTile({ label, value, sub, valueClass, icon }) {
  return (
    <div className="analytics-metric-tile">
      <div className="analytics-tile-icon">{icon}</div>
      <div className="analytics-tile-body">
        <div className={`analytics-tile-value ${valueClass || ''}`}>{value}</div>
        <div className="analytics-tile-label">{label}</div>
        {sub && <div className="analytics-tile-sub">{sub}</div>}
      </div>
    </div>
  );
}

// ── Stock Row ─────────────────────────────────────────────────────────────────
function StockRow({ stock, pnl, pnlPercent, isGainer }) {
  return (
    <div className="analytics-stock-row">
      <div className="analytics-stock-name">{stock}</div>
      <div className={`analytics-stock-pnl ${isGainer ? 'positive' : 'negative'}`}>
        {isGainer ? '+' : ''}{formatIndianCurrency(pnl)}
      </div>
      <div className={`analytics-stock-pct ${isGainer ? 'positive' : 'negative'}`}>
        {formatPercent(pnlPercent)}
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function Analytics() {
  const [period, setPeriod] = useState(30);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  const [overview, setOverview] = useState(null);
  const [pnlBreakdown, setPnlBreakdown] = useState(null);
  const [sectorData, setSectorData] = useState(null);
  const [riskMetrics, setRiskMetrics] = useState(null);
  const [accountComparison, setAccountComparison] = useState([]);
  const [perfSummary, setPerfSummary] = useState(null);
  const [tradingActivity, setTradingActivity] = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, pnl, sector, risk, accounts, perf, activity] = await Promise.all([
        getPortfolioOverview(),
        getPnLBreakdown(),
        getSectorAnalysis(),
        getRiskMetrics(),
        getAccountComparison(),
        getPerformanceSummary(period),
        getTradingActivity(period),
      ]);
      setOverview(ov);
      setPnlBreakdown(pnl);
      setSectorData(sector);
      setRiskMetrics(risk);
      setAccountComparison(accounts);
      setPerfSummary(perf);
      setTradingActivity(activity);
    } catch (err) {
      console.error('Analytics fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  if (loading) {
    return (
      <div className="analytics-page">
        <div className="analytics-loading">
          <LoadingSpinner size="large" text="Calculating analytics..." />
        </div>
      </div>
    );
  }

  // ── Derived values ──
  const healthScore = overview ? Math.min(100, Math.round(
    (pnlBreakdown
      ? (pnlBreakdown.gainers_count / Math.max(1, pnlBreakdown.gainers_count + pnlBreakdown.losers_count)) * 40
      : 0) +
    (riskMetrics ? Math.max(0, 100 - riskMetrics.concentration_risk) * 0.3 : 0) +
    30
  )) : 0;

  const healthColor = healthScore >= 70 ? '#22c55e' : healthScore >= 45 ? '#f59e0b' : '#ef4444';
  const healthLabel = healthScore >= 70 ? 'Healthy' : healthScore >= 45 ? 'Fair' : 'Poor';

  // Win rate
  const totalStocks = (pnlBreakdown?.gainers_count || 0) + (pnlBreakdown?.losers_count || 0);
  const winRate = totalStocks > 0 ? ((pnlBreakdown?.gainers_count / totalStocks) * 100).toFixed(1) : 0;

  // Sector chart data
  const sectorChartData = sectorData?.sectors?.map(s => ({
    name: s.sector,
    value: parseFloat(s.percentage.toFixed(1)),
  })) || [];

  // Account bar data
  const accountBarData = accountComparison.map(a => ({
    name: a.account_name?.split(' ')[0] || `Acc-${a.account_id}`,
    value: a.total_value,
    pnl: a.pnl,
  }));

  // Radar chart data for risk profile
  const radarData = riskMetrics ? [
    { subject: 'Diversification', A: riskMetrics.diversification_score },
    { subject: 'Low Concentration', A: Math.max(0, 100 - riskMetrics.concentration_risk) },
    { subject: 'Win Rate', A: parseFloat(winRate) },
    { subject: 'Profit Stocks', A: totalStocks > 0 ? (pnlBreakdown.gainers_count / totalStocks) * 100 : 0 },
    { subject: 'Portfolio Health', A: healthScore },
  ] : [];

  const tabs = [
    { id: 'overview', label: '📊 Overview' },
    { id: 'pnl', label: '💹 P&L' },
    { id: 'risk', label: '🛡 Risk' },
    { id: 'accounts', label: '👤 Accounts' },
  ];

  return (
    <div className="analytics-page">
      {/* Header */}
      <div className="analytics-header">
        <div>
          <h1>📊 P&L Analytics</h1>
          <p className="analytics-subtitle">Portfolio health, performance &amp; risk metrics</p>
        </div>
        <div className="analytics-controls">
          <div className="period-pills">
            {PERIOD_OPTIONS.map(opt => (
              <button
                key={opt.value}
                className={`period-pill ${period === opt.value ? 'active' : ''}`}
                onClick={() => setPeriod(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <button className="btn-refresh-analytics" onClick={fetchAll}>↻ Refresh</button>
        </div>
      </div>

      {/* Tabs */}
      <div className="analytics-tabs">
        {tabs.map(t => (
          <button
            key={t.id}
            className={`analytics-tab ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ──────────────── OVERVIEW TAB ──────────────── */}
      {activeTab === 'overview' && (
        <div className="analytics-content">
          {/* Top KPIs */}
          <div className="analytics-kpi-row">
            <MetricTile
              icon="💰"
              label="Portfolio Value"
              value={formatIndianCurrency(overview?.total_value || 0)}
            />
            <MetricTile
              icon="📈"
              label="Total P&L"
              value={formatIndianCurrency(Math.abs(overview?.total_pnl || 0))}
              valueClass={overview?.total_pnl >= 0 ? 'positive' : 'negative'}
              sub={formatPercent(overview?.overall_pnl_percent || 0)}
            />
            <MetricTile
              icon="🏦"
              label="Invested"
              value={formatIndianCurrency(overview?.investment_value || 0)}
            />
            <MetricTile
              icon="📋"
              label="Holdings"
              value={overview?.holdings_count || 0}
              sub={`${overview?.positions_count || 0} positions`}
            />
          </div>

          {/* Health + Sector */}
          <div className="analytics-row-2col">
            {/* Health Gauge */}
            <div className="analytics-card">
              <h3>Portfolio Health Score</h3>
              <div className="health-gauge-row">
                <ScoreGauge score={healthScore} label={healthLabel} color={healthColor} />
                <div className="health-breakdown">
                  <div className="health-item">
                    <span>Win Rate</span>
                    <span className={parseFloat(winRate) >= 50 ? 'positive' : 'negative'}>{winRate}%</span>
                  </div>
                  <div className="health-item">
                    <span>Gainers</span>
                    <span className="positive">{pnlBreakdown?.gainers_count || 0} stocks</span>
                  </div>
                  <div className="health-item">
                    <span>Losers</span>
                    <span className="negative">{pnlBreakdown?.losers_count || 0} stocks</span>
                  </div>
                  <div className="health-item">
                    <span>Concentration</span>
                    <span className={riskMetrics?.concentration_risk > 50 ? 'negative' : 'positive'}>
                      {riskMetrics?.concentration_risk?.toFixed(1) || 0}%
                    </span>
                  </div>
                  <div className="health-item">
                    <span>Diversification</span>
                    <span className="positive">{riskMetrics?.diversification_score?.toFixed(1) || 0}/100</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Sector Pie */}
            <div className="analytics-card">
              <h3>Sector Allocation</h3>
              {sectorChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={230}>
                  <PieChart>
                    <Pie
                      data={sectorChartData}
                      dataKey="value"
                      nameKey="name"
                      cx="45%"
                      cy="50%"
                      outerRadius={85}
                      innerRadius={40}
                    >
                      {sectorChartData.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(v) => [`${v}%`, 'Allocation']}
                      contentStyle={{ background: '#111827', border: '1px solid #1e2535', borderRadius: '8px' }}
                    />
                    <Legend layout="vertical" align="right" verticalAlign="middle" iconSize={10} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="analytics-empty">No sector data available</div>
              )}
            </div>
          </div>

          {/* Trading Activity */}
          {tradingActivity && (
            <div className="analytics-card">
              <h3>Trading Activity ({period}D)</h3>
              <div className="activity-grid">
                <div className="activity-item">
                  <div className="activity-value">{tradingActivity.total_orders}</div>
                  <div className="activity-label">Total Orders</div>
                </div>
                <div className="activity-item">
                  <div className="activity-value positive">{tradingActivity.buy_orders}</div>
                  <div className="activity-label">Buy Orders</div>
                </div>
                <div className="activity-item">
                  <div className="activity-value negative">{tradingActivity.sell_orders}</div>
                  <div className="activity-label">Sell Orders</div>
                </div>
                <div className="activity-item">
                  <div className="activity-value">{tradingActivity.completed_orders}</div>
                  <div className="activity-label">Completed</div>
                </div>
                <div className="activity-item">
                  <div className="activity-value negative">{tradingActivity.rejected_orders}</div>
                  <div className="activity-label">Rejected</div>
                </div>
                <div className="activity-item">
                  <div className="activity-value">{formatIndianCurrency(tradingActivity.total_turnover)}</div>
                  <div className="activity-label">Turnover</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ──────────────── P&L TAB ──────────────── */}
      {activeTab === 'pnl' && (
        <div className="analytics-content">
          {/* P&L Summary */}
          <div className="analytics-kpi-row">
            <MetricTile
              icon="✅"
              label="Total Gains"
              value={formatIndianCurrency(pnlBreakdown?.total_gains || 0)}
              valueClass="positive"
            />
            <MetricTile
              icon="❌"
              label="Total Losses"
              value={formatIndianCurrency(Math.abs(pnlBreakdown?.total_losses || 0))}
              valueClass="negative"
            />
            <MetricTile
              icon="📊"
              label="Net P&L"
              value={formatIndianCurrency(Math.abs(pnlBreakdown?.net_pnl || 0))}
              valueClass={pnlBreakdown?.net_pnl >= 0 ? 'positive' : 'negative'}
            />
            <MetricTile
              icon="🎯"
              label="Win Rate"
              value={`${winRate}%`}
              valueClass={parseFloat(winRate) >= 50 ? 'positive' : 'negative'}
              sub={`${pnlBreakdown?.gainers_count || 0}W / ${pnlBreakdown?.losers_count || 0}L`}
            />
          </div>

          {/* Performance Summary */}
          {perfSummary && (
            <div className="analytics-card">
              <h3>Performance ({period}-Day Return)</h3>
              <div className="perf-summary-grid">
                <div className="perf-item">
                  <div className="perf-label">Start Value</div>
                  <div className="perf-value">{formatIndianCurrency(perfSummary.start_value)}</div>
                </div>
                <div className="perf-item">
                  <div className="perf-label">End Value</div>
                  <div className="perf-value">{formatIndianCurrency(perfSummary.end_value)}</div>
                </div>
                <div className="perf-item">
                  <div className="perf-label">Period Return</div>
                  <div className={`perf-value ${perfSummary.period_return >= 0 ? 'positive' : 'negative'}`}>
                    {formatIndianCurrency(Math.abs(perfSummary.period_return))}
                  </div>
                </div>
                <div className="perf-item">
                  <div className="perf-label">Return %</div>
                  <div className={`perf-value ${perfSummary.period_return_percent >= 0 ? 'positive' : 'negative'}`}>
                    {formatPercent(perfSummary.period_return_percent)}
                  </div>
                </div>
                {perfSummary.best_day && (
                  <div className="perf-item">
                    <div className="perf-label">Best Day</div>
                    <div className="perf-value positive">{formatIndianCurrency(perfSummary.best_day.pnl)}</div>
                    <div className="perf-sub">{new Date(perfSummary.best_day.date).toLocaleDateString('en-IN')}</div>
                  </div>
                )}
                {perfSummary.worst_day && (
                  <div className="perf-item">
                    <div className="perf-label">Worst Day</div>
                    <div className="perf-value negative">{formatIndianCurrency(Math.abs(perfSummary.worst_day.pnl))}</div>
                    <div className="perf-sub">{new Date(perfSummary.worst_day.date).toLocaleDateString('en-IN')}</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Gainers vs Losers */}
          <div className="analytics-row-2col">
            <div className="analytics-card">
              <h3>🟢 Top Gainers</h3>
              {pnlBreakdown?.top_gainers?.length > 0 ? (
                <div className="analytics-stock-list">
                  {pnlBreakdown.top_gainers.map((s, i) => (
                    <StockRow key={i} stock={s.stock} pnl={s.pnl} pnlPercent={s.pnl_percent} isGainer />
                  ))}
                </div>
              ) : (
                <div className="analytics-empty">No gainers found</div>
              )}
            </div>
            <div className="analytics-card">
              <h3>🔴 Top Losers</h3>
              {pnlBreakdown?.top_losers?.length > 0 ? (
                <div className="analytics-stock-list">
                  {pnlBreakdown.top_losers.map((s, i) => (
                    <StockRow key={i} stock={s.stock} pnl={s.pnl} pnlPercent={s.pnl_percent} isGainer={false} />
                  ))}
                </div>
              ) : (
                <div className="analytics-empty">No losers found</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ──────────────── RISK TAB ──────────────── */}
      {activeTab === 'risk' && (
        <div className="analytics-content">
          <div className="analytics-kpi-row">
            <MetricTile
              icon="⚖️"
              label="Concentration Risk"
              value={`${riskMetrics?.concentration_risk?.toFixed(1) || 0}%`}
              valueClass={riskMetrics?.concentration_risk > 50 ? 'negative' : 'positive'}
              sub="Single stock max exposure"
            />
            <MetricTile
              icon="🔀"
              label="Diversification"
              value={`${riskMetrics?.diversification_score?.toFixed(1) || 0}/100`}
              valueClass={riskMetrics?.diversification_score > 60 ? 'positive' : 'negative'}
            />
            <MetricTile
              icon="📉"
              label="Loss-Making Stocks"
              value={riskMetrics?.loss_making_stocks || 0}
              valueClass={riskMetrics?.loss_making_stocks > 0 ? 'negative' : 'positive'}
              sub={`${riskMetrics?.loss_making_percentage?.toFixed(1) || 0}% of portfolio`}
            />
            <MetricTile
              icon="📦"
              label="Total Stocks"
              value={riskMetrics?.total_stocks || 0}
            />
          </div>

          {/* Radar chart */}
          <div className="analytics-row-2col">
            <div className="analytics-card">
              <h3>Risk Profile Radar</h3>
              {radarData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#1e2535" />
                    <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: '#9ca3af' }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9, fill: '#6b7280' }} />
                    <Radar name="Portfolio" dataKey="A" stroke="#6366f1" fill="#6366f1" fillOpacity={0.35} />
                    <Tooltip
                      formatter={(v) => [`${v.toFixed(1)}`, '']}
                      contentStyle={{ background: '#111827', border: '1px solid #1e2535', borderRadius: '8px' }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              ) : (
                <div className="analytics-empty">No risk data available</div>
              )}
            </div>

            <div className="analytics-card">
              <h3>Risk Summary</h3>
              <div className="risk-table">
                {[
                  { label: 'Max Single Stock Exposure', value: formatIndianCurrency(riskMetrics?.max_single_stock_exposure || 0) },
                  { label: 'Loss Making %', value: `${riskMetrics?.loss_making_percentage?.toFixed(1) || 0}%`, negative: (riskMetrics?.loss_making_percentage || 0) > 30 },
                  { label: 'Concentration Risk', value: `${riskMetrics?.concentration_risk?.toFixed(1) || 0}%`, negative: (riskMetrics?.concentration_risk || 0) > 50 },
                  { label: 'Diversification Score', value: `${riskMetrics?.diversification_score?.toFixed(1) || 0}/100`, positive: (riskMetrics?.diversification_score || 0) > 60 },
                  { label: 'Win Rate', value: `${winRate}%`, positive: parseFloat(winRate) >= 50, negative: parseFloat(winRate) < 40 },
                ].map((row, i) => (
                  <div key={i} className="risk-row">
                    <span className="risk-label">{row.label}</span>
                    <span className={`risk-value ${row.positive ? 'positive' : row.negative ? 'negative' : ''}`}>
                      {row.value}
                    </span>
                  </div>
                ))}
              </div>

              <div className="risk-advice">
                {(riskMetrics?.concentration_risk || 0) > 50 && (
                  <div className="advice-item warning">
                    ⚠️ High concentration risk. Consider diversifying your portfolio.
                  </div>
                )}
                {parseFloat(winRate) < 40 && (
                  <div className="advice-item warning">
                    ⚠️ Win rate below 40%. Review your entry/exit criteria.
                  </div>
                )}
                {(riskMetrics?.loss_making_stocks || 0) === 0 && (
                  <div className="advice-item success">
                    ✅ All stocks are profitable! Great portfolio health.
                  </div>
                )}
                {(riskMetrics?.diversification_score || 0) > 70 && (
                  <div className="advice-item success">
                    ✅ Portfolio is well-diversified.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ──────────────── ACCOUNTS TAB ──────────────── */}
      {activeTab === 'accounts' && (
        <div className="analytics-content">
          {accountComparison.length > 0 ? (
            <>
              {/* Bar chart */}
              <div className="analytics-card">
                <h3>Account-wise Portfolio Value</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={accountBarData} barCategoryGap="30%">
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2535" />
                    <XAxis dataKey="name" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`} />
                    <Tooltip
                      formatter={(v) => [formatIndianCurrency(v), 'Value']}
                      contentStyle={{ background: '#111827', border: '1px solid #1e2535', borderRadius: '8px' }}
                    />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                      {accountBarData.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Account table */}
              <div className="analytics-card">
                <h3>Account Comparison</h3>
                <div className="table-container">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Account</th>
                        <th>Portfolio Value</th>
                        <th>Invested</th>
                        <th>P&L</th>
                        <th>P&L %</th>
                        <th>Holdings</th>
                        <th>Positions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {accountComparison.map((acc) => (
                        <tr key={acc.account_id}>
                          <td><strong style={{ color: 'var(--text-primary)' }}>{acc.account_name}</strong></td>
                          <td>{formatIndianCurrency(acc.total_value)}</td>
                          <td>{formatIndianCurrency(acc.investment_value)}</td>
                          <td className={acc.pnl >= 0 ? 'positive' : 'negative'}>
                            {formatIndianCurrency(Math.abs(acc.pnl))}
                          </td>
                          <td className={acc.pnl_percent >= 0 ? 'positive' : 'negative'}>
                            {formatPercent(acc.pnl_percent)}
                          </td>
                          <td>{acc.holdings_count}</td>
                          <td>{acc.positions_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="analytics-card">
              <div className="analytics-empty" style={{ padding: '60px 0' }}>
                <div style={{ fontSize: '48px' }}>👤</div>
                <div style={{ marginTop: '12px' }}>No accounts found.</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
