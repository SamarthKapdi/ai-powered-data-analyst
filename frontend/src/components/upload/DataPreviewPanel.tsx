import { useState, useEffect } from 'react';
import { getDataPreview } from '../../services/api';
import type { DatasetInfo, DataPreview } from '../../types';
import { formatNumber } from '../../utils/helpers';

interface DataPreviewPanelProps {
  dataset: DatasetInfo;
}

export function DataPreviewPanel({ dataset }: DataPreviewPanelProps) {
  const [preview, setPreview] = useState<DataPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    setLoading(true);
    setError(null);
    getDataPreview(dataset.id)
      .then(setPreview)
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load preview'))
      .finally(() => setLoading(false));
  }, [dataset.id]);

  if (loading) {
    return (
      <div className="preview-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="preview-container">
        <div style={{ color: '#ef4444', fontSize: '0.875rem' }}>{error}</div>
      </div>
    );
  }

  if (!preview) return null;

  const filteredData = searchTerm
    ? preview.preview_data.filter((row) =>
        Object.values(row).some((v) =>
          String(v).toLowerCase().includes(searchTerm.toLowerCase())
        )
      )
    : preview.preview_data;

  const missingCount = Object.values(dataset.missing_values).reduce((a, b) => a + b, 0);

  return (
    <div className="preview-container">
      <div className="preview-stats">
        <div className="preview-stat">
          <div className="preview-stat-label">Rows</div>
          <div className="preview-stat-value">{formatNumber(dataset.rows)}</div>
        </div>
        <div className="preview-stat">
          <div className="preview-stat-label">Columns</div>
          <div className="preview-stat-value">{dataset.columns}</div>
        </div>
        <div className="preview-stat">
          <div className="preview-stat-label">Missing Values</div>
          <div className="preview-stat-value" style={{ color: missingCount > 0 ? '#f59e0b' : '#10b981' }}>
            {missingCount}
          </div>
        </div>
        <div className="preview-stat">
          <div className="preview-stat-label">Duplicates</div>
          <div className="preview-stat-value" style={{ color: dataset.duplicate_rows > 0 ? '#f59e0b' : '#10b981' }}>
            {dataset.duplicate_rows}
          </div>
        </div>
      </div>

      <div className="preview-section">
        <div className="preview-section-title">Column Schema</div>
        <div className="column-tags">
          {dataset.column_names.map((col) => (
            <span key={col} className="column-tag">
              {col}
              <span className="column-type">{dataset.column_types[col] || 'unknown'}</span>
            </span>
          ))}
        </div>
      </div>

      {missingCount > 0 && (
        <div className="preview-section">
          <div className="preview-section-title">Missing Values by Column</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
            {Object.entries(dataset.missing_values)
              .filter(([_, count]) => count > 0)
              .map(([col, count]) => (
                <span key={col} className="column-tag" style={{ borderColor: '#f59e0b' }}>
                  {col}: <span style={{ color: '#f59e0b', fontWeight: 600 }}>{count}</span>
                </span>
              ))}
          </div>
        </div>
      )}

      <div className="preview-section">
        <div className="preview-section-title">Data Preview (first {Math.min(preview.total_rows, 100)} rows)</div>
        <input
          type="text"
          placeholder="Search data..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            width: '100%',
            padding: '0.5rem 0.75rem',
            background: 'var(--bg-primary)',
            border: '1px solid var(--border)',
            borderRadius: '0.375rem',
            color: 'var(--text-primary)',
            fontSize: '0.8125rem',
            marginBottom: '0.5rem',
            outline: 'none',
          }}
        />
        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                {preview.columns.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredData.slice(0, 100).map((row, idx) => (
                <tr key={idx}>
                  {preview.columns.map((col) => (
                    <td key={col}>{row[col] != null ? String(row[col]) : '—'}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
