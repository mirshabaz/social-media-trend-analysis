import type {
  ActivityItem,
  AnalyticsFilterParams,
  DatasetPreview,
  DatasetRecord,
  NotificationItem,
  ReportItem,
  StructuredInsight,
  UploadInspection,
  UserProfile,
} from "../types/api"

const API_BASE = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "")

const TOKEN_STORAGE_KEY = "socialpulse_auth_token"

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function setStoredToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token)
    else localStorage.removeItem(TOKEN_STORAGE_KEY)
  } catch {
    // ignore storage failures
  }
}

function buildQuery(params?: Record<string, string | number | boolean | null | undefined>): string {
  if (!params) return ""
  const qs = new URLSearchParams()
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && String(val).trim() !== "") {
      qs.set(key, String(val))
    }
  }
  const encoded = qs.toString()
  return encoded ? `?${encoded}` : ""
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json()
    if (typeof data?.detail === "string") return data.detail
    if (Array.isArray(data?.detail)) return data.detail.map((d: any) => d.msg).join(", ")
    if (typeof data?.message === "string") return data.message
  } catch {
    try {
      const text = await response.text()
      if (text) return text
    } catch {
      // ignore
    }
  }
  return `Request failed with status ${response.status}`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getStoredToken()
  const headers = new Headers(init.headers)
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", "Bearer " + token)
  }
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response))
  }
  return response.json() as Promise<T>
}

export async function downloadFileFromApi(path: string, fallbackFilename: string): Promise<void> {
  const token = getStoredToken()
  const headers = new Headers()
  if (token) headers.set("Authorization", "Bearer " + token)
  const response = await fetch(`${API_BASE}${path}`, { headers })
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response))
  }
  const blob = await response.blob()
  const disposition = response.headers.get("Content-Disposition") ?? ""
  const match = disposition.match(/filename="?([^"]+)"?/i)
  const filename = match?.[1] || fallbackFilename

  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export const api = {
  baseUrl: API_BASE,
  health: () => request<{ status: string; service: string; version: string }>("/api/health"),

  // Datasets
  datasets: () => request<{ status: string; datasets: DatasetRecord[] }>("/api/datasets"),
  activeDataset: () => request<{ status: string; dataset: DatasetRecord | null }>("/api/dataset"),
  datasetDetail: (id: number, limit = 30) =>
    request<{ status: string; dataset: DatasetRecord; preview: DatasetPreview }>(
      `/api/dataset/${id}${buildQuery({ limit })}`
    ),
  inspectUpload: async (file: File) => {
    const form = new FormData()
    form.append("file", file)
    return request<{ status: string; preview: UploadInspection }>("/api/upload/preview", {
      method: "POST",
      body: form,
    })
  },
  uploadDataset: async (
    file: File,
    options?: {
      columnMapping?: Record<string, string>
      datasetName?: string
      activate?: boolean
    }
  ) => {
    const form = new FormData()
    form.append("file", file)
    if (options?.columnMapping) {
      form.append("column_mapping", JSON.stringify(options.columnMapping))
    }
    if (options?.datasetName) {
      form.append("dataset_name", options.datasetName)
    }
    if (options?.activate !== undefined) {
      form.append("activate", String(options.activate))
    }
    return request<{ status: string; dataset: DatasetRecord }>("/api/upload", {
      method: "POST",
      body: form,
    })
  },
  activateDataset: (id: number) =>
    request<{ status: string; dataset: DatasetRecord }>(`/api/dataset/${id}/activate`, {
      method: "POST",
    }),
  deleteDataset: (id: number) =>
    request<{ status: string; deleted_id: number; new_active_id: number | null }>(
      `/api/dataset/${id}`,
      { method: "DELETE" }
    ),
  downloadDataset: (id: number, name: string, cleaned = true) =>
    downloadFileFromApi(
      `/api/dataset/${id}/download${buildQuery({ cleaned })}`,
      `${name}_${cleaned ? "cleaned" : "original"}.csv`
    ),

  // Analytics
  overview: (filters?: AnalyticsFilterParams) =>
    request<{ status: string; data: Record<string, any> }>(
      `/api/overview${buildQuery(filters as Record<string, any>)}`
    ),
  trends: (filters?: AnalyticsFilterParams) =>
    request<{ status: string; data: Record<string, any> }>(
      `/api/trends${buildQuery(filters as Record<string, any>)}`
    ),
  sentiment: (filters?: AnalyticsFilterParams) =>
    request<{ status: string; data: Record<string, any> }>(
      `/api/sentiment${buildQuery(filters as Record<string, any>)}`
    ),
  engagement: (filters?: AnalyticsFilterParams & { sort_by?: string; limit?: number }) =>
    request<{ status: string; data: Record<string, any> }>(
      `/api/engagement${buildQuery(filters as Record<string, any>)}`
    ),
  platforms: (params?: { dataset_id?: number | null; platforms?: string; start_date?: string; end_date?: string }) =>
    request<{ status: string; data: any[]; meta: Record<string, any> }>(
      `/api/platforms${buildQuery(params)}`
    ),
  hashtags: (filters?: AnalyticsFilterParams & { tag?: string }) =>
    request<{ status: string; data: Record<string, any> }>(
      `/api/hashtags${buildQuery(filters as Record<string, any>)}`
    ),
  contentPerformance: (filters?: AnalyticsFilterParams) =>
    request<{ status: string; data: Record<string, any> }>(
      `/api/content-performance${buildQuery(filters as Record<string, any>)}`
    ),
  topics: (filters?: AnalyticsFilterParams) =>
    request<{ status: string; data: Record<string, any> }>(
      `/api/topics${buildQuery(filters as Record<string, any>)}`
    ),
  timeAnalysis: (filters?: AnalyticsFilterParams & { granularity?: string }) =>
    request<{ status: string; data: Record<string, any> }>(
      `/api/time-analysis${buildQuery(filters as Record<string, any>)}`
    ),
  anomalies: (filters?: AnalyticsFilterParams) =>
    request<{ status: string; data: Record<string, any> }>(
      `/api/anomalies${buildQuery(filters as Record<string, any>)}`
    ),
  posts: (
    filters?: AnalyticsFilterParams & {
      sort_by?: string
      sort_dir?: string
      page?: number
      page_size?: number
    }
  ) =>
    request<{ status: string; data: Record<string, any> }>(
      `/api/posts${buildQuery(filters as Record<string, any>)}`
    ),
  postDetail: (postId: string, datasetId?: number | null) =>
    request<{ status: string; data: Record<string, any> }>(
      `/api/posts/${encodeURIComponent(postId)}${buildQuery({ dataset_id: datasetId })}`
    ),
  insights: (filters?: AnalyticsFilterParams) =>
    request<{
      status: string
      insights: string[]
      structured_insights: StructuredInsight[]
      data: Record<string, any>
    }>(`/api/insights${buildQuery(filters as Record<string, any>)}`),

  // Assistant
  askAssistant: (question: string, datasetId?: number | null) =>
    request<{
      status: string
      data: {
        answer: string
        metrics: Array<{ label: string; value: string; detail: string }>
        suggested_followups: string[]
        mode: string
        dataset_name: string
      }
    }>("/api/assistant/query", {
      method: "POST",
      body: JSON.stringify({ question, dataset_id: datasetId }),
    }),

  // Reports
  reports: () => request<{ status: string; reports: ReportItem[] }>("/api/reports"),
  generateReport: (payload: {
    report_type: string
    format: string
    dataset_id?: number | null
    platform?: string
    start_date?: string
    end_date?: string
    title?: string
  }) =>
    request<{ status: string; report: ReportItem }>("/api/reports/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  downloadReport: (id: number, filename: string) =>
    downloadFileFromApi(`/api/reports/${id}/download`, filename),
  deleteReport: (id: number) =>
    request<{ status: string; deleted_id: number }>(`/api/reports/${id}`, { method: "DELETE" }),

  // System / Search / Notifications / Activity
  search: (q: string, datasetId?: number | null) =>
    request<{ status: string; results: Record<string, any[]> }>(
      `/api/search${buildQuery({ q, dataset_id: datasetId })}`
    ),
  notifications: () =>
    request<{ status: string; unread_count: number; notifications: NotificationItem[] }>(
      "/api/notifications"
    ),
  markNotificationRead: (id: number) =>
    request<{ status: string }>(`/api/notifications/${id}/read`, { method: "POST" }),
  markAllNotificationsRead: () =>
    request<{ status: string }>("/api/notifications/read-all", { method: "POST" }),
  activity: (limit = 20) =>
    request<{ status: string; activity: ActivityItem[] }>(`/api/activity${buildQuery({ limit })}`),

  // Auth
  register: (payload: {
    email: string
    password: string
    full_name: string
    role?: string
    organization?: string
  }) =>
    request<{ status: string; token: string; user: UserProfile }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  login: (payload: { email: string; password: string }) =>
    request<{ status: string; token: string; user: UserProfile }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  logout: () => request<{ status: string }>("/api/auth/logout", { method: "POST" }),
  me: () => request<{ status: string; user: UserProfile }>("/api/auth/me"),
  updateProfile: (payload: {
    full_name: string
    role: string
    organization: string
    bio: string
  }) =>
    request<{ status: string; user: UserProfile }>("/api/auth/profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  changePassword: (payload: { current_password: string; new_password: string }) =>
    request<{ status: string; message: string }>("/api/auth/password", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
}
