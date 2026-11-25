export interface DatasetRecord {
  id: number
  name: string
  original_filename: string
  row_count: number
  cleaned_row_count: number
  column_count: number
  duplicate_count: number
  missing_value_count: number
  invalid_record_count: number
  status: string
  column_mapping: Record<string, string>
  cleaning_summary: Record<string, any>
  is_bundled: boolean
  is_active: boolean
  owner_id: number | null
  created_at: string
}

export interface DatasetPreview {
  id: number
  name: string
  columns: string[]
  rows: Record<string, any>[]
  row_count: number
  cleaned_row_count: number
  missing_values: Record<string, number>
  duplicate_count: number
  invalid_record_count: number
  column_mapping: Record<string, string>
  cleaning_summary: Record<string, any>
}

export interface UploadInspection {
  filename: string
  suggested_name: string
  file_size_bytes: number
  row_count: number
  column_count: number
  columns: string[]
  detected_mapping: Record<string, string>
  missing_values: Record<string, number>
  total_missing_values: number
  estimated_duplicates: number
  sample_rows: Record<string, any>[]
  supported_fields: Array<{
    key: string
    label: string
    required: boolean
    description: string
  }>
}

export interface AnalyticsMeta {
  dataset_id: number | null
  dataset_name: string
  total_rows_unfiltered: number
  filtered_rows: number
  date_min: string | null
  date_max: string | null
  available_platforms: string[]
  available_topics: string[]
  has_engagement_denominator: boolean
  engagement_rate_basis: string | null
  sentiment_disclaimer: string
}

export interface PostItem {
  post_id: string
  author: string
  platform: string
  content: string
  topic: string
  hashtags: string[]
  likes: number
  shares: number
  comments: number
  engagement: number
  sentiment: "Positive" | "Negative" | "Neutral" | string
  sentiment_polarity: number
  detected_emotion: string
  sentiment_source: string
  char_length: number
  timestamp: string | null
  z_score?: number
  median_multiple?: number
  reason?: string
}

export interface UserProfile {
  id: number
  email: string
  full_name: string
  role: string
  organization: string
  bio: string
  is_active: boolean
  created_at: string
}

export interface NotificationItem {
  id: number
  title: string
  message: string
  category: string
  severity: "info" | "success" | "warning" | "error" | string
  is_read: boolean
  meta: Record<string, any>
  created_at: string
}

export interface ActivityItem {
  id: number
  action: string
  target_type: string
  target_name: string
  details: string
  created_at: string
}

export interface ReportItem {
  id: number
  dataset_id: number | null
  dataset_name: string
  report_type: string
  format: "pdf" | "csv" | "xlsx" | "json" | string
  filename: string
  title: string
  summary: Record<string, any>
  created_at: string
}

export interface AnalyticsFilterParams {
  dataset_id?: number | null
  platform?: string
  sentiment?: string
  topic?: string
  hashtag?: string
  start_date?: string
  end_date?: string
  search?: string
}

export interface StructuredInsight {
  id: string
  title: string
  category: string
  observation: string
  evidence: string
  recommendation: string
  confidence_note: string
}

