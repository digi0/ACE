import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LeftSidebar } from '../components/LeftSidebar';
import { ChatWorkspace } from '../components/ChatWorkspace';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const MainAssistant = () => {
  const navigate = useNavigate();
  const [currentChatId, setCurrentChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [prefillPrompt, setPrefillPrompt] = useState('');
  
  // Get student ID from localStorage (set during mocked login)
  const studentId = localStorage.getItem('ace_student_id') || 'abc123456';

  useEffect(() => {
    // Check if authenticated
    const isAuthenticated = localStorage.getItem('ace_authenticated');
    if (!isAuthenticated) {
      navigate('/');
      return;
    }
  }, [navigate]);

  const handleNewChat = () => {
    setCurrentChatId(null);
    setMessages([]);
    setPrefillPrompt('');
  };

  const handleSelectChat = async (chatId) => {
    try {
      const response = await axios.get(`${API}/chat/${chatId}`);
      setCurrentChatId(chatId);
      setMessages(response.data.messages || []);
      setPrefillPrompt('');
    } catch (error) {
      console.error('Error loading chat:', error);
    }
  };

  const handleChatCreated = (newChatId) => {
    setCurrentChatId(newChatId);
    // Trigger sidebar refresh to show new chat
    setRefreshTrigger(prev => prev + 1);
  };

  const handleInsightAction = (prompt) => {
    // Start new chat with pre-filled prompt from intelligence card
    setCurrentChatId(null);
    setMessages([]);
    setPrefillPrompt(prompt);
  };

  return (
    <div 
      className="flex h-screen overflow-hidden"
      data-testid="main-assistant"
    >
      <LeftSidebar
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        currentChatId={currentChatId}
        studentId={studentId}
        refreshTrigger={refreshTrigger}
        onInsightAction={handleInsightAction}
      />
      <ChatWorkspace
        chatId={currentChatId}
        studentId={studentId}
        onChatCreated={handleChatCreated}
        messages={messages}
        setMessages={setMessages}
        prefillPrompt={prefillPrompt}
        clearPrefill={() => setPrefillPrompt('')}
      />
    </div>
  );
};

export default MainAssistant;
