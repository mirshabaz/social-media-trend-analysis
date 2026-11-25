import { useCallback, useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { AlertCircle, ChevronLeft, ChevronRight, Search } from "lucide-react"
import { PageFrame } from "../components/PageFrame"
import {
  CHART_COLORS,
  ChartCard,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  MetricCard,
  SENTIMENT_COLORS,
  SentimentBadge,
} from "../components/ui/StateBlocks"
import { useApp } from "../context/AppContext"
import { api } from "../services/api"
import type { PostItem } from "../types/api"

export function SentimentPage({
  mode = "sentiment",
}: {
  mode?: "sentiment" | "emotion" | "opinion"
}) {
  const { datasetVersion, openPostDetail } = useApp()
  const [searchParams] = useSearchParams()

  const [sentimentFilter, setSentimentFilter] = useState(searchParams.get("filter") ?? "")
  const [platform, setPlatform] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)

  const [data, setData] = useState<Record<string, any> | null>(null)
  const [postsData, setPostsData] = useState<{ posts: PostItem[]; pagination: any } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const loadSentiment = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const filters = {
        platform: platform || undefined,
        sentiment: sentimentFilter || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        search: search || undefined,
      }
      const [sentRes, postsRes] = await Promise.all([
        api.sentiment(filters),
        api.posts({ ...filters, page, page_size: 12 }),
      ])
      setData(sentRes.data)
      setPostsData(postsRes.data as any)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sentiment intelligence.")
    } finally {
      setLoading(false)
    }
  }, [platform, sentimentFilter, startDate, endDate, search, page])

  useEffect(() => {
    loadSentiment()
  }, [loadSentiment, datasetVersion])

  const meta = data?.meta ?? {}
  const summary = data?.summary ?? {}
  const distribution: any[] = data?.distribution ?? []
  const posWords: any[] = data?.emotional_words?.positive ?? []
  const negWords: any[] = data?.emotional_words?.negative ?? []
  const emotions: any[] = data?.emotions ?? []

  return (
    <PageFrame
      eyebrow="NLP & Opinion Mining"
      title={
        mode === "emotion"
          ? "Emotion Detection"
          : mode === "opinion"
            ? "Topic Opinion Analysis"
            : "Sentiment Intelligence"
      }
      description="Analyze audience polarity across platforms, topics, timelines, and individual posts"
    >
      {/* Transparency Disclaimer */}
      <div className="rounded-xl border border-amber-500/35 bg-amber-500/10 px-4 py-2.5 text-xs text-amber-200 flex items-start gap-2.5">
        <AlertCircle size={15} className="shrink-0 mt-0.5 text-amber-400" />
        <span>
          {data?.disclaimer ??
            "Automated sentiment predictions may be imperfect on sarcasm, idioms, or specialized terminology."}
        </span>
      </div>

      {/* Filters */}
      <div className="sp-card p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-3 text-[var(--text-muted)]" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="Search post text..."
            className="sp-input w-full !pl-8"
          />
        </div>
        <select
          value={sentimentFilter}
          onChange={(e) => {
            setSentimentFilter(e.target.value)
            setPage(1)
          }}
          className="sp-select w-full"
        >
          <option value="">All Sentiments</option>
          <option value="Positive">Positive</option>
          <option value="Negative">Negative</option>
          <option value="Neutral">Neutral</option>
        </select>
        <select
          value={platform}
          onChange={(e) => {
            setPlatform(e.target.value)
            setPage(1)
          }}
          className="sp-select w-full"
        >
          <option value="">All Platforms</option>
          {(meta.available_platforms ?? []).map((p: string) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={startDate}
          min={meta.date_min ?? undefined}
          max={meta.date_max ?? undefined}
          onChange={(e) => {
            setStartDate(e.target.value)
            setPage(1)
          }}
          className="sp-input w-full"
          aria-label="Start date"
        />
        <input
          type="date"
          value={endDate}
          min={meta.date_min ?? undefined}
          max={meta.date_max ?? undefined}
          onChange={(e) => {
            setEndDate(e.target.value)
            setPage(1)
          }}
          className="sp-input w-full"
          aria-label="End date"
        />
      </div>

      {loading ? (
        <LoadingSkeleton cards={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadSentiment} />
      ) : summary.total_posts === 0 ? (
        <EmptyState
          title="No posts match sentiment filters"
          action={
            <button
              type="button"
              onClick={() => {
                setSentimentFilter("")
                setPlatform("")
                setStartDate("")
                setEndDate("")
                setSearch("")
              }}
              className="sp-btn-primary"
            >
              Reset Filters
            </button>
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricCard
              title="Positive Sentiment"
              value={`${summary.positive_pct ?? 0}%`}
              subtitle="Click to filter Positive posts"
              accent="#22C55E"
              onClick={() => setSentimentFilter(sentimentFilter === "Positive" ? "" : "Positive")}
            />
            <MetricCard
              title="Negative Sentiment"
              value={`${summary.negative_pct ?? 0}%`}
              subtitle="Click to filter Negative posts"
              accent="#EF4444"
              onClick={() => setSentimentFilter(sentimentFilter === "Negative" ? "" : "Negative")}
            />
            <MetricCard
              title="Neutral Sentiment"
              value={`${summary.neutral_pct ?? 0}%`}
              subtitle="Click to filter Neutral posts"
              accent="#94A3B8"
              onClick={() => setSentimentFilter(sentimentFilter === "Neutral" ? "" : "Neutral")}
            />
            <MetricCard
              title="Mean Polarity Score"
              value={summary.avg_polarity ?? 0}
              subtitle="Scale -1.0 (negative) to +1.0 (positive)"
              accent="#7C5CFC"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <ChartCard title="Sentiment Split" subtitle="Click slice to filter table below">
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={distribution}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={55}
                      outerRadius={88}
                      paddingAngle={3}
                      onClick={(entry: any) => {
                        if (entry?.name) {
                          setSentimentFilter(entry.name)
                          setPage(1)
                        }
                      }}
                      className="cursor-pointer"
                    >
                      {distribution.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={SENTIMENT_COLORS[entry.name] ?? "#7C5CFC"}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: "var(--tooltip-bg)",
                        border: "1px solid var(--tooltip-border)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard
              title="Sentiment Over Time"
              subtitle="Weekly counts across Positive, Negative, and Neutral posts"
              className="lg:col-span-2"
            >
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data?.over_time ?? []}>
                    <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                    <XAxis dataKey="period" stroke="var(--chart-tick)" tick={{ fontSize: 10 }} />
                    <YAxis stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "var(--tooltip-bg)",
                        border: "1px solid var(--tooltip-border)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Legend />
                    <Area type="monotone" dataKey="Positive" stackId="1" stroke="#22C55E" fill="#22C55E" fillOpacity={0.35} />
                    <Area type="monotone" dataKey="Neutral" stackId="1" stroke="#94A3B8" fill="#94A3B8" fillOpacity={0.25} />
                    <Area type="monotone" dataKey="Negative" stackId="1" stroke="#EF4444" fill="#EF4444" fillOpacity={0.35} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard title="Platform-Wise Sentiment (%)" subtitle="Distribution by social channel">
              <div className="h-[270px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data?.by_platform ?? []}>
                    <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                    <XAxis dataKey="name" stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <YAxis stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "var(--tooltip-bg)",
                        border: "1px solid var(--tooltip-border)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Legend />
                    <Bar dataKey="Positive" stackId="s" fill="#22C55E" />
                    <Bar dataKey="Neutral" stackId="s" fill="#94A3B8" />
                    <Bar dataKey="Negative" stackId="s" fill="#EF4444" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard
              title="Topic-Wise Sentiment (%)"
              subtitle="Positive vs negative composition across topics"
              className="lg:col-span-2"
            >
              <div className="h-[270px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={(data?.by_topic ?? []).slice(0, 10)}>
                    <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                    <XAxis dataKey="name" stroke="var(--chart-tick)" tick={{ fontSize: 10 }} />
                    <YAxis stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "var(--tooltip-bg)",
                        border: "1px solid var(--tooltip-border)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Legend />
                    <Bar dataKey="Positive" stackId="t" fill="#22C55E" />
                    <Bar dataKey="Neutral" stackId="t" fill="#94A3B8" />
                    <Bar dataKey="Negative" stackId="t" fill="#EF4444" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>

          {/* Emotions + Positive/Negative Topics + Emotional Vocabulary */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <ChartCard title="Detected Emotion Signals" subtitle="Lexicon emotion distribution">
              <div className="h-[240px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={emotions} layout="vertical">
                    <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                    <XAxis type="number" stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={135}
                      stroke="var(--chart-tick)"
                      tick={{ fontSize: 10 }}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--tooltip-bg)",
                        border: "1px solid var(--tooltip-border)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Bar dataKey="count" name="Posts" radius={[0, 6, 6, 0]}>
                      {emotions.map((_, idx) => (
                        <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard title="Most Positive & Negative Topics" subtitle="Highest positive vs negative share">
              <div className="space-y-4 text-xs">
                <div>
                  <div className="font-semibold text-emerald-400 mb-2">Most Positive Topics</div>
                  <div className="space-y-1.5">
                    {(data?.most_positive_topics ?? []).slice(0, 4).map((t: any) => (
                      <div key={t.name} className="flex justify-between items-center">
                        <span className="truncate pr-2">{t.name}</span>
                        <span className="font-bold text-emerald-400">{t.Positive}%</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="border-t border-[var(--border-subtle)] pt-3">
                  <div className="font-semibold text-rose-400 mb-2">Most Negative Topics</div>
                  <div className="space-y-1.5">
                    {(data?.most_negative_topics ?? []).slice(0, 4).map((t: any) => (
                      <div key={t.name} className="flex justify-between items-center">
                        <span className="truncate pr-2">{t.name}</span>
                        <span className="font-bold text-rose-400">{t.Negative}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </ChartCard>

            <ChartCard title="Frequent Emotional Words" subtitle="Top terms in positive vs negative posts">
              <div className="space-y-4 text-xs">
                <div>
                  <div className="font-semibold text-emerald-400 mb-1.5">Positive Vocabulary</div>
                  <div className="flex flex-wrap gap-1.5">
                    {posWords.slice(0, 12).map((w) => (
                      <span
                        key={w.word}
                        className="rounded-full bg-emerald-500/15 text-emerald-400 px-2.5 py-0.5 text-[11px]"
                      >
                        {w.word} ({w.count})
                      </span>
                    ))}
                  </div>
                </div>
                <div className="border-t border-[var(--border-subtle)] pt-3">
                  <div className="font-semibold text-rose-400 mb-1.5">Negative Vocabulary</div>
                  <div className="flex flex-wrap gap-1.5">
                    {negWords.slice(0, 12).map((w) => (
                      <span
                        key={w.word}
                        className="rounded-full bg-rose-500/15 text-rose-400 px-2.5 py-0.5 text-[11px]"
                      >
                        {w.word} ({w.count})
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </ChartCard>
          </div>

          {/* Searchable Post List */}
          <ChartCard
            title="Individual Post Sentiment Explorer"
            subtitle="Click any row to inspect full NLP polarity, emotion signal, and benchmarks"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                    <th className="py-2.5 pr-3">Post Content</th>
                    <th className="py-2.5 pr-3">Platform</th>
                    <th className="py-2.5 pr-3">Topic</th>
                    <th className="py-2.5 pr-3">Sentiment</th>
                    <th className="py-2.5 pr-3">Polarity</th>
                    <th className="py-2.5 pr-3">Emotion</th>
                    <th className="py-2.5 text-right">Eng.</th>
                  </tr>
                </thead>
                <tbody>
                  {(postsData?.posts ?? []).map((p) => (
                    <tr
                      key={p.post_id}
                      onClick={() => openPostDetail(p.post_id)}
                      className="border-b border-[var(--border-subtle)]/60 hover:bg-[var(--bg-elevated)] cursor-pointer"
                    >
                      <td className="py-2.5 pr-3 max-w-md">
                        <div className="truncate font-medium text-[var(--text-primary)]">{p.content}</div>
                        <div className="text-[10px] text-[var(--text-muted)]">{p.post_id}</div>
                      </td>
                      <td className="py-2.5 pr-3">{p.platform}</td>
                      <td className="py-2.5 pr-3">{p.topic}</td>
                      <td className="py-2.5 pr-3">
                        <SentimentBadge sentiment={p.sentiment} />
                      </td>
                      <td className="py-2.5 pr-3 font-mono">{p.sentiment_polarity}</td>
                      <td className="py-2.5 pr-3 text-[var(--text-secondary)]">{p.detected_emotion}</td>
                      <td className="py-2.5 text-right font-semibold">{p.engagement.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {postsData?.pagination && (
              <div className="flex items-center justify-between mt-4 text-xs text-[var(--text-secondary)]">
                <span>
                  Page {postsData.pagination.page} of {postsData.pagination.total_pages} (
                  {postsData.pagination.total.toLocaleString()} matching posts)
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="sp-btn-secondary !h-8 !px-2.5"
                  >
                    <ChevronLeft size={14} /> Prev
                  </button>
                  <button
                    type="button"
                    disabled={page >= postsData.pagination.total_pages}
                    onClick={() => setPage((p) => p + 1)}
                    className="sp-btn-secondary !h-8 !px-2.5"
                  >
                    Next <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </ChartCard>
        </>
      )}
    </PageFrame>
  )
}

