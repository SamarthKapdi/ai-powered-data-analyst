import { Plus, X, FileSpreadsheet } from 'lucide-react';
import type { DatasetInfo } from '../../types';
import { getFileSize } from '../../utils/helpers';

interface SidebarProps {
  datasets: DatasetInfo[];
  activeDatasetId: string | null;
  onSelectDataset: (id: string) => void;
  onRemoveDataset: (id: string) => void;
  onUploadClick: () => void;
}

export function Sidebar({
  datasets,
  activeDatasetId,
  onSelectDataset,
  onRemoveDataset,
  onUploadClick,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-title">Datasets</span>
        <button className="btn-icon" onClick={onUploadClick} aria-label="Upload file">
          <Plus size={16} />
        </button>
      </div>

      <div className="dataset-list">
        {datasets.length === 0 ? (
          <div className="sidebar-empty">
            <p>No datasets uploaded yet.</p>
            <button className="btn btn-primary" onClick={onUploadClick} style={{ marginTop: '0.75rem' }}>
              <Plus size={14} />
              Upload CSV
            </button>
          </div>
        ) : (
          datasets.map((dataset) => (
            <div
              key={dataset.id}
              className={`dataset-item ${dataset.id === activeDatasetId ? 'active' : ''}`}
              onClick={() => onSelectDataset(dataset.id)}
            >
              <div className="dataset-item-info">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                  <FileSpreadsheet size={14} style={{ color: '#10b981', flexShrink: 0 }} />
                  <span className="dataset-name">{dataset.filename}</span>
                </div>
                <div className="dataset-meta">
                  {dataset.rows.toLocaleString()} rows · {dataset.columns} cols · {getFileSize(dataset.file_size)}
                </div>
              </div>
              <button
                className="dataset-remove btn-icon"
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveDataset(dataset.id);
                }}
                aria-label="Remove dataset"
              >
                <X size={14} />
              </button>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
