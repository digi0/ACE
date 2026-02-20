import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LeftSidebar } from '../components/LeftSidebar';
import { ChatWorkspace } from '../components/ChatWorkspace';
import { Button } from '../components/ui/button';
import { PanelLeftClose, PanelLeft } from 'lucide-react';
import api, { isAuthenticated } from '../utils/api';

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
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetchUser();
  }, []);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, { withCredentials: true });
      setUser(response.data);
      
      if (!response.data.profile_complete) {
        navigate('/onboarding');
      }
    } catch (err) {
      navigate('/login');
    }
  };

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

      {/* Mobile Sidebar - Fixed overlay (only on mobile) */}
      <div 
        className={`
          md:hidden fixed inset-y-0 left-0 z-50
          w-72
          transform transition-transform duration-300 ease-in-out
          ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <LeftSidebar
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          currentChatId={currentChatId}
          refreshTrigger={refreshTrigger}
          onInsightAction={handleInsightAction}
          collapsed={false}
          onToggleCollapse={() => setMobileMenuOpen(false)}
          isMobile={true}
          user={user}
        />
      </div>

      {/* Desktop Sidebar - Static in flex layout */}
      <div 
        className={`
          hidden md:flex flex-shrink-0
          ${sidebarCollapsed ? 'w-16' : 'w-72'}
          transition-all duration-300 ease-in-out
        `}
      >
        <LeftSidebar
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          currentChatId={currentChatId}
          refreshTrigger={refreshTrigger}
          onInsightAction={handleInsightAction}
          collapsed={sidebarCollapsed}
          onToggleCollapse={toggleSidebar}
          isMobile={false}
          user={user}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        <ChatWorkspace
          chatId={currentChatId}
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
