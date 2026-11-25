import { useEffect, useRef, useState, type ReactNode } from "react"
import { NavLink, useLocation, useNavigate } from "react-router-dom"
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  Bot,
  CheckCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  Compass,
  Database,
  FileSpreadsheet,
  FileText,
  Flame,
  Gauge,
  Hash,
  HeartPulse,
  HelpCircle,
  Home,
  Layers,
  LayoutDashboard,
  Lightbulb,
  LineChart,
  LogIn,
  LogOut,
  Menu,
  MessageSquareHeart,
  Moon,
  Network,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Sun,
  TrendingUp,
  Upload,
  User,
  Users,
  X,
} from "lucide-react"
import { useApp } from "../context/AppContext"
import { api } from "../services/api"
import { ConfirmModal } from "./ui/ConfirmModal"
import { PostDetailModal } from "./ui/PostDetailModal"
import { ToastContainer } from "./ui/StateBlocks"

interface NavItem {
  label: string
  path: string
  icon: typeof LayoutDashboard
  section: string
}

const NAVIGATION: NavItem[] = [
  { section: "Overview", label: "Overview", path: "/", icon: LayoutDashboard },
  { section: "Overview", label: "Command Center", path: "/command-center", icon: Gauge },
  { section: "Overview", label: "Executive Dashboard", path: "/executive-dashboard", icon: BarChart3 },
  { section: "Overview", label: "Social Analytics", path: "/social-analytics", icon: Activity },

  { section: "Trends & Topics", label: "Trending Topics", path: "/trending-topics", icon: TrendingUp },
  { section: "Trends & Topics", label: "Emerging Trends", path: "/emerging-trends", icon: Compass },
  { section: "Trends & Topics", label: "Hashtag Explorer", path: "/hashtags", icon: Hash },
  { section: "Trends & Topics", label: "Keyword Intelligence", path: "/keywords", icon: Search },
  { section: "Trends & Topics", label: "Topic Clustering", path: "/topic-clustering", icon: Network },
  { section: "Trends & Topics", label: "Trend Prediction", path: "/prediction", icon: LineChart },

  { section: "Sentiment & Engagement", label: "Sentiment Analysis", path: "/sentiment", icon: HeartPulse },
  { section: "Sentiment & Engagement", label: "Emotion Detection", path: "/emotion-detection", icon: MessageSquareHeart },
  { section: "Sentiment & Engagement", label: "Opinion Analysis", path: "/opinion-analysis", icon: Users },
  { section: "Sentiment & Engagement", label: "Engagement Analytics", path: "/engagement", icon: Flame },
  { section: "Sentiment & Engagement", label: "Viral Content", path: "/viral-content", icon: Layers },
  { section: "Sentiment & Engagement", label: "Best Posting Time", path: "/posting-time", icon: Clock },
  { section: "Sentiment & Engagement", label: "Anomaly Detection", path: "/anomalies", icon: AlertTriangle },
  { section: "Sentiment & Engagement", label: "Platform Comparison", path: "/platforms", icon: BarChart3 },
  { section: "Sentiment & Engagement", label: "Audience Insights", path: "/audience", icon: Users },

  { section: "AI Intelligence", label: "AI Insights", path: "/ai-insights", icon: Lightbulb },
  { section: "AI Intelligence", label: "AI Assistant", path: "/assistant", icon: Bot },

  { section: "Data & Reports", label: "Dataset Explorer", path: "/datasets", icon: Database },
  { section: "Data & Reports", label: "Data Upload", path: "/upload", icon: Upload },
  { section: "Data & Reports", label: "Data Cleaning", path: "/cleaning", icon: Sparkles },
  { section: "Data & Reports", label: "Reports", path: "/reports", icon: FileText },
  { section: "Data & Reports", label: "Report Builder", path: "/report-builder", icon: FileSpreadsheet },

  { section: "Workspace", label: "Notifications", path: "/notifications", icon: Bell },
  { section: "Workspace", label: "User Profile", path: "/profile", icon: User },
  { section: "Workspace", label: "Settings", path: "/settings", icon: Settings },
  { section: "Workspace", label: "Security", path: "/security", icon: ShieldCheck },
]

const SECTIONS = Array.from(new Set(NAVIGATION.map((item) => item.section)))

export function DashboardLayout({ children }: { children: ReactNode }) {
  const {
    theme,
    toggleTheme,
    user,
    logout,
    datasets,
    activeDataset,
    activateDatasetById,
    notifications,
    unreadCount,
    markRead,
    markAllRead,
    openPostDetail,
    pushToast,
  } = useApp()

  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchResults, setSearchResults] = useState<Record<string, any[]> | null>(null)
  const [notifOpen, setNotifOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const [datasetSwitching, setDatasetSwitching] = useState(false)

  const searchInputRef = useRef<HTMLInputElement | null>(null)
  const searchBoxRef = useRef<HTMLDivElement | null>(null)
  const notifRef = useRef<HTMLDivElement | null>(null)
  const profileRef = useRef<HTMLDivElement | null>(null)

  const location = useLocation()
  const navigate = useNavigate()

  // Keyboard shortcut Cmd/Ctrl + K for Global Search
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        searchInputRef.current?.focus()
        setSearchOpen(true)
      } else if (e.key === "Escape") {
        setSearchOpen(false)
        setNotifOpen(false)
        setProfileOpen(false)
        setHelpOpen(false)
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [])

  // Close popovers on outside click
  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      const target = e.target as Node
      if (searchBoxRef.current && !searchBoxRef.current.contains(target)) {
        setSearchOpen(false)
      }
      if (notifRef.current && !notifRef.current.contains(target)) {
        setNotifOpen(false)
      }
      if (profileRef.current && !profileRef.current.contains(target)) {
        setProfileOpen(false)
      }
    }
    document.addEventListener("mousedown", handleOutside)
    return () => document.removeEventListener("mousedown", handleOutside)
  }, [])

  // Debounced live global search
  useEffect(() => {
    if (!searchOpen) return
    const timer = window.setTimeout(() => {
      api
        .search(searchQuery, activeDataset?.id)
        .then((res) => setSearchResults(res.results))
        .catch(() => setSearchResults(null))
    }, 180)
    return () => window.clearTimeout(timer)
  }, [searchQuery, searchOpen, activeDataset?.id])

  const currentNav =
    NAVIGATION.find((item) => item.path === location.pathname) ?? {
      section: "Workspace",
      label: location.pathname.replace("/", "").replace(/-/g, " ") || "Overview",
      path: location.pathname,
      icon: LayoutDashboard,
    }

  const initials = user?.full_name
    ? user.full_name
        .split(/\s+/)
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "SP"

  async function handleDatasetSwitch(id: number) {
    if (!id || id === activeDataset?.id) return
    setDatasetSwitching(true)
    try {
      await activateDatasetById(id)
    } catch (err) {
      pushToast({
        title: "Switch failed",
        message: err instanceof Error ? err.message : "Could not switch dataset.",
        variant: "error",
      })
    } finally {
      setDatasetSwitching(false)
    }
  }

  return (
    <div className={`sp-shell ${collapsed ? "is-collapsed" : ""}`}>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside className={`sp-sidebar ${mobileOpen ? "is-mobile-open" : ""}`}>
        <div className="h-[68px] flex items-center justify-between px-4 border-b border-[var(--border-subtle)] shrink-0">
          <button
            type="button"
            onClick={() => {
              navigate("/")
              setMobileOpen(false)
            }}
            className="flex items-center gap-2.5 bg-transparent border-0 p-0 text-left min-w-0"
          >
            <div className="w-9 h-9 rounded-xl grid place-items-center text-white bg-gradient-to-br from-[#7C5CFC] to-[#00D4FF] shadow-lg shadow-[#7C5CFC]/25 shrink-0">
              <Activity size={19} />
            </div>
            {!collapsed && (
              <div className="min-w-0">
                <div className="text-[13px] font-extrabold tracking-wider text-[var(--text-primary)] truncate">
                  SOCIALPULSE
                </div>
                <div className="text-[9px] font-semibold tracking-[0.18em] text-[var(--text-muted)]">
                  AI INTELLIGENCE
                </div>
              </div>
            )}
          </button>

          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
            className="lg:hidden text-[var(--text-secondary)] bg-transparent border-0 p-1"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-2.5 py-3 space-y-4">
          {SECTIONS.map((section) => (
            <div key={section}>
              {!collapsed && (
                <div className="px-2.5 mb-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--text-muted)]">
                  {section}
                </div>
              )}
              <div className="space-y-0.5">
                {NAVIGATION.filter((item) => item.section === section).map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === "/"}
                    onClick={() => setMobileOpen(false)}
                    title={collapsed ? item.label : undefined}
                    className={({ isActive }) =>
                      `flex items-center gap-2.5 h-9 px-2.5 rounded-lg text-[12.5px] font-medium no-underline transition-colors ${
                        isActive
                          ? "bg-[var(--accent-soft)] text-[var(--accent-primary)] font-semibold shadow-[inset_2px_0_0_var(--accent-primary)]"
                          : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]"
                      }`
                    }
                  >
                    <item.icon size={16} className="shrink-0" />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <button
          type="button"
          onClick={() => setCollapsed((prev) => !prev)}
          className="hidden lg:flex items-center gap-2 h-11 px-4 border-0 border-t border-[var(--border-subtle)] bg-transparent text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] shrink-0"
        >
          {collapsed ? (
            <ChevronRight size={16} className="mx-auto" />
          ) : (
            <>
              <ChevronLeft size={16} />
              <span>Collapse sidebar</span>
            </>
          )}
        </button>
      </aside>

      <div className="sp-workspace">
        <header className="sp-topbar">
          <div className="flex items-center gap-2.5 flex-1 min-w-0">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
              className="lg:hidden sp-btn-secondary !h-9 !w-9 !p-0 shrink-0"
            >
              <Menu size={18} />
            </button>

            {/* Global Search */}
            <div ref={searchBoxRef} className="relative flex-1 max-w-md">
              <div className="flex items-center gap-2 h-9 px-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-input)] focus-within:border-[var(--accent-primary)]">
                <Search size={15} className="text-[var(--text-muted)] shrink-0" />
                <input
                  ref={searchInputRef}
                  value={searchQuery}
                  onFocus={() => setSearchOpen(true)}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    setSearchOpen(true)
                  }}
                  placeholder="Search topics, hashtags, posts, modules..."
                  className="flex-1 min-w-0 bg-transparent border-0 outline-none text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
                />
                {searchQuery ? (
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    aria-label="Clear search"
                    className="bg-transparent border-0 p-0 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                  >
                    <X size={13} />
                  </button>
                ) : (
                  <kbd className="hidden sm:inline-block text-[10px] px-1.5 py-0.5 rounded border border-[var(--border-subtle)] text-[var(--text-muted)]">
                    ⌘K
                  </kbd>
                )}
              </div>

              {searchOpen && searchResults && (
                <div className="sp-card absolute left-0 right-0 top-11 z-50 p-3 max-h-[70vh] overflow-y-auto shadow-2xl space-y-3">
                  {searchResults.modules?.length > 0 && (
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)] px-2 mb-1">
                        Modules
                      </div>
                      {searchResults.modules.map((m) => (
                        <button
                          key={m.path}
                          type="button"
                          onClick={() => {
                            navigate(m.path)
                            setSearchOpen(false)
                          }}
                          className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs hover:bg-[var(--bg-elevated)] bg-transparent border-0 flex items-center justify-between text-[var(--text-primary)]"
                        >
                          <span>{m.label}</span>
                          <span className="text-[10px] text-[var(--text-muted)]">{m.category}</span>
                        </button>
                      ))}
                    </div>
                  )}

                  {searchResults.topics?.length > 0 && (
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)] px-2 mb-1">
                        Topics
                      </div>
                      {searchResults.topics.map((t) => (
                        <button
                          key={t.name}
                          type="button"
                          onClick={() => {
                            navigate(`/trending-topics?topic=${encodeURIComponent(t.name)}`)
                            setSearchOpen(false)
                          }}
                          className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs hover:bg-[var(--bg-elevated)] bg-transparent border-0 flex items-center justify-between text-[var(--text-primary)]"
                        >
                          <span>{t.name}</span>
                          <span className="text-[10px] text-[var(--text-secondary)]">
                            {t.posts} posts
                          </span>
                        </button>
                      ))}
                    </div>
                  )}

                  {searchResults.hashtags?.length > 0 && (
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)] px-2 mb-1">
                        Hashtags
                      </div>
                      <div className="flex flex-wrap gap-1.5 px-2">
                        {searchResults.hashtags.map((h) => (
                          <button
                            key={h.name}
                            type="button"
                            onClick={() => {
                              navigate(`/hashtags?tag=${encodeURIComponent(h.name)}`)
                              setSearchOpen(false)
                            }}
                            className="rounded-full bg-[var(--accent-soft)] text-[var(--accent-primary)] px-2.5 py-1 text-xs font-medium border-0"
                          >
                            {h.name} ({h.count})
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {searchResults.datasets?.length > 0 && (
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)] px-2 mb-1">
                        Datasets
                      </div>
                      {searchResults.datasets.map((d) => (
                        <button
                          key={d.id}
                          type="button"
                          onClick={() => {
                            navigate("/datasets")
                            setSearchOpen(false)
                          }}
                          className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs hover:bg-[var(--bg-elevated)] bg-transparent border-0 flex items-center justify-between text-[var(--text-primary)]"
                        >
                          <span>{d.name}</span>
                          <span className="text-[10px] text-[var(--text-secondary)]">
                            {d.cleaned_row_count} rows {d.is_active ? "• Active" : ""}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}

                  {searchResults.posts?.length > 0 && (
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)] px-2 mb-1">
                        Matching Posts
                      </div>
                      {searchResults.posts.map((p) => (
                        <button
                          key={p.post_id}
                          type="button"
                          onClick={() => {
                            openPostDetail(p.post_id)
                            setSearchOpen(false)
                          }}
                          className="w-full text-left px-2.5 py-2 rounded-lg text-xs hover:bg-[var(--bg-elevated)] bg-transparent border-0 block text-[var(--text-primary)]"
                        >
                          <div className="flex items-center justify-between text-[11px] font-semibold">
                            <span>
                              {p.post_id} • {p.platform}
                            </span>
                            <span className="text-[var(--accent-secondary)]">
                              {p.engagement.toLocaleString()} eng
                            </span>
                          </div>
                          <div className="text-[11px] text-[var(--text-secondary)] truncate mt-0.5">
                            {p.content}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}

                  {!searchResults.modules?.length &&
                    !searchResults.topics?.length &&
                    !searchResults.hashtags?.length &&
                    !searchResults.posts?.length &&
                    !searchResults.datasets?.length && (
                      <p className="text-xs text-[var(--text-secondary)] text-center py-3 m-0">
                        No matches found for &ldquo;{searchQuery}&rdquo;.
                      </p>
                    )}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* Active Dataset Switcher */}
            {datasets.length > 0 && (
              <div className="hidden xl:flex items-center gap-1.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2.5 h-9">
                <Database size={14} className="text-[var(--accent-secondary)] shrink-0" />
                <select
                  aria-label="Active dataset"
                  value={activeDataset?.id ?? ""}
                  disabled={datasetSwitching}
                  onChange={(e) => handleDatasetSwitch(Number(e.target.value))}
                  className="bg-transparent border-0 outline-none text-xs font-medium text-[var(--text-primary)] max-w-[190px] cursor-pointer"
                >
                  {datasets.map((ds) => (
                    <option key={ds.id} value={ds.id} className="bg-[var(--bg-secondary)] text-[var(--text-primary)]">
                      {ds.name} ({ds.cleaned_row_count})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Theme toggle */}
            <button
              type="button"
              onClick={toggleTheme}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
              aria-label="Toggle theme"
              className="sp-btn-secondary !h-9 !w-9 !p-0"
            >
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>

            {/* Notification Center */}
            <div ref={notifRef} className="relative">
              <button
                type="button"
                onClick={() => setNotifOpen((v) => !v)}
                aria-label="Notifications"
                className="sp-btn-secondary !h-9 !w-9 !p-0 relative"
              >
                <Bell size={16} />
                {unreadCount > 0 && (
                  <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 rounded-full bg-rose-500 text-white text-[10px] font-bold grid place-items-center">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </button>

              {notifOpen && (
                <div className="sp-card absolute right-0 top-11 z-50 w-80 sm:w-96 p-4 shadow-2xl">
                  <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-2.5">
                    <span className="text-xs font-bold text-[var(--text-primary)]">
                      Notifications ({unreadCount} unread)
                    </span>
                    <div className="flex items-center gap-2">
                      {unreadCount > 0 && (
                        <button
                          type="button"
                          onClick={() => markAllRead()}
                          className="text-[11px] font-medium text-[var(--accent-primary)] bg-transparent border-0 flex items-center gap-1"
                        >
                          <CheckCheck size={12} /> Mark all read
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => {
                          navigate("/notifications")
                          setNotifOpen(false)
                        }}
                        className="text-[11px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-transparent border-0"
                      >
                        View all
                      </button>
                    </div>
                  </div>
                  <div className="mt-2.5 max-h-72 overflow-y-auto space-y-2">
                    {notifications.length === 0 ? (
                      <p className="text-xs text-[var(--text-secondary)] text-center py-6 m-0">
                        No system events recorded yet.
                      </p>
                    ) : (
                      notifications.slice(0, 8).map((n) => (
                        <button
                          key={n.id}
                          type="button"
                          onClick={() => markRead(n.id)}
                          className={`w-full text-left p-2.5 rounded-xl border transition-colors bg-transparent ${
                            n.is_read
                              ? "border-[var(--border-subtle)] opacity-75"
                              : "border-[var(--accent-primary)]/40 bg-[var(--accent-soft)]"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-semibold text-[var(--text-primary)]">
                              {n.title}
                            </span>
                            <span className="text-[10px] uppercase text-[var(--text-muted)]">
                              {n.category}
                            </span>
                          </div>
                          <p className="text-[11px] text-[var(--text-secondary)] mt-1 mb-0">
                            {n.message}
                          </p>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Help modal button */}
            <button
              type="button"
              onClick={() => setHelpOpen(true)}
              aria-label="Platform Guide"
              title="Platform Guide"
              className="hidden sm:inline-flex sp-btn-secondary !h-9 !w-9 !p-0"
            >
              <HelpCircle size={16} />
            </button>

            {/* User Profile Dropdown */}
            <div ref={profileRef} className="relative">
              <button
                type="button"
                onClick={() => setProfileOpen((v) => !v)}
                className="flex items-center gap-2 h-9 px-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-left"
              >
                <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#7C5CFC] to-[#00D4FF] text-white text-[11px] font-bold grid place-items-center shrink-0">
                  {initials}
                </span>
                <div className="hidden md:block leading-tight pr-1">
                  <div className="text-xs font-semibold text-[var(--text-primary)] max-w-[115px] truncate">
                    {user ? user.full_name : "Demo Workspace"}
                  </div>
                  <div className="text-[10px] text-[var(--text-muted)] max-w-[115px] truncate">
                    {user ? user.role : "Sign in / Register"}
                  </div>
                </div>
                <ChevronDown size={13} className="text-[var(--text-muted)] hidden md:block" />
              </button>

              {profileOpen && (
                <div className="sp-card absolute right-0 top-11 z-50 w-56 p-2 shadow-2xl space-y-1">
                  <div className="px-2.5 py-2 border-b border-[var(--border-subtle)]">
                    <div className="text-xs font-semibold text-[var(--text-primary)]">
                      {user ? user.full_name : "Public Demo Mode"}
                    </div>
                    <div className="text-[11px] text-[var(--text-secondary)] truncate">
                      {user ? user.email : "Sign in to own private datasets"}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      navigate("/profile")
                      setProfileOpen(false)
                    }}
                    className="w-full text-left px-2.5 py-2 rounded-lg text-xs text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] bg-transparent border-0 flex items-center gap-2"
                  >
                    <User size={14} /> {user ? "Profile & Security" : "Sign In / Profile"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      navigate("/datasets")
                      setProfileOpen(false)
                    }}
                    className="w-full text-left px-2.5 py-2 rounded-lg text-xs text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] bg-transparent border-0 flex items-center gap-2"
                  >
                    <Database size={14} /> Manage Datasets
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      navigate("/settings")
                      setProfileOpen(false)
                    }}
                    className="w-full text-left px-2.5 py-2 rounded-lg text-xs text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] bg-transparent border-0 flex items-center gap-2"
                  >
                    <Settings size={14} /> Workspace Settings
                  </button>
                  {user ? (
                    <button
                      type="button"
                      onClick={() => {
                        logout()
                        setProfileOpen(false)
                      }}
                      className="w-full text-left px-2.5 py-2 rounded-lg text-xs text-rose-400 hover:bg-rose-500/10 bg-transparent border-0 flex items-center gap-2"
                    >
                      <LogOut size={14} /> Sign Out
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => {
                        navigate("/login")
                        setProfileOpen(false)
                      }}
                      className="w-full text-left px-2.5 py-2 rounded-lg text-xs text-[var(--accent-primary)] hover:bg-[var(--accent-soft)] bg-transparent border-0 flex items-center gap-2 font-semibold"
                    >
                      <LogIn size={14} /> Sign In / Register
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Breadcrumb & Active Dataset Context Bar */}
        <div className="px-4 sm:px-7 py-2.5 border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)]/55 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 text-[var(--text-secondary)]">
            <button
              type="button"
              onClick={() => navigate("/")}
              className="inline-flex items-center gap-1 hover:text-[var(--text-primary)] bg-transparent border-0 p-0 text-[var(--text-secondary)]"
            >
              <Home size={12} /> Workspace
            </button>
            <span>/</span>
            <span>{currentNav.section}</span>
            <span>/</span>
            <span className="font-semibold text-[var(--text-primary)] capitalize">
              {currentNav.label}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {activeDataset && (
              <button
                type="button"
                onClick={() => navigate("/datasets")}
                className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-card)] px-2.5 py-0.5 text-[11px] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Active CSV: <strong className="text-[var(--text-primary)]">{activeDataset.name}</strong>
                <span>({activeDataset.cleaned_row_count.toLocaleString()} posts)</span>
              </button>
            )}
            <span className="hidden sm:inline-flex items-center gap-1 text-[11px] text-[var(--text-muted)]">
              <ShieldCheck size={12} className="text-[var(--accent-secondary)]" /> CSV Historical Analytics
            </span>
          </div>
        </div>

        <main className="flex-1 min-w-0">{children}</main>
      </div>

      {/* Help Modal */}
      {helpOpen && (
        <div
          className="fixed inset-0 z-[70] bg-black/65 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setHelpOpen(false)}
        >
          <div className="sp-card w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
              <h2 className="text-base font-bold m-0">SOCIALPULSE AI — Quick Guide</h2>
              <button
                type="button"
                onClick={() => setHelpOpen(false)}
                aria-label="Close guide"
                className="sp-btn-secondary !h-8 !w-8 !p-0"
              >
                <X size={15} />
              </button>
            </div>
            <div className="space-y-3 text-xs text-[var(--text-secondary)] leading-relaxed">
              <p className="m-0">
                <strong className="text-[var(--text-primary)]">CSV-Driven Intelligence:</strong> Every KPI, chart,
                ML topic cluster, anomaly flag, and assistant answer is computed directly from the active dataset
                in your workspace—no fabricated live feeds or invented follower counts.
              </p>
              <p className="m-0">
                <strong className="text-[var(--text-primary)]">Interactive Navigation:</strong> Press{" "}
                <kbd className="px-1.5 py-0.5 rounded border border-[var(--border-subtle)]">Ctrl/Cmd + K</kbd> to
                search topics, hashtags, posts, and modules. Click KPI cards or chart items to drill down.
              </p>
              <p className="m-0">
                <strong className="text-[var(--text-primary)]">Dataset Switching & Column Mapping:</strong> Upload any
                social media CSV in Dataset Explorer, map non-standard column names, and switch active datasets anytime.
              </p>
            </div>
            <div className="flex justify-end">
              <button type="button" onClick={() => setHelpOpen(false)} className="sp-btn-primary">
                Got it
              </button>
            </div>
          </div>
        </div>
      )}

      <PostDetailModal />
      <ConfirmModal />
      <ToastContainer />
    </div>
  )
}
