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
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Hash, Search, X } from "lucide-react"
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
import type { PostItem } from "../types/api"

export function HashtagsPage() {
  const { datasetVersion, openPostDetail } = useApp()
  const [searchParams, setSearchParams] = useSearchParams()

  const [search, setSearch] = useState("")
  const [platform, setPlatform] = useState("")
  const [sentiment, setSentiment] = useState("")
  const [selectedTag, setSelectedTag] = useState(searchParams.get("tag") ?? "")

  const [data, setData] = useState<Record<string, any> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const loadHashtags = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const res = await api.hashtags({
        platform: platform || undefined,
        sentiment: sentiment || undefined,
        search: search || undefined,
        tag: selectedTag || undefined,
      })
      setData(res.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load hashtag intelligence.")
    } finally {
      setLoading(false)
    }
  }, [platform, sentiment, search, selectedTag])

  useEffect(() => {
    loadHashtags()
  }, [loadHashtags, datasetVersion])

  function selectTag(tag: string) {
    setSelectedTag(tag)
    if (tag) setSearchParams({ tag })
    else setSearchParams({})
  }

  const meta = data?.meta ?? {}
  const hashtags: any[] = data?.hashtags ?? []
  const detail = data?.detail ?? null

  return (
    <PageFrame
      eyebrow="Tag Intelligence"
      title="Hashtag Explorer"
      description="Inspect hashtag frequency, average engagement, sentiment posture, co-occurring tags, and associated posts"
    >
      {/* Filters */}
      <div className="sp-card p-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-3 text-[var(--text-muted)]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search hashtags (e.g. #ai)..."
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
        <select
          value={sentiment}
          onChange={(e) => setSentiment(e.target.value)}
          className="sp-select w-full"
        >
          <option value="">All Sentiments</option>
          <option value="Positive">Positive</option>
          <option value="Negative">Negative</option>
          <option value="Neutral">Neutral</option>
        </select>
      </div>

      {loading ? (
        <LoadingSkeleton cards={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadHashtags} />
      ) : hashtags.length === 0 ? (
        <EmptyState title="No matching hashtags found" />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricCard title="Tracked Hashtags" value={hashtags.length} accent="#7C5CFC" />
            <MetricCard
              title="Most Frequent Tag"
              value={hashtags[0]?.name ?? "N/A"}
              subtitle={`${hashtags[0]?.count ?? 0} uses`}
              accent="#00D4FF"
              onClick={() => hashtags[0] && selectTag(hashtags[0].name)}
            />
            <MetricCard
              title="Highest Avg Eng. Tag"
              value={
                [...hashtags].sort((a, b) => b.avg_engagement - a.avg_engagement)[0]?.name ?? "N/A"
              }
              subtitle={`${
                [...hashtags].sort((a, b) => b.avg_engagement - a.avg_engagement)[0]?.avg_engagement ?? 0
              } avg/post`}
              accent="#22C55E"
            />
            <MetricCard
              title="Selected Profile"
              value={detail?.tag ?? "None selected"}
              subtitle="Click any hashtag below"
              accent="#F59E0B"
            />
          </div>

          {/* Selected Hashtag Detail Profile */}
          {detail && detail.summary && (
            <div className="sp-card p-5 border-[#7C5CFC]/50 space-y-5">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border-subtle)] pb-3">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--accent-primary)]">
                    Hashtag Profile
                  </span>
                  <h2 className="text-xl font-bold m-0 mt-0.5 flex items-center gap-2">
                    <Hash size={18} className="text-[var(--accent-secondary)]" />
                    {detail.tag}
                  </h2>
                  <p className="text-xs text-[var(--text-secondary)] mt-1 mb-0">
                    {detail.summary.count} mentions • {detail.summary.engagement.toLocaleString()} total interactions (avg {detail.summary.avg_engagement}) • {detail.summary.positive_pct}% positive / {detail.summary.negative_pct}% negative
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => selectTag("")}
                  className="sp-btn-secondary !h-8 !px-3 !text-xs"
                >
                  <X size={14} /> Close Profile
                </button>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="lg:col-span-2 h-[220px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={detail.timeline ?? []}>
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
                      <Area type="monotone" dataKey="engagement" name="Engagement" stroke="#00D4FF" fill="#00D4FF" fillOpacity={0.22} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <div className="font-semibold text-[var(--text-secondary)] mb-1.5">
                      Related Co-occurring Hashtags
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {(detail.summary.related_hashtags ?? []).map((rel: any) => (
                        <button
                          key={rel.name}
                          type="button"
                          onClick={() => selectTag(rel.name)}
                          className="rounded-full bg-[var(--accent-soft)] text-[var(--accent-primary)] px-2.5 py-1 text-[11px] font-medium border-0"
                        >
                          {rel.name} ({rel.co_occurrences})
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="font-semibold text-[var(--text-secondary)] mb-1.5">
                      Platform Breakdown
                    </div>
                    <div className="space-y-1">
                      {(detail.platforms ?? []).map((pl: any) => (
                        <div key={pl.name} className="flex justify-between">
                          <span>{pl.name}</span>
                          <strong>{pl.posts} posts</strong>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <div className="text-xs font-semibold text-[var(--text-secondary)] mb-2">
                  Associated Posts (click to inspect)
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-64 overflow-y-auto">
                  {(detail.posts ?? []).map((post: PostItem) => (
                    <button
                      key={post.post_id}
                      type="button"
                      onClick={() => openPostDetail(post.post_id)}
                      className="text-left p-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] hover:border-[var(--accent-primary)]"
                    >
                      <div className="flex items-center justify-between text-[11px] font-semibold">
                        <span>
                          {post.post_id} • {post.platform}
                        </span>
                        <SentimentBadge sentiment={post.sentiment} />
                      </div>
                      <div className="text-xs text-[var(--text-secondary)] mt-1 line-clamp-2">
                        {post.content}
                      </div>
                      <div className="text-[11px] text-[var(--accent-secondary)] font-semibold mt-1">
                        {post.engagement.toLocaleString()} interactions
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Charts + Hashtags Ranking */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard
              title="Top Hashtags by Frequency & Avg Engagement"
              subtitle="Click any bar to open that hashtag's profile"
            >
              <div className="h-[320px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={hashtags.slice(0, 12)}>
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
                    <Bar
                      dataKey="count"
                      name="Mentions"
                      radius={[6, 6, 0, 0]}
                      className="cursor-pointer"
                      onClick={(entry: any) => entry?.name && selectTag(entry.name)}
                    >
                      {hashtags.slice(0, 12).map((_, idx) => (
                        <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                    <Bar dataKey="avg_engagement" name="Avg Engagement" fill="#00D4FF" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard title="Hashtag Rankings" subtitle="Click any row to open full hashtag profile">
              <div className="overflow-x-auto max-h-[320px]">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                      <th className="py-2 pr-3">Hashtag</th>
                      <th className="py-2 pr-2 text-right">Uses</th>
                      <th className="py-2 pr-2 text-right">Avg Eng.</th>
                      <th className="py-2 pr-2 text-right">Pos %</th>
                      <th className="py-2">Top Channel</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hashtags.map((h) => (
                      <tr
                        key={h.name}
                        onClick={() => selectTag(h.name)}
                        className={`border-b border-[var(--border-subtle)]/60 hover:bg-[var(--bg-elevated)] cursor-pointer ${
                          selectedTag.toLowerCase() === h.name.toLowerCase()
                            ? "bg-[var(--accent-soft)]"
                            : ""
                        }`}
                      >
                        <td className="py-2.5 pr-3 font-semibold text-[var(--accent-primary)]">
                          {h.name}
                        </td>
                        <td className="py-2.5 pr-2 text-right">{h.count}</td>
                        <td className="py-2.5 pr-2 text-right font-semibold">{h.avg_engagement}</td>
                        <td className="py-2.5 pr-2 text-right text-emerald-400">{h.positive_pct}%</td>
                        <td className="py-2.5">{h.top_platform}</td>
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

