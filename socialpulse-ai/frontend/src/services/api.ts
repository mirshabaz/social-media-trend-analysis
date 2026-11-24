const API_BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000"

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) throw new Error(`API request failed: ${response.status}`)
  return response.json() as Promise<T>
}

export const api = {
  health: () => get<{ status: string }>("/api/health"),
  overview: () => get<{ status: string; data: Record<string, any> }>("/api/overview"),
  trends: () => get<{ status: string; data: Record<string, any> }>("/api/trends"),
  sentiment: () => get<{ status: string; data: Record<string, any> }>("/api/sentiment"),
  engagement: () => get<{ status: string; data: Record<string, any> }>("/api/engagement"),
  platforms: () => get<{ status: string; data: any[] }>("/api/platforms"),
  insights: () => get<{ status: string; insights: string[]; data: Record<string, any> }>("/api/insights"),
  datasets: () => get<{ status: string; datasets: any[] }>("/api/datasets"),
  activeDataset: () => get<{ status: string; dataset: any }>("/api/dataset"),
  uploadDataset: async (file: File) => {
    const form = new FormData()
    form.append("file", file)
    const response = await fetch(`${API_BASE}/api/upload`, { method: "POST", body: form })
    if (!response.ok) throw new Error(await response.text())
    return response.json()
  },
}
