import { useState, useEffect } from 'react';
import { useConversation } from '@elevenlabs/react';
import type { VoiceCallProps, ConversationHistoryItem } from '../../types/call.types';
import { useCallTimer } from '../../hooks/useCallTimer';
import { requestMicrophonePermission, checkMicrophoneSupport } from '../../utils/permissions';
import { ConversationHistory } from './ConversationHistory';
import './VoiceCall.scss';

export function VoiceCall({ agentId }: VoiceCallProps) {
  const [error, setError] = useState<string | null>(null);
  const [isPermissionGranted, setIsPermissionGranted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [conversations, setConversations] = useState<ConversationHistoryItem[]>([]);

  const conversation = useConversation({
    onConnect: () => {
      setError(null);
      setIsLoading(false);
      console.log('Connected to agent');
    },
    onDisconnect: () => {
      setIsLoading(false);
      console.log('Disconnected from agent');
      
      // Add completed conversation to history (mock data for now)
      const newConversation: ConversationHistoryItem = {
        id: Date.now().toString(),
        agentId,
        startedAt: new Date(Date.now() - duration * 1000),
        endedAt: new Date(),
        duration,
        status: 'completed',
      };
      
      setConversations(prev => [newConversation, ...prev.slice(0, 4)]);
    },
    onError: (error) => {
      setError(typeof error === 'string' ? error : 'An error occurred during the call');
      setIsLoading(false);
      console.error('Conversation error:', error);
    }
  });

  const { duration, formattedDuration } = useCallTimer(conversation.status === 'connected');

  useEffect(() => {
    // Check if microphone is supported
    if (!checkMicrophoneSupport()) {
      setError('Microphone is not supported in this browser');
    }
  }, []);

  const handleStartCall = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Request microphone permission if not already granted
      if (!isPermissionGranted) {
        const hasPermission = await requestMicrophonePermission();
        if (!hasPermission) {
          setError('Microphone permission is required for voice calls');
          setIsLoading(false);
          return;
        }
        setIsPermissionGranted(true);
      }

      // Start the conversation
      await conversation.startSession({
        agentId,
        connectionType: 'webrtc',
        dynamicVariables: {
          user: 'John Pork',
          event_name: 'Durhack',
          event_description: 'a university hackathon focused on innovative tech solutions',
        }
      });
    } catch (err) {
      setError('Failed to start call. Please try again.');
      setIsLoading(false);
      console.error('Failed to start call:', err);
    }
  };

  const handleEndCall = async () => {
    try {
      await conversation.endSession();
    } catch (err) {
      console.error('Failed to end call:', err);
    }
  };

  const getStatusColor = (): string => {
    switch (conversation.status) {
      case 'connected': return 'green';
      case 'connecting': return 'orange';
      default: return 'gray';
    }
  };

  const getStatusText = (): string => {
    if (isLoading) return 'Connecting...';
    
    switch (conversation.status) {
      case 'connected': return 'Connected';
      case 'connecting': return 'Connecting...';
      default: return 'Disconnected';
    }
  };

  const isCallActive = conversation.status === 'connected';
  const isConnecting = conversation.status === 'connecting' || isLoading;

  return (
    <div className="voice-call">
      <div className="voice-call__header">
        <h2>Voice Agent</h2>
        <div className="voice-call__status">
          <div className={`status-indicator status-indicator--${getStatusColor()}`} />
          <span className="status-text">{getStatusText()}</span>
        </div>
      </div>

      <div className="voice-call__main">
        <div className="call-controls">
          {!isCallActive && !isConnecting && (
            <button 
              className="call-button call-button--start"
              onClick={handleStartCall}
              disabled={isLoading}
            >
              <span className="call-button__icon">🎙️</span>
              <span className="call-button__text">Start Voice Call</span>
            </button>
          )}

          {(isCallActive || isConnecting) && (
            <button 
              className="call-button call-button--end"
              onClick={handleEndCall}
              disabled={isConnecting}
            >
              <span className="call-button__icon">📞</span>
              <span className="call-button__text">
                {isConnecting ? 'Connecting...' : 'End Call'}
              </span>
            </button>
          )}
        </div>

        {isCallActive && (
          <div className="call-info">
            <div className="call-duration">
              <span className="call-duration__label">Duration:</span>
              <span className="call-duration__time">{formattedDuration}</span>
            </div>
          </div>
        )}

        {error && (
          <div className="error-message">
            <span className="error-message__icon">⚠️</span>
            <span className="error-message__text">{error}</span>
            <button 
              className="error-message__dismiss"
              onClick={() => setError(null)}
            >
              ×
            </button>
          </div>
        )}
      </div>

      <ConversationHistory conversations={conversations} />

      <div className="voice-call__footer">
        <p className="voice-call__help">
          Click "Start Voice Call" to begin talking with the AI agent. 
          Make sure your microphone is enabled.
        </p>
      </div>
    </div>
  );
}
