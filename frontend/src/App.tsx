import { VoiceCall } from './components/VoiceCall/VoiceCall'
import './App.scss'

function App() {
  // Get agent ID from environment variables
  const AGENT_ID = import.meta.env.VITE_ELEVENLABS_AGENT_ID || "your-agent-id-here";

  return (
    <div className="app">
      <header className="app-header">
        <h1>Voice AI Assistant</h1>
        <p>Connect with an AI agent through voice conversation</p>
      </header>
      
      <main className="app-main">
        <VoiceCall agentId={AGENT_ID} />
      </main>
      
      <footer className="app-footer">
        <p>Powered by ElevenLabs Conversational AI</p>
      </footer>
    </div>
  )
}

export default App
