import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LeftSidebar } from '../components/LeftSidebar';
import { ChatWorkspace } from '../components/ChatWorkspace';
import { Button } from '../components/ui/button';
import { PanelLeftClose, PanelLeft } from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const MainAssistant = () => {
  const navigate = useNavigate();
  const [currentChatId, setCurrentChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [prefillPrompt, setPrefillPrompt] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem('ace_sidebar_collapsed');
    return saved === 'true';
  });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
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

  useEffect(() => {
    localStorage.setItem('ace_sidebar_collapsed', sidebarCollapsed.toString());
  }, [sidebarCollapsed]);

  // Close mobile menu when screen resizes to desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 768) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleNewChat = () => {
    setCurrentChatId(null);
    setMessages([]);
    setPrefillPrompt('');
    setMobileMenuOpen(false);
  };

  const handleSelectChat = async (chatId) => {
    try {
      const response = await axios.get(`${API}/chat/${chatId}`);
      setCurrentChatId(chatId);
      setMessages(response.data.messages || []);
      setPrefillPrompt('');
      setMobileMenuOpen(false);
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
    setMobileMenuOpen(false);
  };

  const toggleSidebar = () => {
    setSidebarCollapsed(prev => !prev);
  };

  const toggleMobileMenu = () => {
    setMobileMenuOpen(prev => !prev);
  };

  return (
    <div 
      className="flex h-screen overflow-hidden relative"
      data-testid="main-assistant"
    >
      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/30 z-40 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
          data-testid="mobile-overlay"
        />
      )}

      {/* Sidebar - Desktop: relative positioning, Mobile: fixed overlay */}
      <div 
        className={`
          hidden md:block flex-shrink-0
          ${sidebarCollapsed ? 'w-16' : 'w-64'}
          transition-all duration-300 ease-in-out
          h-full
        `}
      >
        <LeftSidebar
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          currentChatId={currentChatId}
          studentId={studentId}
          refreshTrigger={refreshTrigger}
          onInsightAction={handleInsightAction}
          collapsed={sidebarCollapsed}
          onToggleCollapse={toggleSidebar}
        />
      </div>

      {/* Mobile Sidebar - Fixed overlay */}
      <div 
        className={`
          md:hidden fixed inset-y-0 left-0 z-50
          w-64
          transform transition-transform duration-300 ease-in-out
          ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <LeftSidebar
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          currentChatId={currentChatId}
          studentId={studentId}
          refreshTrigger={refreshTrigger}
          onInsightAction={handleInsightAction}
          collapsed={false}
          onToggleCollapse={() => setMobileMenuOpen(false)}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 w-full">
        <ChatWorkspace
          chatId={currentChatId}
          studentId={studentId}
          onChatCreated={handleChatCreated}
          messages={messages}
          setMessages={setMessages}
          prefillPrompt={prefillPrompt}
          clearPrefill={() => setPrefillPrompt('')}
          sidebarCollapsed={sidebarCollapsed}
          onToggleSidebar={toggleSidebar}
          onToggleMobileMenu={toggleMobileMenu}
        />
      </div>
    </div>
  );
};

export default MainAssistant;
