import { useCallback, useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Check, Info } from "lucide-react"
import { PageFrame } from "../components/PageFrame"
import {
  ChartCard,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
} from "../components/ui/StateBlocks"
import { useApp } from "../context/AppContext"
import { api } from "../services/api"

export function PlatformsPage({ mode = "platforms" }: { mode?: "platforms" | "audience" }) {
  const { datasetVersion, openPostDetail } = useApp()
  const [searchParams] = useSearchParams()
  const focus = searchParams.get("focus")

  const [allPlatforms, setAllPlatforms] = useState<string[]>([])
  const [selected, setSelected] = useState<string[]>(focus ? [focus] : [])
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [platforms, setPlatforms] = useState<any[]>([])
  const [meta, setMeta] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const loadPlatforms = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const res = await api.platforms({
        platforms: selected.length > 0 ? selected.join(",") : undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      })
      setPlatforms(res.data ?? [])
      setMeta(res.meta ?? {})
      const avail: string[] = res.meta?.available_platforms ?? []
      setAllPlatforms(avail)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load platform comparison.")
    } finally {
      setLoading(false)
    }
  }, [selected, startDate, endDate])

  useEffect(() => {
    loadPlatforms()
  }, [loadPlatforms, datasetVersion])

  function togglePlatform(name: string) {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((item) => item !== name) : [...prev, name]
    )
  }

  const sentimentChartData = platforms.map((p) => ({
    name: p.name,
    Positive: p.sentiment?.Positive ?? 0,
    Neutral: p.sentiment?.Neutral ?? 0,
    Negative: p.sentiment?.Negative ?? 0,
  }))

  return (
    <PageFrame
      eyebrow={mode === "audience" ? "Channel Reach & Behavior" : "Cross-Channel Benchmark"}
      title={mode === "audience" ? "Audience & Platform Insights" : "Platform Comparison"}
      description="Compare two or more social platforms using actual dataset volume, engagement, sentiment, and topics"
    >
      {mode === "audience" && (
        <div className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-4 py-2.5 text-xs text-sky-300 flex items-start gap-2">
          <Info size={15} className="shrink-0 mt-0.5" />
          <span>
            Insights below reflect observed channel activity and interactions in the active CSV dataset without invented age, gender, or follower demographics.
          </span>
        </div>
      )}

      {/* Multi-Platform Selector + Dates */}
      <div className="sp-card p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-[var(--text-secondary)] mr-1">
            Compare Channels:
          </span>
          <button
            type="button"
            onClick={() => setSelected([])}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
              selected.length === 0
                ? "bg-[var(--accent-primary)] text-white border-[var(--accent-primary)]"
                : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] border-[var(--border-subtle)]"
            }`}
          >
            All ({allPlatforms.length})
          </button>
          {allPlatforms.map((name) => {
            const active = selected.includes(name)
            return (
              <button
                key={name}
                type="button"
                onClick={() => togglePlatform(name)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
                  active
                    ? "bg-[var(--accent-soft)] text-[var(--accent-primary)] border-[var(--accent-primary)]"
                    : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] border-[var(--border-subtle)] hover:text-[var(--text-primary)]"
                }`}
              >
                {active && <Check size={12} />}
                {name}
              </button>
            )
          })}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <input
            type="date"
            value={startDate}
            min={meta.date_min ?? undefined}
            max={meta.date_max ?? undefined}
            onChange={(e) => setStartDate(e.target.value)}
            className="sp-input !h-9"
            aria-label="Start date"
          />
          <input
            type="date"
            value={endDate}
            min={meta.date_min ?? undefined}
            max={meta.date_max ?? undefined}
            onChange={(e) => setEndDate(e.target.value)}
            className="sp-input !h-9"
            aria-label="End date"
          />
        </div>
      </div>

      {loading ? (
        <LoadingSkeleton cards={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadPlatforms} />
      ) : platforms.length === 0 ? (
        <EmptyState title="No platform metrics found for current selection" />
      ) : (
        <>
          {/* Platform Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {platforms.map((p) => (
              <article key={p.name} className="sp-card p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-[var(--text-primary)] m-0">
                    {p.name}
                  </h3>
                  <span className="rounded-full bg-[var(--accent-soft)] text-[var(--accent-primary)] px-2.5 py-0.5 text-[11px] font-bold">
                    {p.post_share_pct}% share
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-xl bg-[var(--bg-elevated)] p-2.5">
                    <div className="text-[var(--text-muted)]">Posts</div>
                    <div className="text-base font-bold mt-0.5">{p.posts.toLocaleString()}</div>
                  </div>
                  <div className="rounded-xl bg-[var(--bg-elevated)] p-2.5">
                    <div className="text-[var(--text-muted)]">Avg Eng.</div>
                    <div className="text-base font-bold mt-0.5 text-[var(--accent-secondary)]">
                      {p.avg_engagement}
                    </div>
                  </div>
                  <div className="rounded-xl bg-[var(--bg-elevated)] p-2.5">
                    <div className="text-[var(--text-muted)]">Total Eng.</div>
                    <div className="text-sm font-bold mt-0.5">{p.engagement.toLocaleString()}</div>
                  </div>
                  <div className="rounded-xl bg-[var(--bg-elevated)] p-2.5">
                    <div className="text-[var(--text-muted)]">Positive %</div>
                    <div className="text-sm font-bold mt-0.5 text-emerald-400">
                      {p.sentiment?.Positive ?? 0}%
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs">
                  <div className="font-semibold text-[var(--text-secondary)]">Top Topics</div>
                  <div className="flex flex-wrap gap-1">
                    {(p.top_topics ?? []).slice(0, 3).map((t: any) => (
                      <span
                        key={t.name}
                        className="rounded-md bg-[var(--bg-input)] border border-[var(--border-subtle)] px-2 py-0.5 text-[11px]"
                      >
                        {t.name}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="space-y-1.5 text-xs">
                  <div className="font-semibold text-[var(--text-secondary)]">Top Hashtags</div>
                  <div className="flex flex-wrap gap-1">
                    {(p.top_hashtags ?? []).slice(0, 4).map((h: any) => (
                      <span
                        key={h.name}
                        className="rounded-full bg-[var(--accent-soft)] text-[var(--accent-primary)] px-2 py-0.5 text-[11px]"
                      >
                        {h.name}
                      </span>
                    ))}
                  </div>
                </div>

                {p.best_post && (
                  <button
                    type="button"
                    onClick={() => openPostDetail(p.best_post.post_id)}
                    className="w-full text-left rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-input)] p-2.5 hover:border-[var(--accent-primary)] transition-colors"
                  >
                    <div className="text-[10px] font-bold uppercase text-[var(--accent-primary)]">
                      Top Post ({p.best_post.engagement.toLocaleString()} eng)
                    </div>
                    <div className="text-[11px] text-[var(--text-secondary)] truncate mt-0.5">
                      {p.best_post.content}
                    </div>
                  </button>
                )}
              </article>
            ))}
          </div>

          {/* Comparison Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ChartCard
              title="Total vs Average Engagement Comparison"
              subtitle="Volume vs per-post efficiency"
            >
              <div className="h-[290px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={platforms}>
                    <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="4 4" />
                    <XAxis dataKey="name" stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="left" stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="right" orientation="right" stroke="var(--chart-tick)" tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "var(--tooltip-bg)",
                        border: "1px solid var(--tooltip-border)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Legend />
                    <Bar yAxisId="left" dataKey="engagement" name="Total Engagement" fill="#7C5CFC" radius={[6, 6, 0, 0]} />
                    <Bar yAxisId="right" dataKey="avg_engagement" name="Avg / Post" fill="#00D4FF" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard
              title="Sentiment Distribution Across Platforms (%)"
              subtitle="Positive, Neutral, and Negative shares"
            >
              <div className="h-[290px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={sentimentChartData}>
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
          </div>
        </>
      )}
    </PageFrame>
  )
}

