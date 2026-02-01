import { useState, useEffect } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { 
  Settings, 
  MessageSquare, 
  Plus, 
  Trash2,
  ChevronRight
} from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const LeftSidebar = ({ 
  onNewChat, 
  onSelectChat, 
  currentChatId, 
  studentId,
  refreshTrigger,
  onInsightAction
}) => {
  const [profile, setProfile] = useState(null);
  const [intelligence, setIntelligence] = useState(null);
  const [chatSessions, setChatSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [studentId, refreshTrigger]);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [profileRes, intelligenceRes, chatsRes] = await Promise.all([
        axios.get(`${API}/student/profile`),
        axios.get(`${API}/student/intelligence`),
        axios.get(`${API}/chats/${studentId}`)
      ]);
      setProfile(profileRes.data);
      setIntelligence(intelligenceRes.data);
      setChatSessions(chatsRes.data);
    } catch (error) {
      console.error('Error fetching sidebar data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteChat = async (e, chatId) => {
    e.stopPropagation();
    try {
      await axios.delete(`${API}/chat/${chatId}`);
      setChatSessions(prev => prev.filter(c => c.id !== chatId));
      if (currentChatId === chatId) {
        onNewChat();
      }
    } catch (error) {
      console.error('Error deleting chat:', error);
    }
  };

  const handleInsightAction = () => {
    if (intelligence?.action && onInsightAction) {
      onInsightAction(intelligence.action.prompt);
    }
  };

  const getUrgencyStyle = (urgency) => {
    switch (urgency) {
      case 'high': return 'border-l-red-400 bg-red-50/50';
      case 'medium': return 'border-l-amber-400 bg-amber-50/50';
      default: return 'border-l-[#96BEE6] bg-[#F8FAFC]';
    }
  };

  return (
    <aside 
      className="w-80 h-screen bg-white border-r border-[#E2E8F0] flex flex-col"
      data-testid="left-sidebar"
    >
      {/* Profile Block */}
      <div className="p-4 border-b border-[#E2E8F0]">
        {profile ? (
          <div className="flex items-center gap-3" data-testid="profile-block">
            <Avatar className="h-11 w-11 border-2 border-[#96BEE6]/30">
              <AvatarImage src="https://images.unsplash.com/photo-1745558858213-c1bb66fc8fde?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NTJ8MHwxfHNlYXJjaHwyfHx1bml2ZXJzaXR5JTIwY2FtcHVzJTIwbGlicmFyeSUyMHN0dWRlbnRzfGVufDB8fHx8MTc2OTg2MzY5MHww&ixlib=rb-4.1.0&q=85&w=100" />
              <AvatarFallback className="bg-[#001E44] text-white font-medium">
                {profile.name?.split(' ').map(n => n[0]).join('')}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-[#0F172A] text-sm truncate" data-testid="student-name">
                {profile.name}
              </p>
              <p className="text-xs text-[#475569]" data-testid="student-id">
                {profile.psu_id}
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-[#475569] hover:bg-[#F1F5F9]"
              data-testid="settings-button"
            >
              <Settings className="w-4 h-4" />
            </Button>
          </div>
        ) : (
          <div className="animate-pulse flex items-center gap-3">
            <div className="h-11 w-11 rounded-full bg-[#E2E8F0]" />
            <div className="flex-1">
              <div className="h-4 bg-[#E2E8F0] rounded w-24 mb-1" />
              <div className="h-3 bg-[#E2E8F0] rounded w-16" />
            </div>
          </div>
        )}
      </div>

      {/* Intelligence Card - Dynamic */}
      {intelligence && (
        <div className="p-4 border-b border-[#E2E8F0]">
          <Card 
            className={`border-0 border-l-[3px] shadow-none ${getUrgencyStyle(intelligence.urgency)}`}
            data-testid="intelligence-card"
          >
            <CardContent className="p-3">
              {/* Context Line */}
              <p className="text-[10px] uppercase tracking-wider text-[#94A3B8] mb-1.5" data-testid="intelligence-context">
                {intelligence.context?.term} · {intelligence.context?.level} · {intelligence.context?.status}
              </p>
              
              {/* Single Insight */}
              <p className="text-sm text-[#0F172A] leading-relaxed" data-testid="intelligence-insight">
                {intelligence.insight}
              </p>
              
              {/* Soft Action Button (optional) */}
              {intelligence.action && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleInsightAction}
                  className="mt-2.5 h-7 px-0 text-xs text-[#1E407C] hover:text-[#001E44] hover:bg-transparent font-medium gap-1"
                  data-testid="intelligence-action-button"
                >
                  {intelligence.action.label}
                  <ChevronRight className="w-3.5 h-3.5" />
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* New Chat Button */}
      <div className="p-4">
        <Button
          onClick={onNewChat}
          className="w-full bg-[#001E44] hover:bg-[#1E407C] text-white gap-2 h-10"
          data-testid="new-chat-button"
        >
          <Plus className="w-4 h-4" />
          New conversation
        </Button>
      </div>

      {/* Chat History */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="px-4 py-2">
          <p className="text-xs font-medium text-[#475569] uppercase tracking-wider">
            Previous chats
          </p>
        </div>
        <ScrollArea className="flex-1 px-2">
          <div className="space-y-1 pb-4" data-testid="chat-history">
            {isLoading ? (
              <div className="space-y-2 px-2">
                {[1, 2, 3].map(i => (
                  <div key={i} className="animate-pulse h-10 bg-[#E2E8F0] rounded-lg" />
                ))}
              </div>
            ) : chatSessions.length > 0 ? (
              chatSessions.map(session => (
                <div
                  key={session.id}
                  onClick={() => onSelectChat(session.id)}
                  className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-150 ${
                    currentChatId === session.id 
                      ? 'bg-[#96BEE6]/20 text-[#001E44]' 
                      : 'hover:bg-[#F1F5F9] text-[#475569]'
                  }`}
                  data-testid={`chat-item-${session.id}`}
                >
                  <MessageSquare className="w-4 h-4 flex-shrink-0 opacity-60" />
                  <span className="flex-1 text-sm truncate">{session.title}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => handleDeleteChat(e, session.id)}
                    data-testid={`delete-chat-${session.id}`}
                  >
                    <Trash2 className="w-3 h-3 text-[#94A3B8] hover:text-red-500" />
                  </Button>
                </div>
              ))
            ) : (
              <p className="px-4 py-6 text-sm text-[#94A3B8] text-center">
                No previous conversations
              </p>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-[#E2E8F0]">
        <p className="text-xs text-[#94A3B8] text-center">
          ACE · Penn State Academic Support
        </p>
      </div>
    </aside>
  );
};

export default LeftSidebar;
