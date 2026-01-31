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
  };

  const handleSelectChat = async (chatId) => {
    try {
      const response = await axios.get(`${API}/chat/${chatId}`);
      setCurrentChatId(chatId);
      setMessages(response.data.messages || []);
    } catch (error) {
      console.error('Error loading chat:', error);
    }
  };

  const handleChatCreated = (newChatId) => {
    setCurrentChatId(newChatId);
    // Trigger sidebar refresh to show new chat
    setRefreshTrigger(prev => prev + 1);
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
      />
      <ChatWorkspace
        chatId={currentChatId}
        studentId={studentId}
        onChatCreated={handleChatCreated}
        messages={messages}
        setMessages={setMessages}
      />
    </div>
  );
};

export default MainAssistant;
