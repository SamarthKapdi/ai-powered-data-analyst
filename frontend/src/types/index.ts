export interface DatasetInfo {
  id: string;
  filename: string;
  rows: number;
  columns: number;
  column_names: string[];
  column_types: Record<string, string>;
  missing_values: Record<string, number>;
  duplicate_rows: number;
  file_size: number;
  uploaded_at: string;
}

export interface ChartConfig {
  type: 'bar' | 'line' | 'pie' | 'scatter' | 'table';
  data: Record<string, unknown>[];
  options: {
    xKey?: string;
    yKey?: string | string[];
    title?: string;
    xLabel?: string;
    yLabel?: string;
    nameKey?: string;
    valueKey?: string;
    colors?: string[];
  };
}

export interface AnomalyInfo {
  row_index: number;
  column: string;
  value: number;
  expected_range: string;
  method: string;
  reason: string;
  severity: string;
}

export interface AnalysisResponse {
  answer: string;
  data?: Record<string, unknown>[] | Record<string, unknown>;
  chart_config?: ChartConfig;
  sql_code?: string;
  pandas_code?: string;
  anomalies?: AnomalyInfo[];
  insights?: string[];
  error?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  analysis?: AnalysisResponse;
  isLoading?: boolean;
}

export interface InsightsData {
  kpis: Array<{
    name: string;
    value: number | string;
    description: string;
    change?: number;
  }>;
  top_performers: Array<{
    name: string;
    value: number;
    category: string;
  }>;
  trends: Array<{
    period: string;
    value: number;
    change?: number;
  }>;
  anomalies: AnomalyInfo[];
  suggestions: string[];
}

export interface DataPreview {
  columns: string[];
  dtypes: Record<string, string>;
  preview_data: Record<string, unknown>[];
  total_rows: number;
  missing_summary: Record<string, number>;
  duplicate_count: number;
}
