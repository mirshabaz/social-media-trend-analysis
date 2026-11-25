import { useCallback, useEffect, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { ArrowDownRight, ArrowUpRight, Info, Minus, Search, TrendingUp } from "lucide-react"
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

export function TrendsPage({
  defaultTab = "topics",
}: {
  defaultTab?: "topics" | "emerging" | "keywords" | "prediction"
}) {
  const { datasetVersion, openPostDetail } = useApp()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const [tab, setTab] = useState(defaultTab)
  const [platform, setPlatform] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [keywordFilter, setKeywordFilter] = useState("")
  const [selectedTopic, setSelectedTopic] = useState<string>(searchParams.get("topic") ?? "")
  const [topicPosts, setTopicPosts] = useState<PostItem[]>([])
  const [data, setData] = useState<Record<string, any> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    setTab(defaultTab)
  }, [defaultTab])

  const loadTrends = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const res = await api.trends({
        platform: platform || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        search: keywordFilter || undefined,
      })
      setData(res.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trend explorer.")
    } finally {
      setLoading(false)
    }
  }, [platform, startDate, endDate, keywordFilter])

  useEffect(() => {
    loadTrends()
  }, [loadTrends, datasetVersion])

  useEffect(() => {
    if (!selectedTopic) {
      setTopicPosts([])
      return
    }
    api
      .posts({ topic: selectedTopic, platform: platform || undefined, page: 1, page_size: 8 })
      .then((res) => setTopicPosts(res.data.posts ?? []))
      .catch(() => setTopicPosts([]))
  }, [selectedTopic, platform, datasetVersion])

  const meta = data?.meta ?? {}
  const topics: any[] = data?.topics ?? []
  const emerging: any[] = data?.emerging_topics ?? []
  const hashtags: any[] = data?.hashtags ?? []
  const keywords: any[] = data?.keywords ?? []
  const timeline: any[] = data?.topic_timeline ?? []
  const timelineTopics =
    timeline.length > 0 ? Object.keys(timeline[0]).filter((k) => k !== "period") : []

  const selectedTopicObj = topics.find((t) => t.name === selectedTopic) ?? null

  const filteredTopics = keywordFilter.trim()
    ? topics.filter((t) => t.name.toLowerCase().includes(keywordFilter.toLowerCase()))
    : topics

  const filteredKeywords = keywordFilter.trim()
    ? keywords.filter((k) => k.keyword.toLowerCase().includes(keywordFilter.toLowerCase()))
    : keywords

  return (
    <PageFrame
      eyebrow="Discovery & Velocity"
      title={
        tab === "emerging"
          ? "Emerging Trends"
          : tab === "keywords"
            ? "Keyword Intelligence"
            : tab === "prediction"
              ? "Historical Trend Growth Analysis"
              : "Social Media Trend Explorer"
      }
      description="Explore topic volume, period-over-period growth, hashtag momentum, and TF-IDF keyword signals"
      actions={
        <div className="flex flex-wrap gap-1.5">
          {[
            { id: "topics", label: "Trending Topics" },
            { id: "emerging", label: "Emerging Growth" },
            { id: "keywords", label: "TF-IDF Keywords" },
            { id: "prediction", label: "Growth vs Forecast" },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id as any)}
              className={tab === item.id ? "sp-btn-primary !h-8 !text-xs" : "sp-btn-secondary !h-8 !text-xs"}
            >
              {item.label}
            </button>
          ))}
        </div>
      }
    >
      {/* Filters */}
      <div className="sp-card p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-3 text-[var(--text-muted)]" />
          <input
            value={keywordFilter}
            onChange={(e) => setKeywordFilter(e.target.value)}
            placeholder="Search topics or keywords..."
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

      {data?.historical_note && (
        <div className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-4 py-2.5 text-xs text-sky-300 flex items-start gap-2">
          <Info size={15} className="shrink-0 mt-0.5" />
          <span>{data.historical_note}</span>
        </div>
      )}

      {loading ? (
        <LoadingSkeleton cards={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadTrends} />
      ) : filteredTopics.length === 0 && filteredKeywords.length === 0 ? (
        <EmptyState
          title="No trend records matched"
          action={
            <button
              type="button"
              onClick={() => {
                setPlatform("")
                setStartDate("")
                setEndDate("")
                setKeywordFilter("")
              }}
              className="sp-btn-primary"
            >
              Reset Trend Filters
            </button>
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricCard
              title="Discovered Topics"
              value={topics.length}
              subtitle={topics[0] ? `Top: ${topics[0].name}` : undefined}
              accent="#7C5CFC"
            />
            <MetricCard
              title="Fastest Rising Topic"
              value={emerging[0] ? emerging[0].name : "Insufficient dates"}
              subtitle={
                emerging[0]?.growth_pct !== null && emerging[0]?.growth_pct !== undefined
                  ? `${emerging[0].growth_pct >= 0 ? "+" : ""}${emerging[0].growth_pct}% period change`
                  : "Requires multi-day timestamps"
              }
              accent="#22C55E"
            />
            <MetricCard
              title="Top Hashtag"
              value={hashtags[0]?.name ?? "N/A"}
              subtitle={hashtags[0] ? `${hashtags[0].count} mentions` : undefined}
              accent="#00D4FF"
              onClick={() =>
                hashtags[0] && navigate(`/hashtags?tag=${encodeURIComponent(hashtags[0].name)}`)
              }
            />
            <MetricCard
              title="Top Extracted Term"
              value={keywords[0]?.keyword ?? "N/A"}
              subtitle={keywords[0] ? `TF-IDF ${keywords[0].tfidf_score}` : undefined}
              accent="#F59E0B"
            />
          </div>

          {/* Selected Topic Drilldown Drawer */}
          {selectedTopicObj && (
            <div className="sp-card p-5 border-[#7C5CFC]/50 space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--accent-primary)]">
                    Topic Drill-Down
                  </span>
                  <h2 className="text-lg font-bold m-0 mt-0.5">{selectedTopicObj.name}</h2>
                  <p className="text-xs text-[var(--text-secondary)] mt-1 mb-0">
                    {selectedTopicObj.posts} posts ({selectedTopicObj.share_pct}% share) •{" "}
                    {selectedTopicObj.engagement.toLocaleString()} total interactions (avg{" "}
                    {selectedTopicObj.avg_engagement}/post) • Top platform:{" "}
                    {selectedTopicObj.top_platform}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedTopic("")
                    setSearchParams({})
                  }}
                  className="sp-btn-secondary !h-8 !text-xs"
                >
                  Close Detail
                </button>
              </div>
              {topicPosts.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {topicPosts.map((post) => (
                    <button
                      key={post.post_id}
                      type="button"
                      onClick={() => openPostDetail(post.post_id)}
                      className="text-left p-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] hover:border-[var(--accent-primary)] transition-colors"
                    >
                      <div className="flex items-center justify-between gap-2 text-[11px] font-semibold">
                        <span>
                          {post.post_id} • {post.platform}
                        </span>
                        <SentimentBadge sentiment={post.sentiment} />
                      </div>
                      <p className="text-xs text-[var(--text-secondary)] mt-1.5 mb-1 line-clamp-2">
                        {post.content}
                      </p>
                      <div className="text-[11px] text-[var(--accent-secondary)] font-semibold">
                        {post.engagement.toLocaleString()} interactions
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab !== "keywords" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <ChartCard
                title="Topic Volume & Engagement Comparison"
                subtitle="Click any bar to inspect posts in that topic"
              >
                <div className="h-[310px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={filteredTopics.slice(0, 10)}>
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
                        dataKey="posts"
                        name="Posts"
                        fill="#7C5CFC"
                        radius={[6, 6, 0, 0]}
                        className="cursor-pointer"
                        onClick={(entry: any) => {
                          if (entry?.name) setSelectedTopic(entry.name)
                        }}
                      />
                      <Bar
                        dataKey="avg_engagement"
                        name="Avg Engagement"
                        fill="#00D4FF"
                        radius={[6, 6, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>

              <ChartCard
                title="Historical Topic Evolution Over Time"
                subtitle="Weekly post volume across top topics"
              >
                {timeline.length === 0 ? (
                  <EmptyState
                    title="Insufficient timestamp history"
                    message="Upload a dataset with multi-week dates to visualize topic evolution."
                  />
                ) : (
                  <div className="h-[310px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={timeline}>
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
                        {timelineTopics.map((topicName, idx) => (
                          <Line
                            key={topicName}
                            type="monotone"
                            dataKey={topicName}
                            stroke={CHART_COLORS[idx % CHART_COLORS.length]}
                            strokeWidth={2}
                            dot={false}
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </ChartCard>
            </div>
          )}

          {/* Trend Ranking Table */}
          {tab !== "keywords" && (
            <ChartCard
              title="Topic Ranking & Growth Velocity"
              subtitle="Click any topic row to inspect matching posts and platform leadership"
            >
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                      <th className="py-2.5 pr-3">Topic</th>
                      <th className="py-2.5 pr-3">Posts</th>
                      <th className="py-2.5 pr-3">Share</th>
                      <th className="py-2.5 pr-3">Total Eng.</th>
                      <th className="py-2.5 pr-3">Avg Eng.</th>
                      <th className="py-2.5 pr-3">Historical Growth</th>
                      <th className="py-2.5 pr-3">Top Platform</th>
                      <th className="py-2.5">Sentiment Mix</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTopics.map((t) => (
                      <tr
                        key={t.name}
                        onClick={() => setSelectedTopic(t.name)}
                        className={`border-b border-[var(--border-subtle)]/60 hover:bg-[var(--bg-elevated)] cursor-pointer ${
                          selectedTopic === t.name ? "bg-[var(--accent-soft)]" : ""
                        }`}
                      >
                        <td className="py-2.5 pr-3 font-semibold text-[var(--text-primary)]">
                          <span className="inline-flex items-center gap-1.5">
                            <TrendingUp size={13} className="text-[var(--accent-primary)]" />
                            {t.name}
                          </span>
                        </td>
                        <td className="py-2.5 pr-3">{t.posts.toLocaleString()}</td>
                        <td className="py-2.5 pr-3">{t.share_pct}%</td>
                        <td className="py-2.5 pr-3">{t.engagement.toLocaleString()}</td>
                        <td className="py-2.5 pr-3 font-semibold">{t.avg_engagement}</td>
                        <td className="py-2.5 pr-3">
                          {t.growth_pct === null || t.growth_pct === undefined ? (
                            <span className="text-[var(--text-muted)]">N/A</span>
                          ) : (
                            <span
                              className={`inline-flex items-center gap-1 font-semibold ${
                                t.growth_pct > 0
                                  ? "text-emerald-400"
                                  : t.growth_pct < 0
                                    ? "text-rose-400"
                                    : "text-[var(--text-secondary)]"
                              }`}
                            >
                              {t.growth_pct > 0 ? (
                                <ArrowUpRight size={13} />
                              ) : t.growth_pct < 0 ? (
                                <ArrowDownRight size={13} />
                              ) : (
                                <Minus size={13} />
                              )}
                              {t.growth_pct > 0 ? "+" : ""}
                              {t.growth_pct}%
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 pr-3">{t.top_platform}</td>
                        <td className="py-2.5">
                          <span className="text-emerald-400">{t.positive_pct}%+</span> /{" "}
                          <span className="text-rose-400">{t.negative_pct}%-</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ChartCard>
          )}

          {/* Keywords Intelligence Section */}
          <ChartCard
            title="TF-IDF Keyword Intelligence"
            subtitle="Most distinctive terms and bigrams extracted from active post content"
          >
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={filteredKeywords.slice(0, 12)} layout="vertical">
                    <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                    <XAxis type="number" stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <YAxis
                      type="category"
                      dataKey="keyword"
                      width={130}
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
                    <Bar dataKey="tfidf_score" name="TF-IDF Score" fill="#00D4FF" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="overflow-x-auto max-h-[300px]">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                      <th className="py-2 pr-3">Keyword / Bigram</th>
                      <th className="py-2 pr-3">TF-IDF</th>
                      <th className="py-2 pr-3">Posts</th>
                      <th className="py-2">Avg Eng.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredKeywords.map((kw) => (
                      <tr key={kw.keyword} className="border-b border-[var(--border-subtle)]/60">
                        <td className="py-2 pr-3 font-semibold text-[var(--text-primary)]">{kw.keyword}</td>
                        <td className="py-2 pr-3">{kw.tfidf_score}</td>
                        <td className="py-2 pr-3">{kw.frequency}</td>
                        <td className="py-2 text-[var(--accent-secondary)] font-semibold">{kw.avg_engagement}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </ChartCard>
        </>
      )}
    </PageFrame>
  )
}

