import { Menu, MessageSquarePlus } from 'lucide-react';

interface HeaderProps {
  onNewChat: () => void;
  onToggleSidebar: () => void;
  hasMessages: boolean;
}

export function Header({ onNewChat, onToggleSidebar, hasMessages }: HeaderProps) {
  return (
    <header className="app-header">
      <div className="header-left">
        <button className="btn-icon" onClick={onToggleSidebar} aria-label="Toggle sidebar">
          <Menu size={18} />
        </button>
        <div className="header-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
          </svg>
          InsightFlow AI
        </div>
      </div>
      <div className="header-actions">
        {hasMessages && (
          <button className="btn btn-secondary" onClick={onNewChat}>
            <MessageSquarePlus size={14} />
            New Chat
          </button>
        )}
      </div>
    </header>
  );
}
