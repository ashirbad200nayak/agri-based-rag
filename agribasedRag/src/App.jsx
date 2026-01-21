import { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import ChatInput from './components/ChatInput';
import { sendMessage } from './api/chatService';
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your AI assistant. How can I help you today?' }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState("All");

  const handleSend = async (text) => {
    const userMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    try {
      const response = await sendMessage(text, selectedRegion);
      setMessages((prev) => [...prev, response]);
    } catch (error) {
      console.error("Error sending message:", error);
      setMessages((prev) => [...prev, { role: 'assistant', content: "Sorry, something went wrong." }]);
    } finally {
      setIsTyping(false);
    }
  };

  const startNewChat = () => {
    setMessages([
        { role: 'assistant', content: 'Starting a new conversation. How can I help?' }
    ]);
  };

  return (
    <div className="app-container">
      <Sidebar onNewChat={startNewChat} selectedRegion={selectedRegion} onRegionChange={setSelectedRegion} />
      <main className="chat-area">
        <ChatArea messages={messages} />
        {isTyping && (
             <div className="message-row ai">
                <div className="avatar ai">AI</div>
                <div className="text-content">Typing...</div>
             </div>
        )}
        <ChatInput onSend={handleSend} disabled={isTyping} />
      </main>
    </div>
  );
}

export default App;
