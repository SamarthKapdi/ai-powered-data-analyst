import { useState, useCallback } from 'react';
import { Toaster } from 'react-hot-toast';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { ChatPanel } from './components/chat/ChatPanel';
import { DataPreviewPanel } from './components/upload/DataPreviewPanel';
import { FileUpload } from './components/upload/FileUpload';
import { InsightsPanel } from './components/insights/InsightsPanel';
import { WelcomeScreen } from './components/layout/WelcomeScreen';
import type { DatasetInfo, ChatMessage } from './types';
import './App.css';

function App() {
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [activeDatasetId, setActiveDatasetId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [showUpload, setShowUpload] = useState(false);
  const [rightPanel, setRightPanel] = useState<'preview' | 'insights'>('preview');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const activeDataset = datasets.find((d) => d.id === activeDatasetId) || null;

  const handleDatasetsUploaded = useCallback((newDatasets: DatasetInfo[]) => {
    setDatasets((prev) => [...prev, ...newDatasets]);
    if (newDatasets.length > 0) {
      setActiveDatasetId(newDatasets[0].id);
    }
    setShowUpload(false);
  }, []);

  const handleRemoveDataset = useCallback(
    (datasetId: string) => {
      setDatasets((prev) => prev.filter((d) => d.id !== datasetId));
      if (activeDatasetId === datasetId) {
        setActiveDatasetId(datasets.find((d) => d.id !== datasetId)?.id || null);
      }
    },
    [activeDatasetId, datasets]
  );

  const handleNewChat = useCallback(() => {
    setMessages([]);
  }, []);

  const hasDatasets = datasets.length > 0;

  return (
    <div className="app-container">
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155' },
        }}
      />

      <Header
        onNewChat={handleNewChat}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        hasMessages={messages.length > 0}
      />

      <div className="main-layout">
        {sidebarOpen && (
          <Sidebar
            datasets={datasets}
            activeDatasetId={activeDatasetId}
            onSelectDataset={setActiveDatasetId}
            onRemoveDataset={handleRemoveDataset}
            onUploadClick={() => setShowUpload(true)}
          />
        )}

        <main className="content-area">
          {!hasDatasets && !showUpload ? (
            <WelcomeScreen onUploadClick={() => setShowUpload(true)} />
          ) : (
            <div className="workspace">
              <div className="chat-section">
                <ChatPanel
                  messages={messages}
                  setMessages={setMessages}
                  datasets={datasets}
                  activeDatasetId={activeDatasetId}
                />
              </div>

              {hasDatasets && activeDataset && (
                <div className="right-panel">
                  <div className="panel-tabs">
                    <button
                      className={`panel-tab ${rightPanel === 'preview' ? 'active' : ''}`}
                      onClick={() => setRightPanel('preview')}
                    >
                      Data Preview
                    </button>
                    <button
                      className={`panel-tab ${rightPanel === 'insights' ? 'active' : ''}`}
                      onClick={() => setRightPanel('insights')}
                    >
                      Insights
                    </button>
                  </div>

                  {rightPanel === 'preview' ? (
                    <DataPreviewPanel dataset={activeDataset} />
                  ) : (
                    <InsightsPanel datasetId={activeDataset.id} />
                  )}
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {showUpload && (
        <div className="modal-overlay" onClick={() => setShowUpload(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Upload CSV Files</h2>
              <button className="modal-close" onClick={() => setShowUpload(false)}>
                ✕
              </button>
            </div>
            <FileUpload onUploadComplete={handleDatasetsUploaded} />
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
