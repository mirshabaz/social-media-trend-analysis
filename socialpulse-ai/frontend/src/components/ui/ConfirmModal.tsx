import { useState } from "react"
import { AlertTriangle, X } from "lucide-react"
import { useApp } from "../../context/AppContext"

export function ConfirmModal() {
  const { confirmState, closeConfirm } = useApp()
  const [busy, setBusy] = useState(false)

  if (!confirmState) return null

  async function handleConfirm() {
    if (!confirmState) return
    setBusy(true)
    try {
      await confirmState.onConfirm()
      closeConfirm()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[75] bg-black/65 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={closeConfirm}
    >
      <div className="sp-card w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start gap-3">
          <div
            className={`w-10 h-10 rounded-xl grid place-items-center shrink-0 ${
              confirmState.danger
                ? "bg-rose-500/15 text-rose-400"
                : "bg-amber-500/15 text-amber-400"
            }`}
          >
            <AlertTriangle size={20} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-[var(--text-primary)] m-0">
              {confirmState.title}
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mt-2 mb-0 leading-relaxed">
              {confirmState.message}
            </p>
          </div>
          <button
            type="button"
            onClick={closeConfirm}
            aria-label="Close dialog"
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] bg-transparent border-0"
          >
            <X size={16} />
          </button>
        </div>

        <div className="mt-6 flex items-center justify-end gap-2">
          <button type="button" onClick={closeConfirm} disabled={busy} className="sp-btn-secondary">
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={busy}
            className={
              confirmState.danger
                ? "inline-flex items-center justify-center gap-2 h-[38px] px-4 rounded-[10px] bg-rose-600 hover:bg-rose-500 text-white text-[13px] font-semibold border-0"
                : "sp-btn-primary"
            }
          >
            {busy ? "Processing..." : confirmState.confirmLabel ?? "Confirm"}
          </button>
        </div>
      </div>
    </div>
  )
}

