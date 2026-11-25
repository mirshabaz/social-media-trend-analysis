import { useCallback, useEffect, useState } from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { ArrowDownUp, Search } from "lucide-react"
import { PageFrame } from "../components/PageFrame"
import {
  ChartCard,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  MetricCard,
  SentimentBadge,
} from "../components/ui/StateBlocks"
import { useApp } from "../context/AppContext"
import { api } from "../services/api"
import type { PostItem } from "../types/api"

export function EngagementPage({
  mode = "engagement",
}: {
  mode?: "engagement" | "viral"
}) {
  const { datasetVersion, openPostDetail } = useApp()
  const [sortBy, setSortBy] = useState<"total_engagement" | "likes" | "shares" | "comments">(
    "total_engagement"
  )
  const [platform, setPlatform] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [search, setSearch] = useState("")

  const [engData, setEngData] = useState<Record<string, any> | null>(null)
  const [contentData, setContentData] = useState<Record<string, any> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const loadData = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const filters = {
        platform: platform || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        search: search || undefined,
      }
      const [engRes, contentRes] = await Promise.all([
        api.engagement({ ...filters, sort_by: sortBy, limit: 20 }),
        api.contentPerformance(filters),
      ])
      setEngData(engRes.data)
      setContentData(contentRes.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load engagement analytics.")
    } finally {
      setLoading(false)
    }
  }, [platform, startDate, endDate, search, sortBy])

  useEffect(() => {
    loadData()
  }, [loadData, datasetVersion])

  const meta = engData?.meta ?? {}
  const summary = engData?.summary ?? {}
  const topPosts: PostItem[] = engData?.top_posts ?? []
  const lowestPosts: PostItem[] = engData?.lowest_posts ?? []

  return (
    <PageFrame
      eyebrow={mode === "viral" ? "Content Performance" : "Interactions & Reach"}
      title={mode === "viral" ? "Content Performance & Viral Posts" : "Engagement Analytics"}
      description="Total engagement calculated strictly as Likes + Shares + Comments from dataset metrics"
    >
      {/* Controls */}
      <div className="sp-card p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-3 text-[var(--text-muted)]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search content..."
            className="sp-input w-full !pl-8"
          />
        </div>
        <select
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
          className="sp-select w-full"
        >
          <option value="">All Platforms</option>
          {(meta.available_platforms ?? []).map((p: string) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <div className="relative">
          <ArrowDownUp size={14} className="absolute left-3 top-3 text-[var(--text-muted)] pointer-events-none" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="sp-select w-full !pl-8"
            aria-label="Sort posts by"
          >
            <option value="total_engagement">Highest Total Engagement</option>
            <option value="likes">Highest Likes</option>
            <option value="shares">Highest Shares</option>
            <option value="comments">Highest Comments</option>
          </select>
        </div>
        <input
          type="date"
          value={startDate}
          min={meta.date_min ?? undefined}
          max={meta.date_max ?? undefined}
          onChange={(e) => setStartDate(e.target.value)}
          className="sp-input w-full"
          aria-label="Start date"
        />
        <input
          type="date"
          value={endDate}
          min={meta.date_min ?? undefined}
          max={meta.date_max ?? undefined}
          onChange={(e) => setEndDate(e.target.value)}
          className="sp-input w-full"
          aria-label="End date"
        />
      </div>

      {loading ? (
        <LoadingSkeleton cards={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : !summary.total_engagement && topPosts.length === 0 ? (
        <EmptyState title="No engagement records found" />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <MetricCard
              title="Total Likes"
              value={(summary.total_likes ?? 0).toLocaleString()}
              accent="#EF4444"
            />
            <MetricCard
              title="Total Shares"
              value={(summary.total_shares ?? 0).toLocaleString()}
              accent="#00D4FF"
            />
            <MetricCard
              title="Total Comments"
              value={(summary.total_comments ?? 0).toLocaleString()}
              accent="#F59E0B"
            />
            <MetricCard
              title="Avg / Median Eng."
              value={`${summary.avg_engagement ?? 0} / ${summary.median_engagement ?? 0}`}
              subtitle={`90th percentile: ${summary.p90_engagement ?? 0}`}
              accent="#7C5CFC"
            />
            <MetricCard
              title="Engagement Rate"
              value={
                summary.engagement_rate !== null && summary.engagement_rate !== undefined
                  ? `${summary.engagement_rate}%`
                  : "Not Available"
              }
              subtitle={
                summary.engagement_rate_basis ??
                "Requires impressions, reach, or followers column"
              }
              accent="#22C55E"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard
              title="Engagement Trends Over Time"
              subtitle="Daily likes, shares, and comments"
            >
              <div className="h-[290px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={engData?.trends ?? []}>
                    <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                    <XAxis dataKey="date" stroke="var(--chart-tick)" tick={{ fontSize: 10 }} />
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
                    <Area type="monotone" dataKey="likes" name="Likes" stroke="#7C5CFC" fill="#7C5CFC" fillOpacity={0.25} />
                    <Area type="monotone" dataKey="shares" name="Shares" stroke="#00D4FF" fill="#00D4FF" fillOpacity={0.2} />
                    <Area type="monotone" dataKey="comments" name="Comments" stroke="#22C55E" fill="#22C55E" fillOpacity={0.2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard
              title="Platform Average Interaction Breakdown"
              subtitle="Average likes, shares, and comments per post"
            >
              <div className="h-[290px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={engData?.platforms ?? []}>
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
                    <Bar dataKey="avg_likes" name="Avg Likes" fill="#7C5CFC" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="avg_shares" name="Avg Shares" fill="#00D4FF" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="avg_comments" name="Avg Comments" fill="#22C55E" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard
              title="Content Length vs Average Engagement"
              subtitle="Performance across short, medium, and long posts"
            >
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={contentData?.length_analysis ?? []}>
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
                    <Bar dataKey="avg_engagement" name="Avg Engagement" fill="#7C5CFC" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard
              title="Hashtag Count vs Average Engagement"
              subtitle="How hashtag density correlates with engagement"
            >
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={contentData?.hashtag_count_analysis ?? []}>
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
                    <Bar dataKey="avg_engagement" name="Avg Engagement" fill="#00D4FF" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="avg_shares" name="Avg Shares" fill="#22C55E" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>

          {/* Best & Lowest Posts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard
              title={`Best-Performing Posts (Sorted by ${sortBy.replace("_", " ")})`}
              subtitle="Click any post to inspect full analytics"
            >
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                      <th className="py-2 pr-3">Post</th>
                      <th className="py-2 pr-2">Platform</th>
                      <th className="py-2 pr-2 text-right">Likes</th>
                      <th className="py-2 pr-2 text-right">Shares</th>
                      <th className="py-2 pr-2 text-right">Comm.</th>
                      <th className="py-2 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topPosts.slice(0, 10).map((post) => (
                      <tr
                        key={post.post_id}
                        onClick={() => openPostDetail(post.post_id)}
                        className="border-b border-[var(--border-subtle)]/60 hover:bg-[var(--bg-elevated)] cursor-pointer"
                      >
                        <td className="py-2.5 pr-3 max-w-[220px]">
                          <div className="truncate font-medium text-[var(--text-primary)]">{post.content}</div>
                          <div className="text-[10px] text-[var(--text-muted)]">{post.post_id}</div>
                        </td>
                        <td className="py-2.5 pr-2">{post.platform}</td>
                        <td className="py-2.5 pr-2 text-right">{post.likes.toLocaleString()}</td>
                        <td className="py-2.5 pr-2 text-right">{post.shares.toLocaleString()}</td>
                        <td className="py-2.5 pr-2 text-right">{post.comments.toLocaleString()}</td>
                        <td className="py-2.5 text-right font-bold text-emerald-400">
                          {post.engagement.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ChartCard>

            <ChartCard
              title="Lowest-Performing Posts"
              subtitle="Posts with minimum total interactions (click to inspect)"
            >
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                      <th className="py-2 pr-3">Post</th>
                      <th className="py-2 pr-2">Platform</th>
                      <th className="py-2 pr-2">Sentiment</th>
                      <th className="py-2 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lowestPosts.slice(0, 10).map((post) => (
                      <tr
                        key={post.post_id}
                        onClick={() => openPostDetail(post.post_id)}
                        className="border-b border-[var(--border-subtle)]/60 hover:bg-[var(--bg-elevated)] cursor-pointer"
                      >
                        <td className="py-2.5 pr-3 max-w-[250px]">
                          <div className="truncate font-medium text-[var(--text-primary)]">{post.content}</div>
                          <div className="text-[10px] text-[var(--text-muted)]">{post.post_id} • {post.topic}</div>
                        </td>
                        <td className="py-2.5 pr-2">{post.platform}</td>
                        <td className="py-2.5 pr-2">
                          <SentimentBadge sentiment={post.sentiment} />
                        </td>
                        <td className="py-2.5 text-right font-bold text-rose-400">
                          {post.engagement.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ChartCard>
          </div>
        </>
      )}
    </PageFrame>
  )
}

