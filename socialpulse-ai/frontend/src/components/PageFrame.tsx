import { motion } from "framer-motion"
import type { ReactNode } from "react"

export function PageFrame({
  eyebrow,
  title,
  description,
  actions,
  children,
}: {
  eyebrow: string
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22 }}
      className="max-w-[1600px] mx-auto px-4 sm:px-7 py-6 space-y-6"
    >
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-[var(--accent-primary)] m-0">
            {eyebrow}
          </p>
          <h1 className="text-2xl sm:text-[28px] font-bold tracking-tight text-[var(--text-primary)] mt-1.5 mb-0">
            {title}
          </h1>
          {description && (
            <p className="text-[13px] text-[var(--text-secondary)] mt-1.5 mb-0 max-w-3xl">
              {description}
            </p>
          )}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
      </div>
      {children}
    </motion.div>
  )
}
