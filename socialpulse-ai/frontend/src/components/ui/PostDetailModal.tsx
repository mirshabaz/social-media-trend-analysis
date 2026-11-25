import { useEffect, useState } from "react"
import { Calendar, Heart, MessageSquare, Share2, Tag, TrendingUp, User, X } from "lucide-react"
import { useApp } from "../../context/AppContext"
import { api } from "../../services/api"
import type { PostItem } from "../../types/api"
import { SentimentBadge } from "./StateBlocks"

export function PostDetailModal() {
  const { selectedPostId, closePostDetail } = useApp()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [detail, setDetail] = useState<{
    post: PostItem
    benchmarks: Record<string, number>
  } | null>(null)

  useEffect(() => {
    if (!selectedPostId) {
      setDetail(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError("")
    api
      .postDetail(selectedPostId)
      .then((res) => {
        if (!cancelled) setDetail(res.data as any)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load post.")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedPostId])

  if (!selectedPostId) return null

  return (
    <div
      className="fixed inset-0 z-[70] bg-black/65 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={closePostDetail}
    >
      <div
        className="sp-card w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-[var(--border-subtle)] pb-4">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-widest text-[var(--accent-primary)]">
              Post Intelligence Detail
            </span>
            <h2 className="text-lg font-bold text-[var(--text-primary)] mt-1 mb-0">
              {selectedPostId}
            </h2>
          </div>
          <button
            type="button"
            onClick={closePostDetail}
            aria-label="Close post details"
            className="sp-btn-secondary !h-8 !w-8 !p-0"
          >
            <X size={16} />
          </button>
        </div>

        {loading && <div className="sp-skeleton h-48 mt-4" />}
        {error && <p className="text-sm text-rose-400 mt-4">{error}</p>}

        {detail && !loading && (
          <div className="mt-4 space-y-5">
            <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-secondary)]">
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--bg-elevated)] px-2.5 py-1 font-medium text-[var(--text-primary)]">
                <User size={13} /> @{detail.post.author}
              </span>
              <span className="rounded-lg bg-[var(--accent-soft)] text-[var(--accent-primary)] px-2.5 py-1 font-semibold">
                {detail.post.platform}
              </span>
              <span className="rounded-lg bg-[var(--bg-elevated)] px-2.5 py-1">
                {detail.post.topic}
              </span>
              <SentimentBadge sentiment={detail.post.sentiment} />
              {detail.post.timestamp && (
                <span className="inline-flex items-center gap-1 ml-auto">
                  <Calendar size={13} /> {detail.post.timestamp}
                </span>
              )}
            </div>

            <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-input)] p-4 text-sm leading-relaxed text-[var(--text-primary)]">
              {detail.post.content}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3">
                <div className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                  <Heart size={13} className="text-rose-400" /> Likes
                </div>
                <div className="text-lg font-bold mt-1">{detail.post.likes.toLocaleString()}</div>
              </div>
              <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3">
                <div className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                  <Share2 size={13} className="text-sky-400" /> Shares
                </div>
                <div className="text-lg font-bold mt-1">{detail.post.shares.toLocaleString()}</div>
              </div>
              <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3">
                <div className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                  <MessageSquare size={13} className="text-amber-400" /> Comments
                </div>
                <div className="text-lg font-bold mt-1">{detail.post.comments.toLocaleString()}</div>
              </div>
              <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3">
                <div className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                  <TrendingUp size={13} className="text-[#7C5CFC]" /> Total Eng.
                </div>
                <div className="text-lg font-bold mt-1">{detail.post.engagement.toLocaleString()}</div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="rounded-xl border border-[var(--border-subtle)] p-3.5 space-y-1.5">
                <div className="font-semibold text-[var(--text-primary)]">Performance Benchmarks</div>
                <div className="text-[var(--text-secondary)]">
                  Engagement Percentile: <strong className="text-[var(--text-primary)]">{detail.benchmarks.engagement_percentile}th</strong>
                </div>
                <div className="text-[var(--text-secondary)]">
                  vs Dataset Avg ({detail.benchmarks.dataset_avg_engagement}):{" "}
                  <strong className={detail.benchmarks.vs_dataset_avg_pct >= 0 ? "text-emerald-400" : "text-rose-400"}>
                    {detail.benchmarks.vs_dataset_avg_pct >= 0 ? "+" : ""}
                    {detail.benchmarks.vs_dataset_avg_pct}%
                  </strong>
                </div>
                <div className="text-[var(--text-secondary)]">
                  {detail.post.platform} Avg: <strong className="text-[var(--text-primary)]">{detail.benchmarks.platform_avg_engagement}</strong>
                </div>
              </div>

              <div className="rounded-xl border border-[var(--border-subtle)] p-3.5 space-y-1.5">
                <div className="font-semibold text-[var(--text-primary)]">NLP & Sentiment Indicators</div>
                <div className="text-[var(--text-secondary)]">
                  Polarity Score: <strong className="text-[var(--text-primary)]">{detail.post.sentiment_polarity}</strong>
                </div>
                <div className="text-[var(--text-secondary)]">
                  Emotion Signal: <strong className="text-[var(--text-primary)]">{detail.post.detected_emotion}</strong>
                </div>
                <div className="text-[var(--text-secondary)]">
                  Source: <strong className="text-[var(--text-primary)]">{detail.post.sentiment_source === "dataset_label" ? "Dataset Label" : "Automated NLP"}</strong>
                </div>
              </div>
            </div>

            {detail.post.hashtags.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-[var(--text-secondary)] mb-2 flex items-center gap-1.5">
                  <Tag size={13} /> Extracted Hashtags
                </div>
                <div className="flex flex-wrap gap-2">
                  {detail.post.hashtags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full bg-[var(--accent-soft)] text-[var(--accent-primary)] px-2.5 py-1 text-xs font-medium"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

