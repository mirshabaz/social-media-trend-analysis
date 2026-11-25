import { lazy, Suspense } from "react"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { DashboardLayout } from "./components/DashboardLayout"
import { PageFrame } from "./components/PageFrame"
import { useApp } from "./context/AppContext"

const OverviewPage = lazy(() => import("./pages/OverviewPage").then((m) => ({ default: m.OverviewPage })))
const TrendsPage = lazy(() => import("./pages/TrendsPage").then((m) => ({ default: m.TrendsPage })))
const SentimentPage = lazy(() => import("./pages/SentimentPage").then((m) => ({ default: m.SentimentPage })))
const EngagementPage = lazy(() => import("./pages/EngagementPage").then((m) => ({ default: m.EngagementPage })))
const HashtagsPage = lazy(() => import("./pages/HashtagsPage").then((m) => ({ default: m.HashtagsPage })))
const PlatformsPage = lazy(() => import("./pages/PlatformsPage").then((m) => ({ default: m.PlatformsPage })))
const AdvancedAnalyticsPage = lazy(() => import("./pages/AdvancedAnalyticsPage").then((m) => ({ default: m.AdvancedAnalyticsPage })))
const DatasetManagementPage = lazy(() => import("./pages/DatasetManagementPage").then((m) => ({ default: m.DatasetManagementPage })))
const AssistantPage = lazy(() => import("./pages/AssistantPage").then((m) => ({ default: m.AssistantPage })))
const ReportsPage = lazy(() => import("./pages/ReportsPage").then((m) => ({ default: m.ReportsPage })))
const NotificationsPage = lazy(() => import("./pages/NotificationsPage").then((m) => ({ default: m.NotificationsPage })))
const LoginPage = lazy(() => import("./pages/AuthPages").then((m) => ({ default: m.LoginPage })))
const RegisterPage = lazy(() => import("./pages/AuthPages").then((m) => ({ default: m.RegisterPage })))
const AccountSettingsPage = lazy(() => import("./pages/ProfileSettingsPages").then((m) => ({ default: m.AccountSettingsPage })))
const ProfilePage = lazy(() => import("./pages/ProfileSettingsPages").then((m) => ({ default: m.ProfilePage })))
const SecuritySettingsPage = lazy(() => import("./pages/ProfileSettingsPages").then((m) => ({ default: m.SecuritySettingsPage })))

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, authLoading } = useApp()
  if (authLoading) return <div className="sp-card p-8 m-6 text-sm text-[var(--text-secondary)]">Checking session...</div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="min-h-screen grid place-items-center bg-[var(--bg-primary)] text-sm text-[var(--text-secondary)]">Loading SOCIALPULSE AI...</div>}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="*" element={<DashboardLayout><Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/command-center" element={<OverviewPage mode="command" />} />
          <Route path="/executive-dashboard" element={<OverviewPage mode="executive" />} />
          <Route path="/social-analytics" element={<OverviewPage mode="social" />} />
          <Route path="/trending-topics" element={<TrendsPage defaultTab="topics" />} />
          <Route path="/emerging-trends" element={<TrendsPage defaultTab="emerging" />} />
          <Route path="/prediction" element={<TrendsPage defaultTab="prediction" />} />
          <Route path="/hashtags" element={<HashtagsPage />} />
          <Route path="/keywords" element={<TrendsPage defaultTab="keywords" />} />
          <Route path="/topic-clustering" element={<AdvancedAnalyticsPage defaultTab="clusters" />} />
          <Route path="/sentiment" element={<SentimentPage />} />
          <Route path="/emotion-detection" element={<SentimentPage mode="emotion" />} />
          <Route path="/opinion-analysis" element={<SentimentPage mode="opinion" />} />
          <Route path="/engagement" element={<EngagementPage />} />
          <Route path="/viral-content" element={<EngagementPage mode="viral" />} />
          <Route path="/posting-time" element={<AdvancedAnalyticsPage defaultTab="time" />} />
          <Route path="/anomalies" element={<AdvancedAnalyticsPage defaultTab="anomalies" />} />
          <Route path="/platforms" element={<PlatformsPage />} />
          <Route path="/audience" element={<PlatformsPage mode="audience" />} />
          <Route path="/ai-insights" element={<OverviewPage mode="executive" />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/datasets" element={<DatasetManagementPage />} />
          <Route path="/upload" element={<DatasetManagementPage />} />
          <Route path="/cleaning" element={<DatasetManagementPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/report-builder" element={<ReportsPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/profile" element={<RequireAuth><ProfilePage /></RequireAuth>} />
          <Route path="/settings" element={<AccountSettingsPage />} />
          <Route path="/security" element={<RequireAuth><SecuritySettingsPage /></RequireAuth>} />
          <Route path="*" element={<PageFrame eyebrow="404" title="Page not found" description="The requested route does not exist."><div className="sp-card p-8 text-sm text-[var(--text-secondary)]">Choose a destination from the sidebar.</div></PageFrame>} />
        </Routes></DashboardLayout>} />
      </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
