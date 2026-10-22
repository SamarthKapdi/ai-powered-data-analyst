import axios from 'axios';
import type { DatasetInfo, AnalysisResponse, InsightsData, DataPreview, ChatMessage } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
});

export async function uploadFiles(files: File[]): Promise<DatasetInfo[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  const response = await api.post<DatasetInfo[]>('/api/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function deleteDataset(datasetId: string): Promise<void> {
  await api.delete(`/api/upload/${datasetId}`);
}

export async function getDataPreview(datasetId: string): Promise<DataPreview> {
  const response = await api.get<DataPreview>(`/api/upload/${datasetId}/preview`);
  return response.data;
}

export async function listDatasets(): Promise<DatasetInfo[]> {
  const response = await api.get<DatasetInfo[]>('/api/datasets');
  return response.data;
}

export async function analyzeData(
  question: string,
  datasetIds: string[],
  conversationHistory: Array<{ role: string; content: string }>
): Promise<AnalysisResponse> {
  const response = await api.post<AnalysisResponse>('/api/analyze', {
    question,
    dataset_ids: datasetIds,
    conversation_history: conversationHistory,
  });
  return response.data;
}

export async function getInsights(datasetId: string): Promise<InsightsData> {
  const response = await api.post<InsightsData>('/api/insights', {
    dataset_id: datasetId,
  });
  return response.data;
}

export async function getDatasetData(
  datasetId: string,
  page: number = 1,
  pageSize: number = 50
): Promise<{ data: Record<string, unknown>[]; total: number; page: number; page_size: number }> {
  const response = await api.get(`/api/datasets/${datasetId}/data`, {
    params: { page, page_size: pageSize },
  });
  return response.data;
}

export async function healthCheck(): Promise<boolean> {
  try {
    await api.get('/api/health');
    return true;
  } catch {
    return false;
  }
}

export function buildConversationHistory(
  messages: ChatMessage[]
): Array<{ role: string; content: string }> {
  return messages
    .filter((m) => !m.isLoading)
    .slice(-10)
    .map((m) => ({
      role: m.role,
      content: m.role === 'assistant' && m.analysis ? m.analysis.answer : m.content,
    }));
}
