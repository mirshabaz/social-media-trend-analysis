import { useEffect, useState } from "react"
import { CheckCheck, Bell } from "lucide-react"
import { PageFrame } from "../components/PageFrame"
import { useApp } from "../context/AppContext"

export function NotificationsPage() {
  const { notifications, unreadCount, refreshNotifications, markRead, markAllRead } = useApp()
  const [filter, setFilter] = useState<"all" | "unread">("all")
  useEffect(() => { void refreshNotifications() }, [refreshNotifications])
  const shown = filter === "unread" ? notifications.filter((item) => !item.is_read) : notifications

  return (
	<PageFrame eyebrow="Workspace" title="Notifications" description={`${unreadCount} unread notification${unreadCount === 1 ? "" : "s"}`} actions={<><button type="button" className="sp-btn-secondary" onClick={() => setFilter("all")}>All</button><button type="button" className="sp-btn-secondary" onClick={() => setFilter("unread")}>Unread</button><button type="button" className="sp-btn-primary" onClick={() => void markAllRead()} disabled={unreadCount === 0}><CheckCheck size={15} /> Mark all read</button></>}>
	  {shown.length === 0 ? <div className="sp-card p-12 text-center"><Bell className="mx-auto text-[var(--text-muted)]" /><h2 className="text-base mt-3">No notifications</h2><p className="text-sm text-[var(--text-secondary)]">Workspace events and processing updates will appear here.</p></div> : <div className="space-y-2">{shown.map((item) => <button type="button" key={item.id} onClick={() => void markRead(item.id)} className={`sp-card w-full text-left p-4 flex items-start gap-3 ${item.is_read ? "opacity-75" : "border-[var(--accent-primary)]/50"}`}><span className={`mt-1 w-2 h-2 rounded-full shrink-0 ${item.is_read ? "bg-[var(--text-muted)]" : "bg-[var(--accent-primary)]"}`} /><div className="min-w-0 flex-1"><div className="flex justify-between gap-3"><h2 className="text-sm m-0">{item.title}</h2><time className="text-[10px] text-[var(--text-muted)] shrink-0">{new Date(item.created_at).toLocaleString()}</time></div><p className="text-xs text-[var(--text-secondary)] mt-1 mb-0">{item.message}</p></div></button>)}</div>}
	</PageFrame>
  )
}
