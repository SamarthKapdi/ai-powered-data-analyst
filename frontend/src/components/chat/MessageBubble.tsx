import type { ChatMessage } from '../../types';
import { ChartRenderer } from '../charts/ChartRenderer';
import { CodeBlock } from './CodeBlock';
import { AnomalyCards } from './AnomalyCards';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const { role, content, timestamp, analysis, isLoading } = message;

  if (isLoading) {
    return (
      <div className="message message-assistant">
        <div className="message-avatar">AI</div>
        <div className="message-body">
          <div className="message-content">
            <div className="loading-dots">
              <span className="loading-dot" />
              <span className="loading-dot" />
              <span className="loading-dot" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`message message-${role}`}>
      <div className="message-avatar">{role === 'user' ? 'You' : 'AI'}</div>
      <div className="message-body">
        <div className="message-content">
          <div style={{ whiteSpace: 'pre-wrap' }}>{content}</div>
        </div>

        {role === 'assistant' && analysis && (
          <div className="analysis-result">
            {/* Chart */}
            {analysis.chart_config && analysis.chart_config.data && analysis.chart_config.data.length > 0 && (
              <ChartRenderer config={analysis.chart_config} />
            )}

            {/* Data Table for results */}
            {analysis.data && Array.isArray(analysis.data) && analysis.data.length > 0 && (
              <div className="result-table-wrapper" style={{ marginTop: '0.75rem' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      {Object.keys(analysis.data[0]).map((key) => (
                        <th key={key}>{key}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.data.slice(0, 50).map((row: any, idx: number) => (
                      <tr key={idx}>
                        {Object.values(row).map((val: any, ci: number) => (
                          <td key={ci}>
                            {val != null
                              ? typeof val === 'number'
                                ? val.toLocaleString(undefined, { maximumFractionDigits: 2 })
                                : String(val)
                              : '—'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* SQL Code */}
            {analysis.sql_code && (
              <CodeBlock code={analysis.sql_code} language="SQL" />
            )}

            {/* Pandas Code */}
            {analysis.pandas_code && (
              <CodeBlock code={analysis.pandas_code} language="Python (Pandas)" />
            )}

            {/* Anomalies */}
            {analysis.anomalies && analysis.anomalies.length > 0 && (
              <AnomalyCards anomalies={analysis.anomalies} />
            )}

            {/* Insights */}
            {analysis.insights && analysis.insights.length > 0 && (
              <div style={{ marginTop: '0.75rem' }}>
                {analysis.insights.map((insight, i) => (
                  <div key={i} className="insight-item">
                    💡 {insight}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="message-time">
          {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  );
}
