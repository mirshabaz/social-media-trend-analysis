import { useCallback, useEffect, useState } from "react"
import { Download, FileJson, FileSpreadsheet, FileText, RefreshCw, Trash2 } from "lucide-react"
import { PageFrame } from "../components/PageFrame"
import { ChartCard, EmptyState, ErrorState, LoadingSkeleton } from "../components/ui/StateBlocks"
import { useApp } from "../context/AppContext"
import { api } from "../services/api"
import type { ReportItem } from "../types/api"

export function ReportsPage() {
  const { activeDataset, refreshNotifications, pushToast, requestConfirm } = useApp()
  const [reports, setReports] = useState<ReportItem[]>([])
  const [format, setFormat] = useState("pdf")
  const [reportType, setReportType] = useState("overall")
  const [title, setTitle] = useState("")
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState("")

  const load = useCallback(async () => {
	setLoading(true); setError("")
	try { const res = await api.reports(); setReports(res.reports) } catch (err) { setError(err instanceof Error ? err.message : "Failed to load reports") }
	finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  async function generate() {
	setGenerating(true); setError("")
	try {
	  const res = await api.generateReport({ report_type: reportType, format, dataset_id: activeDataset?.id, title: title.trim() || undefined })
	  await api.downloadReport(res.report.id, res.report.filename)
	  await refreshNotifications(); await load()
	  pushToast({ title: "Report Generated", message: `${res.report.format.toUpperCase()} report downloaded successfully.`, variant: "success" })
	} catch (err) { setError(err instanceof Error ? err.message : "Report generation failed") }
	finally { setGenerating(false) }
  }

  function removeReport(report: ReportItem) {
	requestConfirm({ title: "Delete Report", message: `Delete "${report.title}"?`, confirmLabel: "Delete", danger: true, onConfirm: async () => {
	  await api.deleteReport(report.id); await load(); pushToast({ title: "Report Deleted", message: "The report was removed.", variant: "success" })
	} })
  }

  const FormatIcon = format === "xlsx" ? FileSpreadsheet : format === "json" ? FileJson : FileText

  return (
	<PageFrame eyebrow="Reporting" title="Reports Center" description="Generate real PDF, Excel, CSV, and JSON reports from the active dataset" actions={<button type="button" className="sp-btn-secondary" onClick={load}><RefreshCw size={14} /> Refresh</button>}>
	  <div className="grid grid-cols-1 lg:grid-cols-[320px_minmax(0,1fr)] gap-4">
		<ChartCard title="Generate Report">
		  <div className="space-y-3">
			<label className="block text-xs text-[var(--text-secondary)]">Report title<input className="sp-input w-full mt-1.5" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Executive intelligence report" /></label>
			<label className="block text-xs text-[var(--text-secondary)]">Report type<select className="sp-select w-full mt-1.5" value={reportType} onChange={(e) => setReportType(e.target.value)}><option value="overall">Executive Summary</option><option value="sentiment">Sentiment Analysis</option><option value="trends">Trending Topics</option><option value="engagement">Engagement Analysis</option><option value="platforms">Platform Comparison</option></select></label>
			<label className="block text-xs text-[var(--text-secondary)]">Format<select className="sp-select w-full mt-1.5" value={format} onChange={(e) => setFormat(e.target.value)}><option value="pdf">PDF</option><option value="xlsx">Excel (.xlsx)</option><option value="csv">CSV</option><option value="json">JSON</option></select></label>
			{error && <p className="text-xs text-rose-400">{error}</p>}
			<button type="button" className="sp-btn-primary w-full" disabled={generating} onClick={generate}><FormatIcon size={15} /> {generating ? "Generating..." : `Generate ${format.toUpperCase()}`}</button>
			<p className="text-[11px] text-[var(--text-muted)] m-0">Active dataset: {activeDataset?.name ?? "No dataset selected"}</p>
		  </div>
		</ChartCard>
		<ChartCard title="Report History" subtitle="Previously generated downloadable reports">
		  {loading ? <LoadingSkeleton cards={4} /> : error ? <ErrorState message={error} onRetry={load} /> : reports.length === 0 ? <EmptyState title="No reports generated" message="Generate a report from the active dataset to create the first entry." /> : <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="text-xs text-[var(--text-secondary)]"><tr><th className="p-3 text-left">Report</th><th className="p-3">Type</th><th className="p-3">Format</th><th className="p-3">Created</th><th className="p-3 text-right">Actions</th></tr></thead><tbody>{reports.map((report) => <tr key={report.id} className="border-t border-[var(--border-subtle)]"><td className="p-3"><strong className="block">{report.title}</strong><span className="text-xs text-[var(--text-secondary)]">{report.dataset_name}</span></td><td className="p-3 text-center">{report.report_type}</td><td className="p-3 text-center uppercase">{report.format}</td><td className="p-3 text-center text-xs text-[var(--text-secondary)]">{new Date(report.created_at).toLocaleString()}</td><td className="p-3"><div className="flex justify-end gap-1"><button type="button" className="sp-btn-secondary !h-8 !px-2" title="Download report" onClick={() => void api.downloadReport(report.id, report.filename).catch((err) => pushToast({ title: "Download Failed", message: String(err), variant: "error" }))}><Download size={14} /></button><button type="button" className="sp-btn-secondary !h-8 !px-2 text-rose-400" title="Delete report" onClick={() => removeReport(report)}><Trash2 size={14} /></button></div></td></tr>)}</tbody></table></div>}
		</ChartCard>
	  </div>
	</PageFrame>
  )
}
