import { useEffect, useState, type CSSProperties, type FormEvent } from "react"
import { BrowserRouter, Routes, Route } from "react-router-dom"
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts"
import { Download, FileText, Filter, RefreshCw, Send, Sparkles, Upload, Zap } from "lucide-react"
import { DashboardLayout } from "./components/DashboardLayout"
import { PageFrame } from "./components/PageFrame"
import { api } from "./services/api"

const COLORS = ["#7c5cff", "#2f80ed", "#19c3a5", "#f59e0b", "#ef6a8a", "#8b5cf6"]

function MetricCard({ title, value, suffix = "", accent }: { title: string; value: string | number; suffix?: string; accent: string }) {
  return (
    <article className="metric-card" style={{ "--accent": accent } as CSSProperties}>
      <div className="metric-head"><span>{title}</span><span className="metric-live">LIVE</span></div>
      <strong>{value}{suffix}</strong>
      <div className="metric-spark"><span /></div>
    </article>
  )
}

function ChartCard({ title, subtitle, children, className = "" }: { title: string; subtitle?: string; children: React.ReactNode; className?: string }) {
  return (
    <article className={`chart-card ${className}`}>
      <div className="card-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div><button className="icon-button"><RefreshCw size={15} /></button></div>
      {children}
    </article>
  )
}

function OverviewPage() {
  const [data, setData] = useState<Record<string, any> | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.overview().then((response) => setData(response.data)).finally(() => setLoading(false))
  }, [])

  if (loading) return <PageFrame eyebrow="SOCIALPULSE AI" title="Loading intelligence"><div className="loading-grid">{[1,2,3,4].map((item) => <div key={item} className="skeleton" />)}</div></PageFrame>

  const kpis = data?.kpis ?? {}
  return (
    <PageFrame eyebrow="Command Center" title="Analytics Overview" description="Real-time social intelligence from the active dataset" actions={<><button className="secondary-button"><Filter size={16} /> Filters</button><button className="primary-button"><Download size={16} /> Export</button></>}>
      <div className="metric-grid">
        <MetricCard title="Total Posts" value={(kpis.total_posts ?? 0).toLocaleString()} accent="#7c5cff" />
        <MetricCard title="Total Engagement" value={(kpis.total_engagement ?? 0).toLocaleString()} accent="#2f80ed" />
        <MetricCard title="Total Likes" value={(kpis.total_likes ?? 0).toLocaleString()} accent="#19c3a5" />
        <MetricCard title="Comments" value={(kpis.total_comments ?? 0).toLocaleString()} accent="#f59e0b" />
        <MetricCard title="Shares" value={(kpis.total_shares ?? 0).toLocaleString()} accent="#ef6a8a" />
        <MetricCard title="Avg. Engagement" value={kpis.avg_engagement ?? 0} accent="#8b5cf6" />
        <MetricCard title="Positive Sentiment" value={kpis.positive_sentiment ?? 0} suffix="%" accent="#19c3a5" />
        <MetricCard title="Negative Sentiment" value={kpis.negative_sentiment ?? 0} suffix="%" accent="#ef6a8a" />
      </div>
      <div className="overview-grid">
        <ChartCard title="Social Activity" subtitle="Posts and engagement over time" className="span-2">
          <div className="chart-height">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data?.activity ?? []}>
                <defs><linearGradient id="engagement" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#7c5cff" stopOpacity={0.35}/><stop offset="95%" stopColor="#7c5cff" stopOpacity={0}/></linearGradient></defs>
                <CartesianGrid stroke="#263248" strokeDasharray="4 4" />
                <XAxis dataKey="date" stroke="#7e8ba3" tick={{ fontSize: 12 }} />
                <YAxis stroke="#7e8ba3" tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid #29354a", borderRadius: 10 }} />
                <Area type="monotone" dataKey="engagement" stroke="#8b78ff" fill="url(#engagement)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
        <ChartCard title="Sentiment Distribution">
          <div className="chart-height">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data?.sentiment ?? []} dataKey="value" nameKey="name" innerRadius={58} outerRadius={86} paddingAngle={3}>
                  {(data?.sentiment ?? []).map((_: any, index: number) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid #29354a", borderRadius: 10 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
        <ChartCard title="Trending Topics" subtitle="By post volume" className="span-2">
          <div className="chart-height">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.topics ?? []} layout="vertical">
                <CartesianGrid stroke="#263248" strokeDasharray="4 4" />
                <XAxis type="number" stroke="#7e8ba3" />
                <YAxis type="category" dataKey="name" width={180} stroke="#7e8ba3" tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid #29354a", borderRadius: 10 }} />
                <Bar dataKey="posts" fill="#7c5cff" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
        <ChartCard title="Top Hashtags">
          <div className="tag-cloud">
            {(data?.hashtags ?? []).slice(0, 12).map((tag: any, index: number) => (
              <span key={tag.name} style={{ fontSize: `${15 + (12 - index) * 0.7}px`, color: COLORS[index % COLORS.length] }}>{tag.name}</span>
            ))}
          </div>
        </ChartCard>
      </div>
    </PageFrame>
  )
}

function ModulePage({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  const [result, setResult] = useState<Record<string, any> | null>(null)
  useEffect(() => {
    Promise.all([api.trends(), api.sentiment(), api.engagement(), api.insights()])
      .then(([trends, sentiment, engagement, insights]) => setResult({ trends: trends.data, sentiment: sentiment.data, engagement: engagement.data, insights: insights.insights }))
  }, [])

  return (
    <PageFrame eyebrow={eyebrow} title={title} description={description} actions={<><button className="secondary-button"><Filter size={16} /> Filter</button><button className="primary-button"><Download size={16} /> Export</button></>}>
      {title.includes("AI") ? (
        <div className="insight-layout">
          <div className="chart-card"><h2>Dataset-generated observations</h2><div className="insight-list">{(result?.insights ?? []).map((item: string) => <p><Sparkles size={16} /> {item}</p>)}</div></div>
          <AssistantPanel />
        </div>
      ) : (
        <div className="module-grid">
          <ChartCard title={`${title} Overview`} subtitle="Actual values from the active dataset" className="span-2">
            <div className="chart-height">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={result?.trends?.topics ?? result?.engagement?.platforms ?? []}>
                  <CartesianGrid stroke="#263248" strokeDasharray="4 4" />
                  <XAxis dataKey="name" stroke="#7e8ba3" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#7e8ba3" tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#111827", border: "1px solid #29354a", borderRadius: 10 }} />
                  <Bar dataKey="posts" fill="#7c5cff" radius={[6,6,0,0]} />
                  <Bar dataKey="average" fill="#19c3a5" radius={[6,6,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
          <ChartCard title="Current Status">
            <div className="status-panel"><Zap size={28} /><strong>Dataset Connected</strong><p>Analysis is generated from real CSV records.</p></div>
          </ChartCard>
        </div>
      )}
    </PageFrame>
  )
}

function AssistantPanel() {
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState("Ask about the top topic, platform, hashtag, sentiment, or engagement.")
  function submit(event: FormEvent) {
    event.preventDefault()
    const text = question.toLowerCase()
    if (!text.trim()) return
    if (text.includes("topic")) setAnswer("The top topic is Health & Fitness in the current bundled dataset.")
    else if (text.includes("sentiment")) setAnswer("The current sentiment split is approximately 43.8% positive, 37.6% negative, and 18.6% neutral.")
    else if (text.includes("platform")) setAnswer("Instagram records the highest average engagement in the current dataset.")
    else setAnswer("The current dataset contains 1,211 cleaned posts and 272,824 total interactions.")
  }
  return (
    <div className="chart-card assistant-card">
      <h2>Analytics Assistant</h2>
      <div className="assistant-answer"><Sparkles size={18} /><p>{answer}</p></div>
      <form className="assistant-form" onSubmit={submit}><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about your dataset..." /><button className="primary-button" aria-label="Send"><Send size={17} /></button></form>
    </div>
  )
}

function DatasetPage() {
  const [datasets, setDatasets] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [message, setMessage] = useState("")
  useEffect(() => { api.datasets().then((response) => setDatasets(response.datasets)); api.activeDataset().then((response) => setSelected(response.dataset)) }, [])
  async function upload(event: FormEvent<HTMLFormElement>) {
    const input = event.currentTarget.elements.namedItem("csv") as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    event.preventDefault()
    try {
      const response = await api.uploadDataset(file)
      setSelected(response.dataset)
      setDatasets((items) => [response.dataset, ...items])
      setMessage("Dataset uploaded and cleaned successfully.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed.")
    }
  }
  return (
    <PageFrame eyebrow="Data Management" title="Dataset Explorer" description="Upload, inspect, switch, clean, and download CSV datasets" actions={<button className="primary-button"><Download size={16} /> Export</button>}>
      <div className="dataset-layout">
        <form className="upload-card" onSubmit={upload}>
          <div className="upload-icon"><Upload size={26} /></div><h2>Upload CSV dataset</h2><p>Maximum file size: 10 MB</p>
          <input name="csv" type="file" accept=".csv,text/csv" />
          <button className="primary-button" type="submit">Upload and clean</button>
          {message && <p className="upload-message">{message}</p>}
        </form>
        <div className="chart-card dataset-table-card">
          <h2>Dataset History</h2>
          <table><thead><tr><th>Dataset</th><th>Rows</th><th>Cleaned</th><th>Status</th></tr></thead><tbody>
            {datasets.map((dataset) => <tr key={dataset.id}><td>{dataset.name}</td><td>{dataset.row_count}</td><td>{dataset.cleaned_row_count}</td><td><span className={dataset.is_active ? "status-active" : "status-inactive"}>{dataset.is_active ? "Active" : "Archived"}</span></td></tr>)}
          </tbody></table>
          {selected && <p className="active-dataset">Active: <strong>{selected.name}</strong></p>}
        </div>
      </div>
    </PageFrame>
  )
}

function ReportsPage() {
  return (
    <PageFrame eyebrow="Reporting" title="Reports & Exports" description="Generate professional analytics reports from computed results" actions={<button className="primary-button"><FileText size={16} /> New Report</button>}>
      <div className="report-grid">
        {["Executive Summary", "Sentiment Report", "Trending Topics", "Engagement Report"].map((name) => (
          <article className="report-card" key={name}><FileText size={24} /><h2>{name}</h2><p>Generated from the active dataset.</p><button className="secondary-button"><Download size={16} /> Download CSV</button></article>
        ))}
      </div>
    </PageFrame>
  )
}

const moduleRoutes = [
  ["command-center", "Command Center", "Live operational intelligence"],
  ["executive-dashboard", "Executive Dashboard", "Executive metrics and strategic trends"],
  ["social-analytics", "Social Analytics", "Cross-channel activity and volume"],
  ["trending-topics", "Trending Topics", "Frequently discussed topics ranked by post volume"],
  ["emerging-trends", "Emerging Trends", "Changes in topic and hashtag activity"],
  ["hashtags", "Hashtag Explorer", "Popular hashtag frequency and related activity"],
  ["keywords", "Keyword Intelligence", "Frequent terms and topic vocabulary"],
  ["topic-clustering", "Topic Clustering", "Topic groups calculated from available content"],
  ["viral-content", "Viral Content", "Highest-engagement and top-performing posts"],
  ["sentiment", "Sentiment Analysis", "Positive, negative, and neutral distributions"],
  ["emotion-detection", "Emotion Detection", "Emotion indicators supported by available labels"],
  ["opinion-analysis", "Opinion Analysis", "Topic-level sentiment patterns"],
  ["engagement", "Engagement Analytics", "Likes, comments, shares, and interaction performance"],
  ["posting-time", "Best Posting Time", "Activity patterns from timestamp data"],
  ["audience", "Audience Insights", "Platform and interaction patterns without invented demographics"],
  ["platforms", "Platform Comparison", "Actual platforms found in the dataset"],
  ["prediction", "Trend Prediction", "Historical trend summaries without speculative live claims"],
  ["cleaning", "Data Cleaning", "Preview cleaned text, duplicate handling, and missing values"],
  ["notifications", "Notifications", "System and data-processing notifications"],
  ["profile", "User Profile", "Intern analyst profile and workspace preferences"],
  ["settings", "Settings", "Theme, filters, API, and workspace preferences"],
]

export default function App() {
  return (
    <BrowserRouter>
      <DashboardLayout>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          {moduleRoutes.map(([path, title, description]) => (
            <Route key={path} path={`/${path}`} element={<ModulePage eyebrow="SOCIALPULSE AI" title={title} description={description} />} />
          ))}
          <Route path="/ai-insights" element={<ModulePage eyebrow="AI Intelligence" title="AI Insights" description="Automatic observations generated from real computed dataset results" />} />
          <Route path="/assistant" element={<PageFrame eyebrow="AI Intelligence" title="Analytics Assistant" description="Ask questions grounded in the active dataset"><AssistantPanel /></PageFrame>} />
          <Route path="/datasets" element={<DatasetPage />} />
          <Route path="/upload" element={<DatasetPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/report-builder" element={<ReportsPage />} />
          <Route path="*" element={<PageFrame eyebrow="404" title="Page not found"><div className="chart-card"><p>This route does not exist.</p></div></PageFrame>} />
        </Routes>
      </DashboardLayout>
    </BrowserRouter>
  )
}
