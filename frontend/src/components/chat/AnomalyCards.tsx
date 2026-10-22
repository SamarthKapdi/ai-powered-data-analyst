import { AlertTriangle } from 'lucide-react';
import type { AnomalyInfo } from '../../types';

interface AnomalyCardsProps {
  anomalies: AnomalyInfo[];
}

export function AnomalyCards({ anomalies }: AnomalyCardsProps) {
  const displayed = anomalies.slice(0, 10);
  const remaining = anomalies.length - displayed.length;

  return (
    <div style={{ marginTop: '0.75rem' }}>
      <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#ef4444', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
        <AlertTriangle size={14} />
        {anomalies.length} Anomal{anomalies.length === 1 ? 'y' : 'ies'} Detected
      </div>

      {displayed.map((anomaly, i) => (
        <div key={i} className="anomaly-card">
          <div className="anomaly-header">
            <AlertTriangle size={14} />
            Row {anomaly.row_index} — {anomaly.column}
          </div>
          <div className="anomaly-details">
            <div><strong>Value:</strong> {typeof anomaly.value === 'number' ? anomaly.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : anomaly.value}</div>
            <div><strong>Expected Range:</strong> {anomaly.expected_range}</div>
            <div><strong>Method:</strong> {anomaly.method}</div>
            <div><strong>Reason:</strong> {anomaly.reason}</div>
            {anomaly.severity && <div><strong>Severity:</strong> <span style={{ color: anomaly.severity === 'high' ? '#ef4444' : anomaly.severity === 'medium' ? '#f59e0b' : '#64748b' }}>{anomaly.severity}</span></div>}
          </div>
          <div className="anomaly-warning">
            ⚠️ A statistical anomaly is not necessarily an error or fraudulent event. Please verify the underlying data.
          </div>
        </div>
      ))}

      {remaining > 0 && (
        <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.5rem', textAlign: 'center' }}>
          ...and {remaining} more anomalies
        </div>
      )}
    </div>
  );
}
