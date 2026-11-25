import { useEffect, useRef, useState, type FormEvent } from "react"
import { Bot, Send, Sparkles, Trash2 } from "lucide-react"
import { PageFrame } from "../components/PageFrame"
import { useApp } from "../context/AppContext"
import { api } from "../services/api"

interface Message { id: number; role: "assistant" | "user"; text: string; time: string }

export function AssistantPage() {
  const { activeDataset, datasetVersion } = useApp()
  const [question, setQuestion] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [messages, setMessages] = useState<Message[]>([{ id: 1, role: "assistant", text: "Ask me a question about the active dataset. I use its real cleaned records and deterministic analytics.", time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }])
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages, loading])

  async function submit(event: FormEvent) {
	event.preventDefault()
	const text = question.trim()
	if (!text || loading) return
	const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
	setMessages((items) => [...items, { id: Date.now(), role: "user", text, time: now }])
	setQuestion(""); setLoading(true); setError("")
	try {
	  const res = await api.askAssistant(text, activeDataset?.id)
	  setMessages((items) => [...items, { id: Date.now() + 1, role: "assistant", text: res.data.answer, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }])
	} catch (err) { setError(err instanceof Error ? err.message : "Assistant request failed") }
	finally { setLoading(false) }
  }

  const suggestions = ["Which platform has the highest engagement?", "What are the top five hashtags?", "What is the overall sentiment?", "Which topics are trending?", "Give recommendations based on this dataset."]

  return (
	<PageFrame eyebrow="AI Intelligence" title="Analytics Assistant" description={`Dataset-aware deterministic analysis${activeDataset ? ` · ${activeDataset.name}` : ""}`} actions={<button type="button" className="sp-btn-secondary" onClick={() => setMessages((items) => [items[0]])}><Trash2 size={14} /> Clear</button>}>
	  <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_280px] gap-4">
		<div className="sp-card flex flex-col h-[calc(100vh-230px)] min-h-[480px] overflow-hidden">
		  <div className="flex-1 overflow-y-auto p-5 space-y-4">
			{messages.map((message) => <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}><div className={`max-w-[82%] rounded-2xl px-4 py-3 ${message.role === "user" ? "bg-[var(--accent-primary)] text-white" : "bg-[var(--bg-elevated)] border border-[var(--border-subtle)]"}`}><div className="flex items-center gap-2 mb-1">{message.role === "assistant" ? <Sparkles size={13} /> : null}<span className="text-[10px] opacity-70">{message.time}</span></div><p className="text-sm leading-6 m-0 whitespace-pre-wrap">{message.text}</p></div></div>)}
			{loading && <div className="text-xs text-[var(--text-secondary)] flex items-center gap-2"><Bot size={15} className="animate-pulse" /> Analyzing active dataset...</div>}
			{error && <div className="text-xs text-rose-400 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3">{error}</div>}
			<div ref={endRef} />
		  </div>
		  <form onSubmit={submit} className="p-3 border-t border-[var(--border-subtle)] flex gap-2"><input key={datasetVersion} className="sp-input flex-1" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about platforms, hashtags, sentiment, trends, or posts..." /><button className="sp-btn-primary !px-3" type="submit" disabled={loading || !question.trim()} aria-label="Send question"><Send size={16} /></button></form>
		</div>
		<aside className="sp-card p-4 h-fit"><h2 className="text-sm font-semibold mb-3">Suggested questions</h2><div className="space-y-2">{suggestions.map((item) => <button key={item} type="button" className="w-full text-left rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-2.5 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--accent-primary)]" onClick={() => setQuestion(item)}>{item}</button>)}</div></aside>
	  </div>
	</PageFrame>
  )
}
