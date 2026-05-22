"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type {
  AnalyticsBundle,
  DailyTrendPoint,
  HourlyDemandPoint,
  PlatformSplit,
  StoreLeaderboardRow,
  WeatherImpact,
  ZonePerformance,
} from "@/lib/api";

const TEAL = "#5eead4";
const AMBER = "#fbbf24";
const CORAL = "#f87171";
const INDIGO = "#818cf8";
const PLATFORM_COLORS: Record<string, string> = {
  Blinkit: TEAL,
  "Swiggy Instamart": AMBER,
};

function Panel({ title, children, wide }: { title: string; children: React.ReactNode; wide?: boolean }) {
  return (
    <div className={`glass analytics-panel${wide ? " wide" : ""}`}>
      <div className="label" style={{ marginBottom: 14 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function OverviewCards({ overview }: { overview: AnalyticsBundle["overview"] }) {
  const cards = [
    { label: "Total GMV", value: `₹${(overview.gmv_inr / 1_000_000).toFixed(2)}M`, accent: true },
    { label: "Orders / Day", value: overview.orders_per_day.toLocaleString() },
    { label: "SLA Compliance", value: `${overview.sla_compliance_pct}%` },
    { label: "Avg Order Value", value: `₹${overview.avg_order_value_inr}` },
    { label: "P95 ETA", value: `${overview.p95_eta_minutes} min` },
    { label: "Avg Surge", value: `${overview.avg_surge_multiplier}×` },
  ];
  return (
    <div className="overview-grid">
      {cards.map((c) => (
        <div key={c.label} className="overview-card">
          <div className="label">{c.label}</div>
          <div className="value-sm" style={{ color: c.accent ? "var(--accent)" : undefined, marginTop: 6 }}>
            {c.value}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsDashboard({ data, loading }: { data: AnalyticsBundle | null; loading?: boolean }) {
  if (loading || !data) {
    return (
      <div className="analytics-shell">
        <div className="glass analytics-panel" style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
          Loading analytics…
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-shell">
      <Panel title="Business Overview · 14-Day Window" wide>
        <OverviewCards overview={data.overview} />
      </Panel>

      <div className="analytics-grid">
        <Panel title="Hourly Demand & ETA">
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={data.hourly_demand as HourlyDemandPoint[]}>
              <defs>
                <linearGradient id="orderGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={TEAL} stopOpacity={0.45} />
                  <stop offset="100%" stopColor={TEAL} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="hour" tick={{ fill: "#8b95a8", fontSize: 11 }} tickFormatter={(h) => `${h}h`} />
              <YAxis yAxisId="left" tick={{ fill: "#8b95a8", fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: "#8b95a8", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#0e1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
              />
              <Area yAxisId="left" type="monotone" dataKey="orders" stroke={TEAL} fill="url(#orderGrad)" name="Orders" />
              <Line yAxisId="right" type="monotone" dataKey="avg_eta_min" stroke={AMBER} dot={false} name="Avg ETA (min)" />
            </AreaChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Daily GMV & Order Trend">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.daily_trend as DailyTrendPoint[]}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: "#8b95a8", fontSize: 10 }} tickFormatter={(d) => d.slice(5)} />
              <YAxis yAxisId="left" tick={{ fill: "#8b95a8", fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: "#8b95a8", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#0e1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
              <Line yAxisId="left" type="monotone" dataKey="orders" stroke={INDIGO} dot={false} name="Orders" />
              <Line yAxisId="right" type="monotone" dataKey="gmv_inr" stroke={TEAL} dot={false} name="GMV (₹)" />
            </LineChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Zone Performance (Orders)">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.zone_performance as ZonePerformance[]} layout="vertical" margin={{ left: 8 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" horizontal={false} />
              <XAxis type="number" tick={{ fill: "#8b95a8", fontSize: 11 }} />
              <YAxis type="category" dataKey="zone" width={110} tick={{ fill: "#8b95a8", fontSize: 10 }} />
              <Tooltip contentStyle={{ background: "#0e1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
              <Bar dataKey="orders" fill={TEAL} radius={[0, 4, 4, 0]} name="Orders" />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Platform Market Share">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={data.platform_split as PlatformSplit[]}
                dataKey="orders"
                nameKey="platform"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={3}
              >
                {(data.platform_split as PlatformSplit[]).map((entry) => (
                  <Cell key={entry.platform} fill={PLATFORM_COLORS[entry.platform] ?? INDIGO} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "#0e1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
              <Legend formatter={(v) => <span style={{ color: "#eef2ff", fontSize: 12 }}>{v}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Monsoon Weather Impact">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.weather_impact as WeatherImpact[]}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="weather" tick={{ fill: "#8b95a8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#8b95a8", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#0e1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
              <Bar dataKey="sla_breach_pct" fill={CORAL} name="SLA Breach %" radius={[4, 4, 0, 0]} />
              <Bar dataKey="avg_surge" fill={AMBER} name="Avg Surge ×" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="ETA Distribution">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.eta_distribution}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="bucket" tick={{ fill: "#8b95a8", fontSize: 9 }} interval={1} angle={-25} textAnchor="end" height={50} />
              <YAxis tick={{ fill: "#8b95a8", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#0e1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
              <Bar dataKey="count" fill={INDIGO} name="Orders" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      </div>

      <Panel title="Dark Store Leaderboard" wide>
        <div className="leaderboard-wrap">
          <table className="leaderboard">
            <thead>
              <tr>
                <th>Store</th>
                <th>Zone</th>
                <th>Platform</th>
                <th>Orders</th>
                <th>GMV</th>
                <th>Avg ETA</th>
                <th>SLA Breach</th>
              </tr>
            </thead>
            <tbody>
              {(data.store_leaderboard as StoreLeaderboardRow[]).map((row) => (
                <tr key={row.store_id}>
                  <td>{row.name.replace(/^Blinkit · |^Swiggy Instamart · /, "")}</td>
                  <td>{row.zone}</td>
                  <td>{row.platform}</td>
                  <td>{row.orders.toLocaleString()}</td>
                  <td>₹{(row.gmv_inr / 1000).toFixed(0)}k</td>
                  <td>{row.avg_eta_min}m</td>
                  <td style={{ color: row.sla_breach_pct > 2 ? "var(--danger)" : "var(--accent)" }}>
                    {row.sla_breach_pct}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
