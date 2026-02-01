import { useState, useEffect } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Checkbox } from './ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog';
import { 
  Settings, 
  MessageSquare, 
  Plus, 
  Trash2,
  ChevronRight,
  Calendar,
  GraduationCap,
  Users,
  Clock,
  LayoutGrid,
  Sliders,
  BookOpen,
  TrendingUp
} from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Available tools for Quick Access
const AVAILABLE_TOOLS = [
  { 
    id: 'weekly-calendar', 
    label: 'Weekly Calendar', 
    icon: Calendar,
    action: 'chat',
    prompt: "Show me what's on my schedule this week and any upcoming deadlines."
  },
  { 
    id: 'schedule-builder', 
    label: 'Schedule Builder', 
    icon: LayoutGrid,
    action: 'chat',
    prompt: "Help me plan my course schedule for next semester."
  },
  { 
    id: 'degree-progress', 
    label: 'Degree Progress', 
    icon: TrendingUp,
    action: 'chat',
    prompt: "What requirements do I still need to complete for my degree?"
  },
  { 
    id: 'advising-portal', 
    label: 'Advising Portal', 
    icon: Users,
    action: 'stub',
    stubTitle: 'Advising Portal',
    stubContent: 'Connect with your academic advisor through Starfish.'
  },
  { 
    id: 'check-deadlines', 
    label: 'Check Deadlines', 
    icon: Clock,
    action: 'chat',
    prompt: "What are the important academic deadlines I should know about this semester?"
  },
  { 
    id: 'course-catalog', 
    label: 'Course Catalog', 
    icon: BookOpen,
    action: 'stub',
    stubTitle: 'Course Catalog',
    stubContent: 'Browse available courses in LionPATH.'
  }
];

const DEFAULT_TOOLS = ['weekly-calendar', 'degree-progress', 'check-deadlines'];

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
  const [selectedTools, setSelectedTools] = useState(() => {
    const saved = localStorage.getItem('ace_quick_tools');
    return saved ? JSON.parse(saved) : DEFAULT_TOOLS;
  });
  const [customizeOpen, setCustomizeOpen] = useState(false);
  const [tempSelectedTools, setTempSelectedTools] = useState(selectedTools);
  const [stubModal, setStubModal] = useState(null);

  useEffect(() => {
    fetchData();
  }, [studentId, refreshTrigger]);

  useEffect(() => {
    localStorage.setItem('ace_quick_tools', JSON.stringify(selectedTools));
  }, [selectedTools]);

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

  const handleToolClick = (tool) => {
    if (tool.action === 'chat' && onInsightAction) {
      onInsightAction(tool.prompt);
    } else if (tool.action === 'stub') {
      setStubModal({ title: tool.stubTitle, content: tool.stubContent });
    }
  };

  const handleToolToggle = (toolId) => {
    setTempSelectedTools(prev => {
      if (prev.includes(toolId)) {
        return prev.filter(id => id !== toolId);
      } else if (prev.length < 3) {
        return [...prev, toolId];
      }
      return prev;
    });
  };

  const handleSaveTools = () => {
    setSelectedTools(tempSelectedTools);
    setCustomizeOpen(false);
  };

  const handleOpenCustomize = () => {
    setTempSelectedTools(selectedTools);
    setCustomizeOpen(true);
  };

  const getUrgencyStyle = (urgency) => {
    switch (urgency) {
      case 'high': return 'border-l-red-400 bg-red-50/50';
      case 'medium': return 'border-l-amber-400 bg-amber-50/50';
      default: return 'border-l-[#96BEE6] bg-[#F8FAFC]';
    }
  };

  const activeTools = selectedTools
    .map(id => AVAILABLE_TOOLS.find(t => t.id === id))
    .filter(Boolean);

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

      {/* Quick Access Panel */}
      <div className="px-4 pt-4 pb-3 border-b border-[#E2E8F0]">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-medium text-[#475569] uppercase tracking-wider">
            Quick Access
          </p>
          <Dialog open={customizeOpen} onOpenChange={setCustomizeOpen}>
            <DialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleOpenCustomize}
                className="h-6 px-2 text-[10px] text-[#94A3B8] hover:text-[#475569] hover:bg-[#F1F5F9] gap-1"
                data-testid="customize-tools-button"
              >
                <Sliders className="w-3 h-3" />
                Customize
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md" data-testid="customize-tools-modal">
              <DialogHeader>
                <DialogTitle className="font-heading text-lg text-[#001E44]">
                  Customize Quick Access
                </DialogTitle>
              </DialogHeader>
              <div className="py-4">
                <p className="text-sm text-[#475569] mb-4">
                  Select up to 3 tools for quick access:
                </p>
                <div className="space-y-2">
                  {AVAILABLE_TOOLS.map(tool => {
                    const IconComponent = tool.icon;
                    const isSelected = tempSelectedTools.includes(tool.id);
                    const isDisabled = !isSelected && tempSelectedTools.length >= 3;
                    
                    return (
                      <label
                        key={tool.id}
                        className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                          isSelected 
                            ? 'border-[#96BEE6] bg-[#96BEE6]/10' 
                            : isDisabled
                              ? 'border-[#E2E8F0] bg-[#F8FAFC] opacity-50 cursor-not-allowed'
                              : 'border-[#E2E8F0] hover:border-[#96BEE6]/50 hover:bg-[#F8FAFC]'
                        }`}
                        data-testid={`tool-option-${tool.id}`}
                      >
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={() => !isDisabled && handleToolToggle(tool.id)}
                          disabled={isDisabled}
                          className="data-[state=checked]:bg-[#001E44] data-[state=checked]:border-[#001E44]"
                        />
                        <IconComponent className="w-4 h-4 text-[#1E407C]" />
                        <span className="text-sm text-[#0F172A]">{tool.label}</span>
                      </label>
                    );
                  })}
                </div>
                <p className="text-xs text-[#94A3B8] mt-3">
                  {tempSelectedTools.length}/3 tools selected
                </p>
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setCustomizeOpen(false)}
                  className="border-[#E2E8F0]"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSaveTools}
                  className="bg-[#001E44] hover:bg-[#1E407C]"
                  data-testid="save-tools-button"
                >
                  Save
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
        
        {/* Tool Rows */}
        <div className="space-y-1" data-testid="quick-access-tools">
          {activeTools.map(tool => {
            const IconComponent = tool.icon;
            return (
              <button
                key={tool.id}
                onClick={() => handleToolClick(tool)}
                className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left hover:bg-[#F1F5F9] transition-colors group"
                data-testid={`quick-tool-${tool.id}`}
              >
                <div className="w-7 h-7 rounded-md bg-[#F1F5F9] group-hover:bg-[#96BEE6]/20 flex items-center justify-center transition-colors">
                  <IconComponent className="w-4 h-4 text-[#1E407C]" />
                </div>
                <span className="text-sm text-[#0F172A]">{tool.label}</span>
                <ChevronRight className="w-3.5 h-3.5 text-[#94A3B8] ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            );
          })}
        </div>
      </div>

      {/* Stub Modal for non-chat tools */}
      <Dialog open={!!stubModal} onOpenChange={() => setStubModal(null)}>
        <DialogContent className="sm:max-w-sm" data-testid="stub-modal">
          <DialogHeader>
            <DialogTitle className="font-heading text-lg text-[#001E44]">
              {stubModal?.title}
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-[#475569]">{stubModal?.content}</p>
            <div className="mt-4 p-4 bg-[#F8FAFC] rounded-lg border border-[#E2E8F0]">
              <p className="text-xs text-[#94A3B8] text-center">
                This feature links to external Penn State systems
              </p>
            </div>
          </div>
          <div className="flex justify-end">
            <Button
              onClick={() => setStubModal(null)}
              className="bg-[#001E44] hover:bg-[#1E407C]"
            >
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>

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
