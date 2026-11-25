import { useCallback, useEffect, useState, type DragEvent, type FormEvent } from "react"
import { Download, Database, RefreshCw, Search, Trash2, Upload } from "lucide-react"
import { PageFrame } from "../components/PageFrame"
import { EmptyState, ErrorState, LoadingSkeleton, ChartCard } from "../components/ui/StateBlocks"
import { useApp } from "../context/AppContext"
import { api } from "../services/api"
import type { UploadInspection } from "../types/api"

export function DatasetManagementPage() {
  const { datasets, activeDataset, refreshDatasets, activateDatasetById, bumpDatasetVersion, pushToast, requestConfirm } = useApp()
  const [query, setQuery] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [inspection, setInspection] = useState<UploadInspection | null>(null)
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [datasetName, setDatasetName] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [dragging, setDragging] = useState(false)

  const load = useCallback(async () => {
	setLoading(true); setError("")
	try { await refreshDatasets() } catch (err) { setError(err instanceof Error ? err.message : "Failed to load datasets") }
	finally { setLoading(false) }
  }, [refreshDatasets])

  useEffect(() => { load() }, [load])

  async function inspect(selected: File) {
	if (!selected.name.toLowerCase().endsWith(".csv")) { setError("Only CSV files are supported."); return }
	if (selected.size > 10 * 1024 * 1024) { setError("File exceeds the 10 MB upload limit."); return }
	setFile(selected); setError(""); setLoading(true)
	try {
	  const res = await api.inspectUpload(selected)
	  setInspection(res.preview)
	  setMapping(res.preview.detected_mapping)
	  setDatasetName(res.preview.suggested_name)
	} catch (err) { setError(err instanceof Error ? err.message : "Could not inspect CSV") }
	finally { setLoading(false) }
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
	event.preventDefault(); setDragging(false)
	const selected = event.dataTransfer.files[0]
	if (selected) void inspect(selected)
  }

  async function upload(event: FormEvent) {
	event.preventDefault()
	if (!file) { setError("Select a CSV file first."); return }
	setLoading(true); setError("")
	try {
	  await api.uploadDataset(file, { columnMapping: mapping, datasetName: datasetName.trim(), activate: true })
	  await refreshDatasets(); bumpDatasetVersion()
	  setFile(null); setInspection(null); setMapping({}); setDatasetName("")
	  pushToast({ title: "Dataset Saved", message: "CSV validated, cleaned, persisted, and activated.", variant: "success" })
	} catch (err) { setError(err instanceof Error ? err.message : "Upload failed") }
	finally { setLoading(false) }
  }

  async function removeDataset(id: number, name: string) {
	requestConfirm({ title: "Delete Dataset", message: `Delete "${name}" and its persisted cleaned data?`, confirmLabel: "Delete Dataset", danger: true, onConfirm: async () => {
	  await api.deleteDataset(id); await refreshDatasets(); bumpDatasetVersion()
	  pushToast({ title: "Dataset Deleted", message: `${name} was removed.`, variant: "success" })
	} })
  }

  const filtered = datasets.filter((item) => item.name.toLowerCase().includes(query.toLowerCase()) || item.original_filename.toLowerCase().includes(query.toLowerCase()))

  return (
	<PageFrame eyebrow="Data Management" title="Dataset Management" description="Upload, validate, clean, activate, inspect, download, and delete persisted datasets" actions={<button type="button" className="sp-btn-secondary" onClick={load}><RefreshCw size={15} /> Refresh</button>}>
	  <div className="grid grid-cols-1 xl:grid-cols-[360px_minmax(0,1fr)] gap-4">
		<form className="sp-card p-5 space-y-4" onSubmit={upload}>
		  <h2 className="text-sm font-semibold m-0">Upload CSV</h2>
		  <div className={`rounded-xl border border-dashed p-6 text-center transition-colors ${dragging ? "border-[var(--accent-primary)] bg-[var(--accent-soft)]" : "border-[var(--border-strong)]"}`} onDragEnter={(e) => { e.preventDefault(); setDragging(true) }} onDragOver={(e) => e.preventDefault()} onDragLeave={() => setDragging(false)} onDrop={onDrop}>
			<Upload className="mx-auto text-[var(--accent-primary)]" size={26} />
			<p className="text-sm mt-3 mb-2">Drag and drop a CSV here</p>
			<label className="sp-btn-secondary inline-flex cursor-pointer"><input className="sr-only" type="file" accept=".csv,text/csv" onChange={(e) => { const selected = e.target.files?.[0]; if (selected) void inspect(selected) }} />Choose File</label>
			{file && <p className="text-xs text-[var(--text-secondary)] mt-3 mb-0 break-all">{file.name}</p>}
		  </div>
		  {inspection && (
			<div className="space-y-3">
			  <input className="sp-input w-full" value={datasetName} onChange={(e) => setDatasetName(e.target.value)} placeholder="Dataset name" />
			  <div className="grid grid-cols-3 gap-2 text-center">
				<div className="sp-card p-2"><strong className="block text-lg">{inspection.row_count}</strong><span className="text-[10px] text-[var(--text-secondary)]">Rows</span></div>
				<div className="sp-card p-2"><strong className="block text-lg">{inspection.total_missing_values}</strong><span className="text-[10px] text-[var(--text-secondary)]">Missing</span></div>
				<div className="sp-card p-2"><strong className="block text-lg">{inspection.estimated_duplicates}</strong><span className="text-[10px] text-[var(--text-secondary)]">Duplicates</span></div>
			  </div>
			  <div className="max-h-48 overflow-auto space-y-2">
				{inspection.columns.map((column) => (
				  <label key={column} className="grid grid-cols-[1fr_150px] gap-2 items-center text-xs"><span className="truncate text-[var(--text-secondary)]">{column}</span><select className="sp-select !h-8" value={mapping[column] || "ignored"} onChange={(e) => setMapping((prev) => ({ ...prev, [column]: e.target.value }))}><option value="ignored">Ignore</option>{inspection.supported_fields.map((field) => <option key={field.key} value={field.key}>{field.label}</option>)}</select></label>
				))}
			  </div>
			  <button className="sp-btn-primary w-full" type="submit" disabled={loading}><Upload size={15} /> Save, Clean & Activate</button>
			</div>
		  )}
		  {error && <p className="text-xs text-rose-400 mb-0">{error}</p>}
		</form>

		<div className="space-y-4">
		  <ChartCard title="Dataset History" subtitle={`${filtered.length} of ${datasets.length} datasets`} action={<div className="relative"><Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" /><input className="sp-input !h-8 !pl-8 w-48" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search datasets" /></div>}>
			{loading ? <LoadingSkeleton cards={4} /> : error ? <ErrorState message={error} onRetry={load} /> : filtered.length === 0 ? <EmptyState title="No datasets found" /> : (
			  <div className="overflow-x-auto">
				<table className="w-full text-sm"><thead className="text-xs text-[var(--text-secondary)]"><tr><th className="text-left p-3">Dataset</th><th className="text-right p-3">Rows</th><th className="text-right p-3">Missing</th><th className="text-right p-3">Duplicates</th><th className="p-3">Status</th><th className="p-3 text-right">Actions</th></tr></thead><tbody>{filtered.map((item) => <tr key={item.id} className="border-t border-[var(--border-subtle)]"><td className="p-3"><strong className="block">{item.name}</strong><span className="text-xs text-[var(--text-secondary)]">{item.original_filename}</span></td><td className="p-3 text-right">{item.cleaned_row_count}</td><td className="p-3 text-right">{item.missing_value_count}</td><td className="p-3 text-right">{item.duplicate_count}</td><td className="p-3 text-center"><span className={item.is_active ? "text-emerald-400" : "text-[var(--text-secondary)]"}>{item.is_active ? "Active" : item.status}</span></td><td className="p-3"><div className="flex justify-end gap-1"><button type="button" title="Activate" className="sp-btn-secondary !h-8 !px-2" disabled={item.is_active} onClick={() => void activateDatasetById(item.id)}><Database size={14} /></button><button type="button" title="Download cleaned CSV" className="sp-btn-secondary !h-8 !px-2" onClick={() => void api.downloadDataset(item.id, item.name, true).catch((err) => pushToast({ title: "Download Failed", message: String(err), variant: "error" }))}><Download size={14} /></button><button type="button" title="Delete dataset" className="sp-btn-secondary !h-8 !px-2 text-rose-400" onClick={() => void removeDataset(item.id, item.name)}><Trash2 size={14} /></button></div></td></tr>)}</tbody></table>
			  </div>
			)}
		  </ChartCard>
		  {activeDataset && <div className="sp-card p-4 text-xs text-[var(--text-secondary)]">Active dataset: <strong className="text-[var(--text-primary)]">{activeDataset.name}</strong> · {activeDataset.cleaned_row_count} cleaned rows · {activeDataset.column_count} columns</div>}
		</div>
	  </div>
	</PageFrame>
  )
}
