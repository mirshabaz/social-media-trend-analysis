import { AlertTriangle, CheckCircle2, Info, RefreshCw, Sparkles, X, XCircle } from "lucide-react"
import type { CSSProperties, ReactNode } from "react"
import { useApp } from "../../context/AppContext"

export const CHART_COLORS = [
  "#7C5CFC",
  "#00D4FF",
  "#22C55E",
  "#F59E0B",
  "#EF4444",
  "#EC4899",
  "#38BDF8",
  "#A855F7",
]

export const SENTIMENT_COLORS: Record<string, string> = {
  Positive: "#22C55E",
  Negative: "#EF4444",
  Neutral: "#94A3B8",
}

export function MetricCard({
  title,
  value,
  subtitle,
  accent = "#7C5CFC",
  badge,
  onClick,
}: {
  title: string
  value: string | number
  subtitle?: string
  accent?: string
  badge?: string
  onClick?: () => void
}) {
  const Tag = onClick ? "button" : "article"
  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      className={`sp-card sp-card-hover relative overflow-hidden p-4 text-left w-full ${
        onClick ? "cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#7C5CFC]" : ""
      }`}
      style={{ "--card-accent": accent } as CSSProperties}
    >
      <span
        className="absolute inset-x-0 top-0 h-[2px]"
        style={{ background: accent }}
      />
      <div className="flex items-center justify-between gap-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
        <span className="truncate">{title}</span>
        {badge && (
          <span
            className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold"
            style={{ background: `${accent}22`, color: accent }}
          >
            {badge}
          </span>
        )}
      </div>
      <div className="mt-3 text-2xl font-bold tracking-tight text-[var(--text-primary)] truncate">
        {value}
      </div>
      {subtitle && (
        <div className="mt-1.5 text-xs text-[var(--text-secondary)] truncate">
          {subtitle}
        </div>
      )}
    </Tag>
  )
}

export function ChartCard({
  title,
  subtitle,
  action,
  onRefresh,
  refreshing,
  className = "",
  children,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
  onRefresh?: () => void
  refreshing?: boolean
  className?: string
  children: ReactNode
}) {
  return (
    <article className={`sp-card p-5 min-w-0 ${className}`}>
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-[var(--text-primary)] m-0 truncate">
            {title}
          </h2>
          {subtitle && (
            <p className="text-xs text-[var(--text-secondary)] mt-1 mb-0">
              {subtitle}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {action}
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              title="Refresh panel"
              aria-label={`Refresh ${title}`}
              className="sp-btn-secondary !h-8 !w-8 !p-0"
            >
              <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
            </button>
          )}
        </div>
      </div>
      {children}
    </article>
  )
}

export function SentimentBadge({ sentiment }: { sentiment: string }) {
  const s = sentiment || "Neutral"
  const style =
    s === "Positive"
      ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
      : s === "Negative"
        ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
        : "bg-slate-500/15 text-slate-400 border-slate-500/30"
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${style}`}>
      {s}
    </span>
  )
}

export function LoadingSkeleton({ cards = 4 }: { cards?: number }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: cards }).map((_, idx) => (
          <div key={idx} className="sp-skeleton h-28" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="sp-skeleton h-72 lg:col-span-2" />
        <div className="sp-skeleton h-72" />
      </div>
    </div>
  )
}

export function EmptyState({
  title = "No matching records",
  message = "Try adjusting your filters or switching the active dataset.",
  action,
}: {
  title?: string
  message?: string
  action?: ReactNode
}) {
  return (
    <div className="sp-card p-10 text-center flex flex-col items-center justify-center gap-3">
      <div className="w-12 h-12 rounded-2xl bg-[var(--accent-soft)] text-[var(--accent-primary)] grid place-items-center">
        <Sparkles size={22} />
      </div>
      <h3 className="text-base font-semibold text-[var(--text-primary)] m-0">{title}</h3>
      <p className="text-sm text-[var(--text-secondary)] max-w-md m-0">{message}</p>
      {action}
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="sp-card p-6 border-rose-500/40 bg-rose-500/5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div className="flex items-start gap-3">
        <AlertTriangle size={20} className="text-rose-400 shrink-0 mt-0.5" />
        <div>
          <h3 className="text-sm font-semibold text-[var(--text-primary)] m-0">
            Unable to load analytics data
          </h3>
          <p className="text-xs text-[var(--text-secondary)] mt-1 mb-0">{message}</p>
        </div>
      </div>
      {onRetry && (
        <button type="button" onClick={onRetry} className="sp-btn-secondary shrink-0">
          <RefreshCw size={14} /> Retry
        </button>
      )}
    </div>
  )
}

export function ToastContainer() {
  const { toasts, dismissToast } = useApp()
  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-5 right-5 z-[80] flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4 sm:px-0">
      {toasts.map((toast) => {
        const Icon =
          toast.variant === "success"
            ? CheckCircle2
            : toast.variant === "error"
              ? XCircle
              : toast.variant === "warning"
                ? AlertTriangle
                : Info
        const color =
          toast.variant === "success"
            ? "text-emerald-400 border-emerald-500/35"
            : toast.variant === "error"
              ? "text-rose-400 border-rose-500/35"
              : toast.variant === "warning"
                ? "text-amber-400 border-amber-500/35"
                : "text-sky-400 border-sky-500/35"
        return (
          <div
            key={toast.id}
            className={`sp-card pointer-events-auto p-3.5 flex items-start gap-3 shadow-2xl border ${color}`}
          >
            <Icon size={18} className="shrink-0 mt-0.5" />
            <div className="min-w-0 flex-1">
              <div className="text-xs font-semibold text-[var(--text-primary)]">
                {toast.title}
              </div>
              {toast.message && (
                <div className="text-xs text-[var(--text-secondary)] mt-0.5">
                  {toast.message}
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => dismissToast(toast.id)}
              aria-label="Dismiss notification"
              className="text-[var(--text-muted)] hover:text-[var(--text-primary)] bg-transparent border-0 p-0.5"
            >
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}

