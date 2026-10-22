import { Upload } from 'lucide-react';

interface WelcomeScreenProps {
  onUploadClick: () => void;
}

export function WelcomeScreen({ onUploadClick }: WelcomeScreenProps) {
  return (
    <div className="welcome-container">
      <div className="welcome-icon">📊</div>
      <h1 className="welcome-title">InsightFlow AI</h1>
      <p className="welcome-subtitle">
        Upload your CSV files and ask questions in natural language. Get instant insights,
        visualizations, anomaly detection, and generated SQL/Pandas code.
      </p>

      <div className="welcome-features">
        <div className="feature-card">
          <div className="feature-icon">💬</div>
          <div className="feature-title">Natural Language</div>
          <div className="feature-desc">
            Ask questions about your data in plain English and get accurate answers.
          </div>
        </div>
        <div className="feature-card">
          <div className="feature-icon">📈</div>
          <div className="feature-title">Visualizations</div>
          <div className="feature-desc">
            Auto-generated charts: bar, line, pie, scatter plots, and data tables.
          </div>
        </div>
        <div className="feature-card">
          <div className="feature-icon">🔍</div>
          <div className="feature-title">Anomaly Detection</div>
          <div className="feature-desc">
            Statistical anomaly detection using IQR, Z-score, and time-series methods.
          </div>
        </div>
        <div className="feature-card">
          <div className="feature-icon">🧮</div>
          <div className="feature-title">Code Generation</div>
          <div className="feature-desc">
            Get SQL and Pandas code that reproduces your analysis.
          </div>
        </div>
        <div className="feature-card">
          <div className="feature-icon">📋</div>
          <div className="feature-title">Multi-File Analysis</div>
          <div className="feature-desc">
            Upload multiple CSVs and compare or join datasets seamlessly.
          </div>
        </div>
        <div className="feature-card">
          <div className="feature-icon">💡</div>
          <div className="feature-title">Smart Insights</div>
          <div className="feature-desc">
            Automated KPIs, trends, and actionable observations from your data.
          </div>
        </div>
      </div>

      <button className="btn btn-primary" onClick={onUploadClick} style={{ fontSize: '0.9375rem', padding: '0.75rem 1.75rem' }}>
        <Upload size={18} />
        Upload CSV to Get Started
      </button>
    </div>
  );
}
