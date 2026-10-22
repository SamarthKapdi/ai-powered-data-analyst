import { useState, useRef, useEffect, useCallback } from 'react';
import { Send } from 'lucide-react';
import toast from 'react-hot-toast';
import { analyzeData, buildConversationHistory } from '../../services/api';
import { generateId } from '../../utils/helpers';
import { MessageBubble } from './MessageBubble';
import type { ChatMessage, DatasetInfo } from '../../types';

interface ChatPanelProps {
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  datasets: DatasetInfo[];
  activeDatasetId: string | null;
}

const SUGGESTIONS = [
  'Which region generated the highest revenue?',
  'Show monthly sales trends',
  'What are the top 5 products by revenue?',
  'Detect anomalies in the dataset',
  'Show revenue distribution by category',
  'Compare quantity sold across regions',
  'Generate SQL for total revenue by product',
  'What is the average order value?',
];

export function ChatPanel({ messages, setMessages, datasets, activeDatasetId }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;
    if (datasets.length === 0) {
      toast.error('Please upload a CSV file first');
      return;
    }

    const userMsg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };

    const loadingMsg: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const datasetIds = activeDatasetId ? [activeDatasetId] : datasets.map((d) => d.id);
      const history = buildConversationHistory([...messages, userMsg]);
      const response = await analyzeData(text.trim(), datasetIds, history);

      const assistantMsg: ChatMessage = {
        id: loadingMsg.id,
        role: 'assistant',
        content: response.answer || response.error || 'Analysis complete.',
        timestamp: new Date(),
        analysis: response,
      };

      setMessages((prev) => prev.map((m) => (m.id === loadingMsg.id ? assistantMsg : m)));
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Analysis failed';
      const assistantMsg: ChatMessage = {
        id: loadingMsg.id,
        role: 'assistant',
        content: typeof errorMsg === 'string' ? `Sorry, an error occurred: ${errorMsg}` : 'Sorry, an error occurred during analysis.',
        timestamp: new Date(),
      };
      setMessages((prev) => prev.map((m) => (m.id === loadingMsg.id ? assistantMsg : m)));
      toast.error('Analysis failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion);
  };

  const hasDatasets = datasets.length > 0;

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            {hasDatasets ? (
              <>
                <h3>Ask a question about your data</h3>
                <p>
                  Try asking about revenue, trends, top performers, anomalies, or request
                  SQL/Pandas code for your analysis.
                </p>
                <div className="suggestions-grid">
                  {SUGGESTIONS.map((s, i) => (
                    <button
                      key={i}
                      className="suggestion-card"
                      onClick={() => handleSuggestionClick(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <>
                <h3>Upload a dataset to get started</h3>
                <p>Click the upload button in the sidebar to add your CSV files.</p>
              </>
            )}
          </div>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-wrapper">
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              hasDatasets
                ? 'Ask a question about your data...'
                : 'Upload a CSV file to start analyzing...'
            }
            disabled={!hasDatasets || isLoading}
            rows={1}
          />
          <button
            className="send-btn"
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isLoading || !hasDatasets}
            aria-label="Send message"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
