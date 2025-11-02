import type { ConversationHistoryItem } from '../../types/call.types';
import './ConversationHistory.scss';

interface ConversationHistoryProps {
  conversations: ConversationHistoryItem[];
}

export function ConversationHistory({ conversations }: ConversationHistoryProps) {
  const formatDate = (date: Date) => {
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / 60000);
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes} min ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)} hour ago`;
    return date.toLocaleDateString();
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (conversations.length === 0) {
    return (
      <div className="conversation-history">
        <h3>Recent Conversations</h3>
        <div className="conversation-history__empty">
          <p>No conversations yet. Start your first voice call above!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="conversation-history">
      <h3>Recent Conversations</h3>
      <div className="conversation-history__list">
        {conversations.map((conversation) => (
          <div key={conversation.id} className="conversation-item">
            <div className="conversation-item__header">
              <div className="conversation-item__status">
                <div 
                  className={`status-dot ${
                    conversation.status === 'completed' ? 'status-dot--success' : 'status-dot--error'
                  }`}
                />
                <span className="conversation-item__time">
                  {formatDate(conversation.startedAt)}
                </span>
              </div>
              <div className="conversation-item__duration">
                {formatDuration(conversation.duration)}
              </div>
            </div>
            {conversation.transcript && (
              <div className="conversation-item__transcript">
                {conversation.transcript.substring(0, 100)}
                {conversation.transcript.length > 100 && '...'}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}