export type CallStatus = 'disconnected' | 'connecting' | 'connected' | 'ended' | 'error';

export interface CallState {
  status: CallStatus;
  conversationId: string | null;
  duration: number;
  error: string | null;
  agentId: string;
}

export interface ConversationHistoryItem {
  id: string;
  agentId: string;
  startedAt: Date;
  endedAt: Date | null;
  duration: number;
  status: 'completed' | 'failed';
  transcript?: string;
}

export interface VoiceCallProps {
  agentId: string;
}