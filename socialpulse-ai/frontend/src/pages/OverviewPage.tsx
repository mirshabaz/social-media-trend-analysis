import { useCallback, useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import {
  Activity,
  Download,
  Filter,
  RotateCcw,
  Sparkles,
  Upload,
} from "lucide-react"
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
import type { ActivityItem, PostItem } from "../types/api"

export function OverviewPage({
  mode = "overview",
}: {
  mode?: "overview" | "command" | "executive" | "social"
}) {
  const {
    datasetVersion,
    activeDataset,
    globalFilters,
    setGlobalFilters,
    resetFilters,
    openPostDetail,
    pushToast,
    refreshNotifications,
  } = useApp()

  const navigate = useNavigate()
  const [data, setData] = useState<Record<string, any> | null>(null)
  const [topPosts, setTopPosts] = useState<PostItem[]>([])
  const [activityLog, setActivityLog] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState("")
  const [showFilters, setShowFilters] = useState(false)
  const [exporting, setExporting] = useState(false)

  const loadData = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) setRefreshing(true)
      else setLoading(true)
      setError("")
      try {
        const [ovRes, engRes, actRes] = await Promise.all([
          api.overview(globalFilters),
          api.engagement({ ...globalFilters, limit: 6 }),
          api.activity(6),
        ])
        setData(ovRes.data)
        setTopPosts(engRes.data.top_posts ?? [])
        setActivityLog(actRes.activity ?? [])
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load overview metrics.")
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [globalFilters]
  )

  useEffect(() => {
    loadData()
  }, [loadData, datasetVersion])

  async function handleQuickExport(fmt: "pdf" | "csv" | "xlsx") {
    setExporting(true)
    try {
      const res = await api.generateReport({
        report_type: "overall",
        format: fmt,
        platform: globalFilters.platform || undefined,
        start_date: globalFilters.start_date || undefined,
        end_date: globalFilters.end_date || undefined,
      })
      await api.downloadReport(res.report.id, `${res.report.title}.${fmt}`)
      await refreshNotifications()
      pushToast({
        title: "Report Downloaded",
        message: `Generated and downloaded ${fmt.toUpperCase()} overview report.`,
        variant: "success",
      })
    } catch (err) {
      pushToast({
        title: "Export Failed",
        message: err instanceof Error ? err.message : "Could not generate export.",
        variant: "error",
      })
    } finally {
      setExporting(false)
    }
  }

  const pageMeta =
    mode === "command"
      ? {
          eyebrow: "Operations",
          title: "Command Center",
          description: "Live dataset telemetry, anomaly alerts, and cross-channel KPI status",
        }
      : mode === "executive"
        ? {
            eyebrow: "Leadership View",
            title: "Executive Dashboard",
            description: "High-level ROI, sentiment posture, and strategic topic performance",
          }
        : mode === "social"
          ? {
              eyebrow: "Cross-Channel",
              title: "Social Analytics",
              description: "Post volume, interaction velocity, and content length efficiency",
            }
          : {
              eyebrow: "Command Center",
              title: "Analytics Overview",
              description: "Dataset-grounded social intelligence across topics, sentiment, platforms, and engagement",
            }

  const kpis = data?.kpis ?? {}
  const meta = data?.meta ?? {}
  const availablePlatforms: string[] = meta.available_platforms ?? []

  return (
    <PageFrame
      eyebrow={pageMeta.eyebrow}
      title={pageMeta.title}
      description={pageMeta.description}
      actions={
        <>
          <button
            type="button"
            onClick={() => setShowFilters((v) => !v)}
            className="sp-btn-secondary"
          >
            <Filter size={15} /> {showFilters ? "Hide Filters" : "Filters"}
          </button>
          <button
            type="button"
            onClick={() => navigate("/upload")}
            className="sp-btn-secondary"
          >
            <Upload size={15} /> Upload CSV
          </button>
          <button
            type="button"
            disabled={exporting}
            onClick={() => handleQuickExport("pdf")}
            className="sp-btn-primary"
          >
            <Download size={15} /> {exporting ? "Exporting..." : "Export PDF"}
          </button>
        </>
      }
    >
      {/* Interactive Filter Bar */}
      {showFilters && (
        <div className="sp-card p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
          <div>
            <label className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1">
              Platform
            </label>
            <select
              value={globalFilters.platform ?? ""}
              onChange={(e) =>
                setGlobalFilters((prev) => ({ ...prev, platform: e.target.value }))
              }
              className="sp-select w-full"
            >
              <option value="">All Platforms</option>
              {availablePlatforms.map((plat) => (
                <option key={plat} value={plat}>
                  {plat}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={globalFilters.start_date ?? ""}
              min={meta.date_min ?? undefined}
              max={meta.date_max ?? undefined}
              onChange={(e) =>
                setGlobalFilters((prev) => ({ ...prev, start_date: e.target.value }))
              }
              className="sp-input w-full"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1">
              End Date
            </label>
            <input
              type="date"
              value={globalFilters.end_date ?? ""}
              min={meta.date_min ?? undefined}
              max={meta.date_max ?? undefined}
              onChange={(e) =>
                setGlobalFilters((prev) => ({ ...prev, end_date: e.target.value }))
              }
              className="sp-input w-full"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1">
              Keyword / Hashtag
            </label>
            <input
              type="text"
              value={globalFilters.search ?? ""}
              placeholder="Filter content..."
              onChange={(e) =>
                setGlobalFilters((prev) => ({ ...prev, search: e.target.value }))
              }
              className="sp-input w-full"
            />
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={resetFilters} className="sp-btn-secondary flex-1">
              <RotateCcw size={14} /> Reset
            </button>
            <button
              type="button"
              onClick={() => handleQuickExport("csv")}
              disabled={exporting}
              className="sp-btn-secondary"
              title="Download CSV Summary"
            >
              CSV
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <LoadingSkeleton cards={8} />
      ) : error ? (
        <ErrorState message={error} onRetry={() => loadData()} />
      ) : !data || kpis.total_posts === 0 ? (
        <EmptyState
          title="No posts match your current filters"
          message="Clear the active platform or date filters, or upload a new CSV dataset."
          action={
            <button type="button" onClick={resetFilters} className="sp-btn-primary">
              Reset Filters
            </button>
          }
        />
      ) : (
        <>
          {/* Clickable KPI Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricCard
              title="Total Posts Analyzed"
              value={(kpis.total_posts ?? 0).toLocaleString()}
              subtitle={activeDataset ? `From ${activeDataset.name}` : "Active CSV dataset"}
              accent="#7C5CFC"
              badge="DATASET"
              onClick={() => navigate("/datasets")}
            />
            <MetricCard
              title="Total Engagement"
              value={(kpis.total_engagement ?? 0).toLocaleString()}
              subtitle={`${(kpis.total_likes ?? 0).toLocaleString()} likes • ${(kpis.total_shares ?? 0).toLocaleString()} shares`}
              accent="#00D4FF"
              onClick={() => navigate("/engagement")}
            />
            <MetricCard
              title="Avg. Engagement / Post"
              value={kpis.avg_engagement ?? 0}
              subtitle={
                kpis.engagement_rate !== null && kpis.engagement_rate !== undefined
                  ? `Eng. Rate: ${kpis.engagement_rate}%`
                  : "Eng. Rate: N/A (no reach column)"
              }
              accent="#8B5CF6"
              onClick={() => navigate("/engagement")}
            />
            <MetricCard
              title="Top Platform"
              value={kpis.top_platform ?? "N/A"}
              subtitle={`Top Topic: ${kpis.top_topic ?? "N/A"}`}
              accent="#00D4FF"
              badge="LEADER"
              onClick={() => navigate("/platforms")}
            />
            <MetricCard
              title="Positive Sentiment"
              value={`${kpis.positive_sentiment ?? 0}%`}
              subtitle={`${(kpis.positive_count ?? 0).toLocaleString()} positive posts`}
              accent="#22C55E"
              onClick={() => navigate("/sentiment?filter=Positive")}
            />
            <MetricCard
              title="Negative Sentiment"
              value={`${kpis.negative_sentiment ?? 0}%`}
              subtitle={`${(kpis.negative_count ?? 0).toLocaleString()} negative posts`}
              accent="#EF4444"
              onClick={() => navigate("/sentiment?filter=Negative")}
            />
            <MetricCard
              title="Neutral Sentiment"
              value={`${kpis.neutral_sentiment ?? 0}%`}
              subtitle={`${(kpis.neutral_count ?? 0).toLocaleString()} neutral posts`}
              accent="#94A3B8"
              onClick={() => navigate("/sentiment?filter=Neutral")}
            />
            <MetricCard
              title="Top Hashtag"
              value={kpis.top_hashtag ?? "N/A"}
              subtitle="Click to explore hashtag intelligence"
              accent="#F59E0B"
              onClick={() =>
                navigate(
                  kpis.top_hashtag && kpis.top_hashtag !== "N/A"
                    ? `/hashtags?tag=${encodeURIComponent(kpis.top_hashtag)}`
                    : "/hashtags"
                )
              }
            />
          </div>

          {/* 6 Interactive Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* 1. Engagement Over Time */}
            <ChartCard
              title="Engagement Over Time"
              subtitle="Click any point to inspect that date's time analytics"
              onRefresh={() => loadData(true)}
              refreshing={refreshing}
              className="lg:col-span-2"
            >
              <div className="h-[290px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={data.activity ?? []}
                    onClick={(state: any) => {
                      if (state?.activeLabel) {
                        navigate(`/posting-time?date=${state.activeLabel}`)
                      }
                    }}
                  >
                    <defs>
                      <linearGradient id="spEngFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#7C5CFC" stopOpacity={0.38} />
                        <stop offset="95%" stopColor="#7C5CFC" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                    <XAxis dataKey="date" stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <YAxis stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "var(--tooltip-bg)",
                        border: "1px solid var(--tooltip-border)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="engagement"
                      stroke="#7C5CFC"
                      fill="url(#spEngFill)"
                      strokeWidth={2.2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* 2. Sentiment Distribution */}
            <ChartCard
              title="Sentiment Distribution"
              subtitle="Click a slice to inspect sentiment posts"
              onRefresh={() => loadData(true)}
              refreshing={refreshing}
            >
              <div className="h-[230px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data.sentiment ?? []}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={56}
                      outerRadius={86}
                      paddingAngle={3}
                      onClick={(entry: any) => {
                        if (entry?.name) navigate(`/sentiment?filter=${entry.name}`)
                      }}
                      className="cursor-pointer"
                    >
                      {(data.sentiment ?? []).map((entry: any) => (
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
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-center gap-4 text-xs mt-1">
                {(data.sentiment ?? []).map((s: any) => (
                  <button
                    key={s.name}
                    type="button"
                    onClick={() => navigate(`/sentiment?filter=${s.name}`)}
                    className="flex items-center gap-1.5 bg-transparent border-0 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                  >
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ background: SENTIMENT_COLORS[s.name] ?? "#7C5CFC" }}
                    />
                    <span>{s.name} ({s.percentage}%)</span>
                  </button>
                ))}
              </div>
            </ChartCard>

            {/* 3. Platform Comparison */}
            <ChartCard
              title="Platform Comparison"
              subtitle="Total interactions & average per post"
              onRefresh={() => loadData(true)}
              refreshing={refreshing}
            >
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={data.platforms ?? []}
                    onClick={(state: any) => {
                      if (state?.activeLabel) {
                        navigate(`/platforms?focus=${encodeURIComponent(state.activeLabel)}`)
                      }
                    }}
                  >
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
                    <Bar dataKey="engagement" name="Total Engagement" fill="#00D4FF" radius={[6, 6, 0, 0]} className="cursor-pointer" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* 4. Trending Topics */}
            <ChartCard
              title="Most Discussed Topics"
              subtitle="Click any topic bar to explore its trend breakdown"
              onRefresh={() => loadData(true)}
              refreshing={refreshing}
              className="lg:col-span-2"
            >
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={(data.topics ?? []).slice(0, 8)} layout="vertical">
                    <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                    <XAxis type="number" stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={170}
                      stroke="var(--chart-tick)"
                      tick={{ fontSize: 11 }}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--tooltip-bg)",
                        border: "1px solid var(--tooltip-border)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Bar
                      dataKey="posts"
                      name="Posts"
                      fill="#7C5CFC"
                      radius={[0, 6, 6, 0]}
                      className="cursor-pointer"
                      onClick={(entry: any) => {
                        if (entry?.name) {
                          navigate(`/trending-topics?topic=${encodeURIComponent(entry.name)}`)
                        }
                      }}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* 5. Hashtag Performance */}
            <ChartCard
              title="Hashtag Performance"
              subtitle="Top hashtags by usage & average engagement"
              action={
                <button
                  type="button"
                  onClick={() => navigate("/hashtags")}
                  className="text-xs font-semibold text-[var(--accent-primary)] bg-transparent border-0"
                >
                  Explorer →
                </button>
              }
            >
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={(data.hashtags ?? []).slice(0, 8)} layout="vertical">
                    <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                    <XAxis type="number" stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={125}
                      stroke="var(--chart-tick)"
                      tick={{ fontSize: 11 }}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--tooltip-bg)",
                        border: "1px solid var(--tooltip-border)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Bar
                      dataKey="count"
                      name="Mentions"
                      radius={[0, 6, 6, 0]}
                      className="cursor-pointer"
                      onClick={(entry: any) => {
                        if (entry?.name) {
                          navigate(`/hashtags?tag=${encodeURIComponent(entry.name)}`)
                        }
                      }}
                    >
                      {(data.hashtags ?? []).slice(0, 8).map((_: any, idx: number) => (
                        <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* 6. Content Engagement Comparison */}
            <ChartCard
              title="Content Length Engagement Comparison"
              subtitle="Average interaction by post character count"
              action={
                <button
                  type="button"
                  onClick={() => navigate("/viral-content")}
                  className="text-xs font-semibold text-[var(--accent-primary)] bg-transparent border-0"
                >
                  Details →
                </button>
              }
              className="lg:col-span-2"
            >
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.content_engagement ?? []}>
                    <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                    <XAxis dataKey="bucket" stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <YAxis stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "var(--tooltip-bg)",
                        border: "1px solid var(--tooltip-border)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Bar dataKey="avg_engagement" name="Avg Engagement" fill="#22C55E" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="posts" name="Post Volume" fill="#7C5CFC" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>

          {/* Bottom Split: Top Performing Posts & Recent Analysis Activity */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <ChartCard
              title="Top Performing Content"
              subtitle="Click any post to open full engagement & NLP analysis"
              className="lg:col-span-2"
              action={
                <button
                  type="button"
                  onClick={() => navigate("/engagement")}
                  className="text-xs font-semibold text-[var(--accent-primary)] bg-transparent border-0"
                >
                  All Posts →
                </button>
              }
            >
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                      <th className="py-2.5 pr-3">Post</th>
                      <th className="py-2.5 pr-3">Platform</th>
                      <th className="py-2.5 pr-3">Sentiment</th>
                      <th className="py-2.5 text-right">Engagement</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topPosts.map((post) => (
                      <tr
                        key={post.post_id}
                        onClick={() => openPostDetail(post.post_id)}
                        className="border-b border-[var(--border-subtle)]/60 hover:bg-[var(--bg-elevated)] cursor-pointer transition-colors"
                      >
                        <td className="py-2.5 pr-3 max-w-md">
                          <div className="font-semibold text-[var(--text-primary)] truncate">
                            {post.content}
                          </div>
                          <div className="text-[11px] text-[var(--text-muted)]">
                            {post.post_id} • {post.topic}
                          </div>
                        </td>
                        <td className="py-2.5 pr-3 font-medium">{post.platform}</td>
                        <td className="py-2.5 pr-3">
                          <SentimentBadge sentiment={post.sentiment} />
                        </td>
                        <td className="py-2.5 text-right font-bold text-[var(--accent-secondary)]">
                          {post.engagement.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ChartCard>

            <ChartCard
              title="Recent Analysis Activity"
              subtitle="Real workspace audit events"
              action={
                <button
                  type="button"
                  onClick={() => navigate("/assistant")}
                  className="text-xs font-semibold text-[var(--accent-primary)] bg-transparent border-0 flex items-center gap-1"
                >
                  <Sparkles size={13} /> Ask AI
                </button>
              }
            >
              <div className="space-y-2.5">
                {activityLog.length === 0 ? (
                  <p className="text-xs text-[var(--text-secondary)] m-0">
                    No activity recorded yet.
                  </p>
                ) : (
                  activityLog.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)]/60 p-3 flex items-start gap-2.5"
                    >
                      <Activity size={14} className="text-[var(--accent-primary)] shrink-0 mt-0.5" />
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-semibold text-[var(--text-primary)] truncate">
                          {item.target_name || item.action}
                        </div>
                        <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                          {item.details}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ChartCard>
          </div>
        </>
      )}
    </PageFrame>
  )
}

