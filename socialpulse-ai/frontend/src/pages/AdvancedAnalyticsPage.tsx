import { useCallback, useEffect, useState } from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { AlertTriangle, Clock, Info, Network } from "lucide-react"
import { PageFrame } from "../components/PageFrame"
import {
  CHART_COLORS,
  ChartCard,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  MetricCard,
  SentimentBadge,
} from "../components/ui/StateBlocks"
import { useApp } from "../context/AppContext"
import { api } from "../services/api"

export function AdvancedAnalyticsPage({
  defaultTab = "clusters",
}: {
  defaultTab?: "clusters" | "time" | "anomalies"
}) {
  const { datasetVersion, openPostDetail } = useApp()
  const [tab, setTab] = useState(defaultTab)
  const [granularity, setGranularity] = useState<"daily" | "weekly" | "monthly">("weekly")
  const [platform, setPlatform] = useState("")

  const [clusterData, setClusterData] = useState<Record<string, any> | null>(null)
  const [timeData, setTimeData] = useState<Record<string, any> | null>(null)
  const [anomData, setAnomData] = useState<Record<string, any> | null>(null)
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    setTab(defaultTab)
  }, [defaultTab])

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const filters = { platform: platform || undefined }
      const [cRes, tRes, aRes] = await Promise.all([
        api.topics(filters),
        api.timeAnalysis({ ...filters, granularity }),
        api.anomalies(filters),
      ])
      setClusterData(cRes.data)
      setTimeData(tRes.data)
      setAnomData(aRes.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load advanced analytics.")
    } finally {
      setLoading(false)
    }
  }, [platform, granularity])

  useEffect(() => {
    loadAll()
  }, [loadAll, datasetVersion])

  const meta = clusterData?.meta ?? timeData?.meta ?? {}
  const clusters: any[] = clusterData?.clusters ?? []
  const selectedCluster =
    clusters.find((c) => c.cluster_id === selectedClusterId) ?? clusters[0] ?? null

  return (
    <PageFrame
      eyebrow="ML & Statistical Intelligence"
      title={
        tab === "clusters"
          ? "NLP Topic Clustering"
          : tab === "time"
            ? "Time-Based & Posting Window Analysis"
            : "Statistical Anomaly Detection"
      }
      description="Machine learning topic grouping, temporal engagement cadence, and outlier explanation"
      actions={
        <div className="flex flex-wrap gap-1.5">
          {[
            { id: "clusters", label: "Topic Clusters", icon: Network },
            { id: "time", label: "Posting Windows", icon: Clock },
            { id: "anomalies", label: "Anomalies", icon: AlertTriangle },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id as any)}
              className={
                tab === item.id
                  ? "sp-btn-primary !h-8 !text-xs"
                  : "sp-btn-secondary !h-8 !text-xs"
              }
            >
              <item.icon size={13} /> {item.label}
            </button>
          ))}
        </div>
      }
    >
      <div className="sp-card p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[var(--text-secondary)]">Platform:</span>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="sp-select !h-9"
          >
            <option value="">All Platforms</option>
            {(meta.available_platforms ?? []).map((p: string) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        {tab === "time" && (
          <div className="flex items-center gap-1.5">
            {(["daily", "weekly", "monthly"] as const).map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGranularity(g)}
                className={
                  granularity === g
                    ? "sp-btn-primary !h-8 !text-xs capitalize"
                    : "sp-btn-secondary !h-8 !text-xs capitalize"
                }
              >
                {g}
              </button>
            ))}
          </div>
        )}
      </div>

      {loading ? (
        <LoadingSkeleton cards={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadAll} />
      ) : tab === "clusters" ? (
        clusters.length === 0 ? (
          <EmptyState title="Not enough text records to build topic clusters" />
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <MetricCard title="Topic Clusters" value={clusters.length} accent="#7C5CFC" />
              <MetricCard
                title="Largest Cluster"
                value={clusters[0]?.label ?? "N/A"}
                subtitle={`${clusters[0]?.post_count ?? 0} posts (${clusters[0]?.share_pct ?? 0}%)`}
                accent="#00D4FF"
              />
              <MetricCard
                title="Highest Eng. Cluster"
                value={[...clusters].sort((a, b) => b.avg_engagement - a.avg_engagement)[0]?.label ?? "N/A"}
                subtitle={`${[...clusters].sort((a, b) => b.avg_engagement - a.avg_engagement)[0]?.avg_engagement ?? 0} avg/post`}
                accent="#22C55E"
              />
              <MetricCard
                title="Clustering Pipeline"
                value="TF-IDF + KMeans"
                subtitle="Unsupervised NLP grouping"
                accent="#8B5CF6"
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <ChartCard title="Cluster Size & Engagement" className="lg:col-span-2">
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={clusters}>
                      <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                      <XAxis dataKey="label" stroke="var(--chart-tick)" tick={{ fontSize: 10 }} />
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
                      <Bar
                        dataKey="post_count"
                        name="Posts"
                        radius={[6, 6, 0, 0]}
                        className="cursor-pointer"
                        onClick={(entry: any) =>
                          entry?.cluster_id !== undefined && setSelectedClusterId(entry.cluster_id)
                        }
                      >
                        {clusters.map((c, idx) => (
                          <Cell key={c.cluster_id} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>

              <ChartCard title="Clusters Directory" subtitle="Select a cluster to inspect keywords and posts">
                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                  {clusters.map((c) => (
                    <button
                      key={c.cluster_id}
                      type="button"
                      onClick={() => setSelectedClusterId(c.cluster_id)}
                      className={`w-full text-left p-3 rounded-xl border transition-colors ${
                        selectedCluster?.cluster_id === c.cluster_id
                          ? "border-[var(--accent-primary)] bg-[var(--accent-soft)]"
                          : "border-[var(--border-subtle)] bg-[var(--bg-elevated)]"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 text-xs font-bold">
                        <span className="truncate">{c.label}</span>
                        <span>{c.post_count} posts</span>
                      </div>
                      <div className="text-[11px] text-[var(--text-secondary)] mt-1 truncate">
                        {c.keywords.join(", ")}
                      </div>
                    </button>
                  ))}
                </div>
              </ChartCard>
            </div>

            {selectedCluster && (
              <ChartCard
                title={`Cluster Detail: ${selectedCluster.label}`}
                subtitle={`${selectedCluster.post_count} posts • Avg Engagement ${selectedCluster.avg_engagement} • Dominant Sentiment: ${selectedCluster.dominant_sentiment}`}
              >
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {selectedCluster.keywords.map((kw: string) => (
                    <span
                      key={kw}
                      className="rounded-full bg-[var(--accent-soft)] text-[var(--accent-primary)] px-2.5 py-1 text-xs font-semibold"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {(selectedCluster.sample_posts ?? []).map((p: any) => (
                    <button
                      key={p.post_id}
                      type="button"
                      onClick={() => openPostDetail(p.post_id)}
                      className="text-left p-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] hover:border-[var(--accent-primary)]"
                    >
                      <div className="flex items-center justify-between text-[11px] font-semibold">
                        <span>
                          {p.post_id} • {p.platform}
                        </span>
                        <SentimentBadge sentiment={p.sentiment} />
                      </div>
                      <p className="text-xs text-[var(--text-secondary)] mt-1 mb-1">{p.content}</p>
                      <div className="text-[11px] text-[var(--accent-secondary)] font-semibold">
                        {p.engagement.toLocaleString()} interactions
                      </div>
                    </button>
                  ))}
                </div>
              </ChartCard>
            )}
          </div>
        )
      ) : tab === "time" ? (
        !timeData?.has_timestamps ? (
          <EmptyState
            title="No valid timestamps found"
            message={timeData?.historical_note ?? "Upload a CSV with a valid date/timestamp column."}
          />
        ) : (
          <div className="space-y-4">
            <div className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-4 py-2.5 text-xs text-sky-300 flex items-start gap-2">
              <Info size={15} className="shrink-0 mt-0.5" />
              <span>{timeData.historical_note}</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <MetricCard
                title="Peak Engagement Day"
                value={timeData.growth_summary?.best_day?.day ?? "N/A"}
                subtitle={`Avg ${timeData.growth_summary?.best_day?.avg_engagement ?? 0} interactions`}
                accent="#7C5CFC"
              />
              <MetricCard
                title="Peak Hour Window"
                value={timeData.growth_summary?.best_hour?.label ?? "N/A"}
                subtitle={`Avg ${timeData.growth_summary?.best_hour?.avg_engagement ?? 0} interactions`}
                accent="#00D4FF"
              />
              <MetricCard
                title="Unique Days Covered"
                value={timeData.growth_summary?.unique_days ?? 0}
                accent="#22C55E"
              />
              <MetricCard
                title="Historical Span Change"
                value={
                  timeData.growth_summary?.period_engagement_change_pct !== null &&
                  timeData.growth_summary?.period_engagement_change_pct !== undefined
                    ? `${timeData.growth_summary.period_engagement_change_pct > 0 ? "+" : ""}${timeData.growth_summary.period_engagement_change_pct}%`
                    : "N/A"
                }
                subtitle="2nd half vs 1st half engagement"
                accent="#F59E0B"
              />
            </div>

            <ChartCard
              title={`Engagement & Sentiment (${granularity})`}
              subtitle="Historical engagement volume and sentiment over selected granularity"
            >
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timeData.series ?? []}>
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
                    <Area type="monotone" dataKey="engagement" name="Total Engagement" stroke="#7C5CFC" fill="#7C5CFC" fillOpacity={0.25} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <ChartCard title="Hourly Engagement Pattern" subtitle="Average engagement across 24 hours">
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={timeData.hourly_pattern ?? []}>
                      <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                      <XAxis dataKey="label" stroke="var(--chart-tick)" tick={{ fontSize: 10 }} />
                      <YAxis stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{
                          background: "var(--tooltip-bg)",
                          border: "1px solid var(--tooltip-border)",
                          borderRadius: 10,
                          fontSize: 12,
                        }}
                      />
                      <Bar dataKey="avg_engagement" name="Avg Engagement" fill="#00D4FF" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>

              <ChartCard title="Day-of-Week Performance" subtitle="Average engagement by weekday">
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={timeData.weekday_pattern ?? []}>
                      <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                      <XAxis dataKey="short_day" stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
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
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>
            </div>
          </div>
        )
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricCard
              title="Flagged Outlier Posts"
              value={anomData?.stats?.flagged_posts_count ?? 0}
              subtitle={anomData?.method}
              accent="#EF4444"
            />
            <MetricCard
              title="Daily Spikes / Drops"
              value={anomData?.stats?.flagged_days_count ?? 0}
              accent="#F59E0B"
            />
            <MetricCard
              title="IQR Upper Fence"
              value={(anomData?.stats?.iqr_upper_threshold ?? 0).toLocaleString()}
              subtitle={`Median: ${anomData?.stats?.median_engagement ?? 0}`}
              accent="#7C5CFC"
            />
            <MetricCard
              title="Mean / Std Dev"
              value={`${anomData?.stats?.mean_engagement ?? 0} / ${anomData?.stats?.std_engagement ?? 0}`}
              accent="#00D4FF"
            />
          </div>

          {(anomData?.daily_anomalies ?? []).length > 0 && (
            <ChartCard title="Unusual Daily Engagement Shifts" subtitle="Days deviating >= 1.8 SD from daily average">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {anomData?.daily_anomalies.map((d: any) => (
                  <div
                    key={d.date}
                    className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3.5 text-xs"
                  >
                    <div className="flex items-center justify-between font-bold">
                      <span>{d.date}</span>
                      <span className={d.type === "Spike" ? "text-emerald-400" : "text-rose-400"}>
                        {d.type} (Z={d.z_score})
                      </span>
                    </div>
                    <p className="text-[var(--text-secondary)] mt-1.5 mb-0">{d.explanation}</p>
                  </div>
                ))}
              </div>
            </ChartCard>
          )}

          <ChartCard
            title="Flagged Post Engagement Outliers"
            subtitle="Every flagged observation explains the statistical trigger behind it (click to inspect)"
          >
            {(anomData?.post_anomalies ?? []).length === 0 ? (
              <EmptyState title="No statistical engagement outliers detected" />
            ) : (
              <div className="space-y-2.5">
                {anomData?.post_anomalies.map((p: any) => (
                  <button
                    key={p.post_id}
                    type="button"
                    onClick={() => openPostDetail(p.post_id)}
                    className="w-full text-left p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] hover:border-[var(--accent-primary)] transition-colors space-y-1.5"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <span className="font-bold text-[var(--text-primary)]">
                        {p.post_id} • {p.platform} • {p.topic}
                      </span>
                      <span className="font-bold text-amber-400">
                        {p.engagement.toLocaleString()} interactions ({p.median_multiple}x median)
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-primary)] m-0">{p.content}</p>
                    <p className="text-[11px] text-[var(--accent-secondary)] m-0">
                      <strong>Why flagged:</strong> {p.reason}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </ChartCard>
        </div>
      )}
    </PageFrame>
  )
}

