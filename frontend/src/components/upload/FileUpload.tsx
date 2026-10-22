import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import { Upload, FileSpreadsheet, X } from 'lucide-react';
import { uploadFiles } from '../../services/api';
import { getFileSize } from '../../utils/helpers';
import type { DatasetInfo } from '../../types';

interface FileUploadProps {
  onUploadComplete: (datasets: DatasetInfo[]) => void;
}

export function FileUpload({ onUploadComplete }: FileUploadProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      setUploadError(null);

      if (rejectedFiles.length > 0) {
        const reasons = rejectedFiles.map((f: any) => {
          const errors = f.errors.map((e: any) => e.message).join(', ');
          return `${f.file.name}: ${errors}`;
        });
        setUploadError(reasons.join('\n'));
      }

      const csvFiles = acceptedFiles.filter((f) => {
        if (!f.name.toLowerCase().endsWith('.csv')) {
          setUploadError((prev) => (prev ? prev + '\n' : '') + `${f.name}: Not a CSV file`);
          return false;
        }
        if (f.size > 50 * 1024 * 1024) {
          setUploadError((prev) => (prev ? prev + '\n' : '') + `${f.name}: File exceeds 50MB limit`);
          return false;
        }
        if (f.size === 0) {
          setUploadError((prev) => (prev ? prev + '\n' : '') + `${f.name}: File is empty`);
          return false;
        }
        return true;
      });

      setSelectedFiles((prev) => [...prev, ...csvFiles]);
    },
    []
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'] },
    maxSize: 50 * 1024 * 1024,
  });

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      const datasets = await uploadFiles(selectedFiles);
      toast.success(`Successfully uploaded ${datasets.length} file${datasets.length > 1 ? 's' : ''}`);
      onUploadComplete(datasets);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Upload failed';
      setUploadError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      toast.error('Upload failed. Please check your files.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="modal-body">
      <div
        {...getRootProps()}
        className={`upload-zone ${isDragActive ? 'active' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="upload-zone-icon">
          <Upload size={40} style={{ color: isDragActive ? '#3b82f6' : '#64748b' }} />
        </div>
        <div className="upload-zone-text">
          {isDragActive
            ? 'Drop your CSV files here...'
            : 'Drag & drop CSV files here, or click to browse'}
        </div>
        <div className="upload-zone-hint">Supports .csv files up to 50MB each</div>
      </div>

      {selectedFiles.length > 0 && (
        <div className="upload-file-list">
          {selectedFiles.map((file, idx) => (
            <div key={idx} className="upload-file-item">
              <div className="upload-file-info">
                <FileSpreadsheet size={16} style={{ color: '#10b981' }} />
                <span className="upload-file-name">{file.name}</span>
                <span className="upload-file-size">{getFileSize(file.size)}</span>
              </div>
              <button
                className="btn-icon"
                onClick={() => removeFile(idx)}
                aria-label="Remove file"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {uploadError && (
        <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '0.5rem', fontSize: '0.8125rem', color: '#ef4444', whiteSpace: 'pre-wrap' }}>
          {uploadError}
        </div>
      )}

      {selectedFiles.length > 0 && (
        <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
          <button className="btn btn-secondary" onClick={() => setSelectedFiles([])}>
            Clear All
          </button>
          <button className="btn btn-primary" onClick={handleUpload} disabled={isUploading}>
            {isUploading ? (
              <>
                <span className="spinner" />
                Uploading...
              </>
            ) : (
              <>
                <Upload size={14} />
                Upload {selectedFiles.length} File{selectedFiles.length > 1 ? 's' : ''}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
