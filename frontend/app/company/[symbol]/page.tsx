"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Building2,
  Globe,
  Users,
  Calendar,
  TrendingUp,
  TrendingDown,
  BarChart3,
  PieChart,
  Newspaper,
  Shield,
  Activity,
  DollarSign,
  Loader2,
  ExternalLink,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

/* ── Types ──────────────────────────────────────────────────── */
interface Profile {
  name: string;
  english_name: string;
  exchange: string;
  industry: string;
  sector: string;
  founded: string;
  listed_date: string;
  address: string;
  website: string;
  employees: number;
  outstanding_shares: number;
  market_cap: number;
}

interface Quarter {
  period: string;
  revenue: number;
  net_profit: number;
  eps: number;
  roe: number;
}

interface Financials {
  pe_ratio: number;
  pb_ratio: number;
  eps_ttm: number;
  roe_ttm: number;
  roa_ttm: number;
  debt_to_equity: number;
  current_ratio: number;
  dividend_yield: number;
  beta: number;
  revenue_ttm: number;
  profit_ttm: number;
  quarterly: Quarter[];
}

interface Technicals {
  rsi_14: number;
  macd: number;
  macd_signal: number;
  ma_20: number;
  ma_50: number;
  ma_200: number;
  bollinger_upper: number;
  bollinger_lower: number;
  atr_14: number;
  adx: number;
  cci: number;
  stochastic_k: number;
  stochastic_d: number;
  obv_trend: string;
  support: number;
  resistance: number;
}

interface Holder {
  name: string;
  shares: number;
  pct: number;
}

interface Ownership {
  foreign_pct: number;
  insider_pct: number;
  state_pct: number;
  free_float_pct: number;
  foreign_room_remaining: number;
  top_holders: Holder[];
}

interface NewsItem {
  title: string;
  date: string;
  source: string;
  sentiment: string;
}

interface CompanyData {
  symbol: string;
  profile: Profile;
  financials: Financials;
  technicals: Technicals;
  ownership: Ownership;
  news: NewsItem[];
}

/* ── Helpers ────────────────────────────────────────────────── */
function fmtVND(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)} nghìn tỷ`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)} tỷ`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)} triệu`;
  return value.toLocaleString("vi-VN");
}

function fmtNum(value: number): string {
  return value.toLocaleString("vi-VN");
}

function rsiColor(rsi: number): string {
  if (rsi >= 70) return "text-red-400";
  if (rsi <= 30) return "text-emerald-400";
  return "text-amber-300";
}

function sentimentBadge(sentiment: string) {
  const map: Record<string, string> = {
    positive: "bg-emerald-900/50 text-emerald-400",
    negative: "bg-red-900/50 text-red-400",
    neutral: "bg-zinc-800 text-zinc-400",
  };
  return map[sentiment] ?? map.neutral;
}

/* ── Card wrapper ───────────────────────────────────────────── */
function Card({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 overflow-hidden">
      <div className="flex items-center gap-2 border-b border-zinc-800 px-5 py-3">
        <Icon className="h-4 w-4 text-emerald-400" />
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-300">
          {title}
        </h2>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function StatItem({
  label,
  value,
  color,
}: {
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-zinc-800/50 last:border-0">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className={`text-sm font-mono font-semibold ${color ?? "text-zinc-200"}`}>
        {value}
      </span>
    </div>
  );
}

/* ── Main page component ────────────────────────────────────── */
export default function CompanyProfilePage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol } = use(params);
  const [data, setData] = useState<CompanyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    fetch(`${API_BASE}/company/${symbol}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => setData(d as CompanyData))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [symbol]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3">
        <p className="text-red-400">Error: {error}</p>
        <Link href="/" className="text-sm text-emerald-400 hover:underline">
          Quay lại Dashboard
        </Link>
      </div>
    );
  }

  const { profile: p, financials: f, technicals: t, ownership: o, news } = data;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-7xl px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-amber-300">
                  {data.symbol}
                </h1>
                <span className="rounded-md bg-emerald-900/40 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                  {p.exchange}
                </span>
                <span className="rounded-md bg-zinc-800 px-2.5 py-0.5 text-xs text-zinc-400">
                  {p.industry}
                </span>
              </div>
              <p className="mt-1 text-sm text-zinc-400">{p.name}</p>
              <p className="text-xs text-zinc-600">{p.english_name}</p>
            </div>
          </div>
        </div>

        {/* Grid: 3 columns */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {/* ── Column 1: Profile + Ownership ─── */}
          <div className="space-y-4">
            <Card title="Thông tin doanh nghiệp" icon={Building2}>
              <div className="space-y-0">
                <StatItem label="Ngành" value={p.industry} />
                <StatItem label="Lĩnh vực" value={p.sector} />
                <StatItem label="Ngày thành lập" value={p.founded} />
                <StatItem label="Ngày niêm yết" value={p.listed_date} />
                <StatItem
                  label="Nhân viên"
                  value={fmtNum(p.employees)}
                />
                <StatItem
                  label="SLCP lưu hành"
                  value={fmtNum(p.outstanding_shares)}
                />
                <StatItem
                  label="Vốn hóa"
                  value={fmtVND(p.market_cap)}
                  color="text-amber-300"
                />
                <div className="pt-2 flex items-center gap-1.5 text-xs text-zinc-500">
                  <Globe className="h-3 w-3" />
                  <a
                    href={p.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-emerald-400 hover:underline inline-flex items-center gap-1"
                  >
                    {p.website}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-zinc-600 mt-1">
                  <Calendar className="h-3 w-3" />
                  {p.address}
                </div>
              </div>
            </Card>

            <Card title="Cơ cấu sở hữu" icon={PieChart}>
              {/* Ownership bar */}
              <div className="mb-3 h-3 rounded-full overflow-hidden flex">
                <div
                  className="bg-blue-500"
                  style={{ width: `${o.foreign_pct}%` }}
                  title={`Nước ngoài: ${o.foreign_pct}%`}
                />
                <div
                  className="bg-amber-500"
                  style={{ width: `${o.insider_pct}%` }}
                  title={`Nội bộ: ${o.insider_pct}%`}
                />
                <div
                  className="bg-fuchsia-500"
                  style={{ width: `${o.state_pct}%` }}
                  title={`Nhà nước: ${o.state_pct}%`}
                />
                <div
                  className="bg-zinc-600"
                  style={{ width: `${o.free_float_pct}%` }}
                  title={`Tự do: ${o.free_float_pct}%`}
                />
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs mb-4">
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-blue-500" />
                  <span className="text-zinc-400">
                    Nước ngoài: {o.foreign_pct}%
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-amber-500" />
                  <span className="text-zinc-400">
                    Nội bộ: {o.insider_pct}%
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-fuchsia-500" />
                  <span className="text-zinc-400">
                    Nhà nước: {o.state_pct}%
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-zinc-600" />
                  <span className="text-zinc-400">
                    Tự do: {o.free_float_pct}%
                  </span>
                </div>
              </div>
              <p className="text-xs text-zinc-500 mb-3">
                Room nước ngoài còn lại: {o.foreign_room_remaining}%
              </p>
              <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                Top 5 cổ đông lớn
              </h3>
              <div className="space-y-0">
                {o.top_holders.map((h, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between py-1.5 border-b border-zinc-800/50 last:border-0"
                  >
                    <span className="text-xs text-zinc-400 truncate max-w-[150px]">
                      {h.name}
                    </span>
                    <div className="text-right">
                      <span className="text-xs font-mono text-zinc-300">
                        {h.pct}%
                      </span>
                      <span className="ml-2 text-[10px] text-zinc-600">
                        ({fmtNum(h.shares)})
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* ── Column 2: Financials ─── */}
          <div className="space-y-4">
            <Card title="Chỉ số tài chính" icon={DollarSign}>
              <div className="grid grid-cols-2 gap-x-6">
                <StatItem label="P/E" value={f.pe_ratio} />
                <StatItem label="P/B" value={f.pb_ratio} />
                <StatItem label="EPS (TTM)" value={fmtNum(f.eps_ttm)} />
                <StatItem
                  label="ROE (TTM)"
                  value={`${f.roe_ttm}%`}
                  color={f.roe_ttm >= 15 ? "text-emerald-400" : "text-zinc-300"}
                />
                <StatItem
                  label="ROA (TTM)"
                  value={`${f.roa_ttm}%`}
                />
                <StatItem
                  label="D/E"
                  value={f.debt_to_equity}
                  color={f.debt_to_equity > 3 ? "text-red-400" : "text-zinc-300"}
                />
                <StatItem label="Current Ratio" value={f.current_ratio} />
                <StatItem label="Beta" value={f.beta} />
                <StatItem
                  label="Cổ tức"
                  value={`${f.dividend_yield}%`}
                  color={f.dividend_yield > 3 ? "text-emerald-400" : "text-zinc-300"}
                />
                <StatItem
                  label="Doanh thu (TTM)"
                  value={`${fmtNum(f.revenue_ttm)} tỷ`}
                />
              </div>
            </Card>

            <Card title="Kết quả kinh doanh theo quý" icon={BarChart3}>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-zinc-700 text-zinc-500">
                      <th className="py-2 text-left font-medium">Quý</th>
                      <th className="py-2 text-right font-medium">
                        DT (tỷ)
                      </th>
                      <th className="py-2 text-right font-medium">
                        LN (tỷ)
                      </th>
                      <th className="py-2 text-right font-medium">EPS</th>
                      <th className="py-2 text-right font-medium">
                        ROE%
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {f.quarterly.map((q) => (
                      <tr
                        key={q.period}
                        className="border-b border-zinc-800/40 hover:bg-zinc-800/30"
                      >
                        <td className="py-1.5 font-medium text-zinc-300">
                          {q.period}
                        </td>
                        <td className="py-1.5 text-right font-mono text-zinc-300">
                          {fmtNum(q.revenue)}
                        </td>
                        <td
                          className={`py-1.5 text-right font-mono ${q.net_profit >= 0 ? "text-emerald-400" : "text-red-400"}`}
                        >
                          {fmtNum(q.net_profit)}
                        </td>
                        <td className="py-1.5 text-right font-mono text-zinc-300">
                          {fmtNum(q.eps)}
                        </td>
                        <td
                          className={`py-1.5 text-right font-mono ${q.roe >= 15 ? "text-emerald-400" : "text-zinc-400"}`}
                        >
                          {q.roe}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          {/* ── Column 3: Technicals + News ─── */}
          <div className="space-y-4">
            <Card title="Phân tích kỹ thuật" icon={Activity}>
              <div className="space-y-0">
                <StatItem
                  label="RSI (14)"
                  value={t.rsi_14}
                  color={rsiColor(t.rsi_14)}
                />
                <StatItem
                  label="MACD"
                  value={t.macd}
                  color={t.macd > t.macd_signal ? "text-emerald-400" : "text-red-400"}
                />
                <StatItem label="MACD Signal" value={t.macd_signal} />
                <StatItem label="MA20" value={t.ma_20} />
                <StatItem label="MA50" value={t.ma_50} />
                <StatItem label="MA200" value={t.ma_200} />
                <StatItem
                  label="Bollinger (Upper)"
                  value={t.bollinger_upper}
                />
                <StatItem
                  label="Bollinger (Lower)"
                  value={t.bollinger_lower}
                />
                <StatItem label="ATR (14)" value={t.atr_14} />
                <StatItem
                  label="ADX"
                  value={t.adx}
                  color={t.adx > 25 ? "text-amber-300" : "text-zinc-400"}
                />
                <StatItem label="CCI" value={t.cci} />
                <StatItem label="Stochastic %K" value={t.stochastic_k} />
                <StatItem label="Stochastic %D" value={t.stochastic_d} />
                <StatItem
                  label="OBV Trend"
                  value={t.obv_trend}
                  color={
                    t.obv_trend === "bullish"
                      ? "text-emerald-400"
                      : t.obv_trend === "bearish"
                        ? "text-red-400"
                        : "text-zinc-400"
                  }
                />
                <div className="mt-3 flex items-center justify-between rounded-lg bg-zinc-800/50 px-3 py-2">
                  <div className="flex items-center gap-1.5 text-xs">
                    <TrendingDown className="h-3.5 w-3.5 text-red-400" />
                    <span className="text-zinc-500">Hỗ trợ</span>
                    <span className="font-mono font-semibold text-red-400">
                      {t.support}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs">
                    <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-zinc-500">Kháng cự</span>
                    <span className="font-mono font-semibold text-emerald-400">
                      {t.resistance}
                    </span>
                  </div>
                </div>
              </div>
            </Card>

            <Card title="Tin tức gần đây" icon={Newspaper}>
              <div className="space-y-3">
                {news.map((n, i) => (
                  <div
                    key={i}
                    className="border-b border-zinc-800/40 pb-2.5 last:border-0 last:pb-0"
                  >
                    <p className="text-sm leading-snug text-zinc-300">
                      {n.title}
                    </p>
                    <div className="mt-1 flex items-center gap-2">
                      <span className="text-[10px] text-zinc-600">
                        {n.date}
                      </span>
                      <span className="text-[10px] text-zinc-500">
                        {n.source}
                      </span>
                      <span
                        className={`inline-block rounded-full px-1.5 py-0.5 text-[10px] font-medium ${sentimentBadge(n.sentiment)}`}
                      >
                        {n.sentiment === "positive"
                          ? "Tích cực"
                          : n.sentiment === "negative"
                            ? "Tiêu cực"
                            : "Trung lập"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
