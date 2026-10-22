import { useState, useEffect } from 'react';
import { getInsights } from '../../services/api';
import { formatNumber } from '../../utils/helpers';
import type { InsightsData } from '../../types';

interface InsightsPanelProps {
  datasetId: string;
}

export function InsightsPanel({ datasetId }: InsightsPanelProps) {
  const [insights, setInsights] = useState<InsightsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getInsights(datasetId)
      .then(setInsights)
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load insights'))
      .finally(() => setLoading(false));
  }, [datasetId]);

  if (loading) {
    return (
      <div className="insights-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="insights-container">
        <div style={{ color: '#ef4444', fontSize: '0.875rem' }}>{error}</div>
      </div>
    );
  }

  if (!insights) return null;

  return (
    <div className="insights-container">
      {/* KPIs */}
      {insights.kpis.length > 0 && (
        <div>
          <div className="preview-section-title">Key Metrics</div>
          <div className="kpi-grid">
            {insights.kpis.slice(0, 8).map((kpi, i) => (
              <div key={i} className="kpi-card">
                <div className="kpi-name">{kpi.name}</div>
                <div className="kpi-value">
                  {typeof kpi.value === 'number' ? formatNumber(kpi.value) : kpi.value}
                </div>
                <div className="kpi-desc">{kpi.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Performers */}
      {insights.top_performers.length > 0 && (
        <div className="preview-section">
          <div className="preview-section-title">Top Performers</div>
          {insights.top_performers.slice(0, 5).map((tp: any, i: number) => (
            <div key={i} className="insight-item" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>
                <strong>#{i + 1}</strong> {tp.name}
                {tp.category && <span style={{ color: '#64748b', marginLeft: '0.5rem' }}>({tp.category})</span>}
              </span>
              <span style={{ fontWeight: 600, color: '#3b82f6' }}>
                {typeof tp.value === 'number' ? formatNumber(tp.value) : tp.value}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Trends */}
      {insights.trends.length > 0 && (
        <div className="preview-section">
          <div className="preview-section-title">Trends</div>
          {insights.trends.map((trend: any, i: number) => (
            <div key={i} className="insight-item" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{trend.period}</span>
              <span style={{ fontWeight: 600 }}>
                {typeof trend.value === 'number' ? formatNumber(trend.value) : trend.value}
                {trend.change != null && (
                  <span style={{ color: trend.change >= 0 ? '#10b981' : '#ef4444', marginLeft: '0.375rem', fontSize: '0.75rem' }}>
                    {trend.change >= 0 ? '↑' : '↓'} {Math.abs(trend.change).toFixed(1)}%
                  </span>
                )}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Suggested Questions */}
      {insights.suggestions.length > 0 && (
        <div className="preview-section">
          <div className="preview-section-title">Suggested Questions</div>
          {insights.suggestions.map((s, i) => (
            <div key={i} className="insight-item" style={{ fontSize: '0.75rem' }}>
              💡 {s}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
