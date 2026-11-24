import { useEffect, useState, type ReactNode } from "react"
import { NavLink, useLocation } from "react-router-dom"
import {
  Activity, Bell, Bot, ChevronLeft, ChevronRight, Database, Gauge,
  Hash, HelpCircle, LayoutDashboard, Lightbulb, LineChart, Menu,
  Moon, PanelTop, Search, Settings, Share2, Sparkles, Sun,
  Upload, Users, X
} from "lucide-react"

const navigation = [
  { label: "Overview", path: "/", icon: LayoutDashboard },
  { label: "Command Center", path: "/command-center", icon: Gauge },
  { label: "Executive Dashboard", path: "/executive-dashboard", icon: PanelTop },
  { label: "Social Analytics", path: "/social-analytics", icon: Activity },
  { label: "Trending Topics", path: "/trending-topics", icon: LineChart },
  { label: "Emerging Trends", path: "/emerging-trends", icon: Sparkles },
  { label: "Hashtag Explorer", path: "/hashtags", icon: Hash },
  { label: "Keyword Intelligence", path: "/keywords", icon: Search },
  { label: "Topic Clustering", path: "/topic-clustering", icon: Share2 },
  { label: "Viral Content", path: "/viral-content", icon: Lightbulb },
  { label: "Sentiment Analysis", path: "/sentiment", icon: Activity },
  { label: "Emotion Detection", path: "/emotion-detection", icon: Activity },
  { label: "Opinion Analysis", path: "/opinion-analysis", icon: Users },
  { label: "Engagement Analytics", path: "/engagement", icon: Gauge },
  { label: "Best Posting Time", path: "/posting-time", icon: Activity },
  { label: "Audience Insights", path: "/audience", icon: Users },
  { label: "Platform Comparison", path: "/platforms", icon: PanelTop },
  { label: "AI Insights", path: "/ai-insights", icon: Sparkles },
  { label: "AI Assistant", path: "/assistant", icon: Bot },
  { label: "Trend Prediction", path: "/prediction", icon: LineChart },
  { label: "Dataset Explorer", path: "/datasets", icon: Database },
  { label: "Data Upload", path: "/upload", icon: Upload },
  { label: "Data Cleaning", path: "/cleaning", icon: Database },
  { label: "Reports", path: "/reports", icon: PanelTop },
  { label: "Report Builder", path: "/report-builder", icon: PanelTop },
  { label: "Notifications", path: "/notifications", icon: Bell },
  { label: "User Profile", path: "/profile", icon: Users },
  { label: "Settings", path: "/settings", icon: Settings },
]

export function DashboardLayout({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [light, setLight] = useState(false)
  const [search, setSearch] = useState("")
  const location = useLocation()

  useEffect(() => setMobileOpen(false), [location.pathname])

  return (
    <div className={light ? "app-shell app-shell-light" : "app-shell"}>
      <aside className={`sidebar ${collapsed ? "sidebar-collapsed" : ""} ${mobileOpen ? "sidebar-mobile-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><Activity size={19} /></div>
          {!collapsed && <div><strong>SOCIALPULSE</strong><span> AI INTELLIGENCE</span></div>}
          <button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={18} /></button>
        </div>
        <nav className="sidebar-nav">
          {navigation.map((item) => (
            <NavLink key={item.path} to={item.path} end={item.path === "/"} className={({ isActive }) => `nav-item ${isActive ? "nav-active" : ""}`} title={collapsed ? item.label : undefined}>
              <item.icon size={18} />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>
        <button className="collapse-button" onClick={() => setCollapsed((value) => !value)}>
          {collapsed ? <ChevronRight size={17} /> : <><ChevronLeft size={17} /><span>Collapse sidebar</span></>}
        </button>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <button className="icon-button mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <label className="global-search">
            <Search size={17} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search topics, hashtags, posts..." />
            <kbd>⌘ K</kbd>
          </label>
          <div className="topbar-actions">
            <button className="icon-button" onClick={() => setLight((value) => !value)} aria-label="Toggle theme">
              {light ? <Moon size={18} /> : <Sun size={18} />}
            </button>
            <button className="icon-button notification-button" aria-label="Notifications"><Bell size={18} /><span>3</span></button>
            <button className="icon-button" aria-label="Help"><HelpCircle size={18} /></button>
            <button className="profile-button"><span>MS</span><div><strong>Mir Shabaz</strong><small>Intern Analyst</small></div></button>
          </div>
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  )
}
