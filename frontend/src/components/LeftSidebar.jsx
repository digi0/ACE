import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';
import { 
  Settings, 
  MessageSquare, 
  Plus, 
  Trash2,
  ChevronRight,
  ChevronLeft,
  Calendar,
  GraduationCap,
  Users,
  Clock,
  LayoutGrid,
  Sliders,
  BookOpen,
  TrendingUp,
  PanelLeftClose,
  PanelLeft,
  LogOut,
  Shield
} from 'lucide-react';
import api, { clearAuth } from '../utils/api';

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
  refreshTrigger,
  onInsightAction,
  collapsed,
  onToggleCollapse,
  isMobile = false,
  user
}) => {
  const navigate = useNavigate();
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

  const testIdPrefix = isMobile ? 'mobile-' : 'desktop-';

  useEffect(() => {
    fetchData();
  }, [refreshTrigger]);

  useEffect(() => {
    localStorage.setItem('ace_quick_tools', JSON.stringify(selectedTools));
  }, [selectedTools]);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [profileRes, intelligenceRes, chatsRes] = await Promise.all([
        api.get('/user/profile'),
        api.get('/student/intelligence'),
        api.get('/chats')
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

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    }
    clearAuth();
    navigate('/login');
  };

  const handleDeleteChat = async (e, chatId) => {
    e.stopPropagation();
    try {
      await api.delete(`/chat/${chatId}`);
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

  // Collapsed view
  if (collapsed) {
    return (
      <TooltipProvider delayDuration={100}>
        <aside 
          className="w-16 h-screen bg-white border-r border-[#E2E8F0] flex flex-col items-center py-3"
          data-testid={`${testIdPrefix}sidebar-collapsed`}
        >
          {/* Expand button */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={onToggleCollapse}
                className="h-9 w-9 mb-3 text-[#475569] hover:bg-[#F1F5F9]"
                data-testid={`${testIdPrefix}expand-sidebar-button`}
              >
                <PanelLeft className="w-5 h-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">Expand sidebar</TooltipContent>
          </Tooltip>

          {/* Profile avatar */}
          {profile && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Avatar className="h-9 w-9 border-2 border-[#96BEE6]/30 mb-4 cursor-pointer">
                  <AvatarImage src="https://images.unsplash.com/photo-1745558858213-c1bb66fc8fde?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NTJ8MHwxfHNlYXJjaHwyfHx1bml2ZXJzaXR5JTIwY2FtcHVzJTIwbGlicmFyeSUyMHN0dWRlbnRzfGVufDB8fHx8MTc2OTg2MzY5MHww&ixlib=rb-4.1.0&q=85&w=100" />
                  <AvatarFallback className="bg-[#001E44] text-white text-xs font-medium">
                    {profile.name?.split(' ').map(n => n[0]).join('')}
                  </AvatarFallback>
                </Avatar>
              </TooltipTrigger>
              <TooltipContent side="right">{profile.name}</TooltipContent>
            </Tooltip>
          )}

          {/* New chat button */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                onClick={onNewChat}
                size="icon"
                className="h-9 w-9 bg-[#001E44] hover:bg-[#1E407C] text-white mb-4"
                data-testid={`${testIdPrefix}new-chat-button-collapsed`}
              >
                <Plus className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">New conversation</TooltipContent>
          </Tooltip>

          {/* Quick tools */}
          <div className="space-y-2 mb-4">
            {activeTools.slice(0, 3).map(tool => {
              const IconComponent = tool.icon;
              return (
                <Tooltip key={tool.id}>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleToolClick(tool)}
                      className="h-9 w-9 text-[#475569] hover:bg-[#F1F5F9]"
                      data-testid={`${testIdPrefix}quick-tool-collapsed-${tool.id}`}
                    >
                      <IconComponent className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">{tool.label}</TooltipContent>
                </Tooltip>
              );
            })}
          </div>

          {/* Divider */}
          <div className="w-8 h-px bg-[#E2E8F0] my-2" />

          {/* Recent chats (just icons) */}
          <ScrollArea className="flex-1 w-full">
            <div className="flex flex-col items-center space-y-1 px-2">
              {chatSessions.slice(0, 5).map(session => (
                <Tooltip key={session.id}>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onSelectChat(session.id)}
                      className={`h-9 w-9 ${
                        currentChatId === session.id 
                          ? 'bg-[#96BEE6]/20 text-[#001E44]' 
                          : 'text-[#475569] hover:bg-[#F1F5F9]'
                      }`}
                      data-testid={`${testIdPrefix}chat-collapsed-${session.id}`}
                    >
                      <MessageSquare className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">{session.title}</TooltipContent>
                </Tooltip>
              ))}
            </div>
          </ScrollArea>

          {/* ACE logo */}
          <div className="mt-auto pt-3">
            <div className="w-8 h-8 bg-[#001E44] rounded-lg flex items-center justify-center">
              <GraduationCap className="w-4 h-4 text-white" />
            </div>
          </div>
        </aside>

        {/* Stub Modal */}
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
      </TooltipProvider>
    );
  }

  // Expanded view
  return (
    <aside 
      className="w-full h-screen bg-white border-r border-[#E2E8F0] flex flex-col"
      data-testid={`${testIdPrefix}sidebar`}
    >
      {/* Header with collapse button */}
      <div className="p-3 border-b border-[#E2E8F0] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-[#001E44] rounded-lg flex items-center justify-center">
            <GraduationCap className="w-4 h-4 text-white" />
          </div>
          <span className="font-heading font-bold text-[#001E44] text-sm">ACE</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
          className="h-8 w-8 text-[#475569] hover:bg-[#F1F5F9]"
          data-testid={`${testIdPrefix}collapse-sidebar-button`}
        >
          {isMobile ? <ChevronLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
        </Button>
      </div>

      {/* Profile Block */}
      <div className="p-3 border-b border-[#E2E8F0]">
        {profile ? (
          <div className="flex items-center gap-2.5" data-testid="profile-block">
            <Avatar className="h-9 w-9 border-2 border-[#96BEE6]/30">
              <AvatarImage src={profile.picture} />
              <AvatarFallback className="bg-[#001E44] text-white text-xs font-medium">
                {profile.name?.split(' ').map(n => n[0]).join('')}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-[#0F172A] text-sm truncate" data-testid="student-name">
                {profile.name}
              </p>
              <p className="text-xs text-[#475569]" data-testid="student-email">
                {profile.email}
              </p>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-[#475569] hover:bg-[#F1F5F9]"
                  data-testid="settings-button"
                >
                  <Settings className="w-3.5 h-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                {user?.is_admin && (
                  <>
                    <DropdownMenuItem 
                      onClick={() => navigate('/admin')}
                      className="cursor-pointer"
                    >
                      <Shield className="w-4 h-4 mr-2" />
                      Admin Panel
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                  </>
                )}
                <DropdownMenuItem 
                  onClick={handleLogout}
                  className="cursor-pointer text-red-600 focus:text-red-600"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ) : (
          <div className="animate-pulse flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-full bg-[#E2E8F0]" />
            <div className="flex-1">
              <div className="h-3.5 bg-[#E2E8F0] rounded w-20 mb-1" />
              <div className="h-3 bg-[#E2E8F0] rounded w-14" />
            </div>
          </div>
        )}
      </div>

      {/* Intelligence Card - Dynamic */}
      {intelligence && (
        <div className="p-3 border-b border-[#E2E8F0]">
          <Card 
            className={`border-0 border-l-[3px] shadow-none ${getUrgencyStyle(intelligence.urgency)}`}
            data-testid="intelligence-card"
          >
            <CardContent className="p-2.5">
              {/* Context Line */}
              <p className="text-[9px] uppercase tracking-wider text-[#94A3B8] mb-1" data-testid="intelligence-context">
                {intelligence.context?.term} · {intelligence.context?.level} · {intelligence.context?.status}
              </p>
              
              {/* Single Insight */}
              <p className="text-xs text-[#0F172A] leading-relaxed" data-testid="intelligence-insight">
                {intelligence.insight}
              </p>
              
              {/* Soft Action Button (optional) */}
              {intelligence.action && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleInsightAction}
                  className="mt-2 h-6 px-0 text-[10px] text-[#1E407C] hover:text-[#001E44] hover:bg-transparent font-medium gap-1"
                  data-testid="intelligence-action-button"
                >
                  {intelligence.action.label}
                  <ChevronRight className="w-3 h-3" />
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Quick Access Panel */}
      <div className="px-3 pt-3 pb-2 border-b border-[#E2E8F0]">
        <div className="flex items-center justify-between mb-1.5">
          <p className="text-[10px] font-medium text-[#475569] uppercase tracking-wider">
            Quick Access
          </p>
          <Dialog open={customizeOpen} onOpenChange={setCustomizeOpen}>
            <DialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleOpenCustomize}
                className="h-5 px-1.5 text-[9px] text-[#94A3B8] hover:text-[#475569] hover:bg-[#F1F5F9] gap-0.5"
                data-testid="customize-tools-button"
              >
                <Sliders className="w-2.5 h-2.5" />
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
        <div className="space-y-0.5" data-testid="quick-access-tools">
          {activeTools.map(tool => {
            const IconComponent = tool.icon;
            return (
              <button
                key={tool.id}
                onClick={() => handleToolClick(tool)}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left hover:bg-[#F1F5F9] transition-colors group"
                data-testid={`quick-tool-${tool.id}`}
              >
                <div className="w-6 h-6 rounded bg-[#F1F5F9] group-hover:bg-[#96BEE6]/20 flex items-center justify-center transition-colors">
                  <IconComponent className="w-3.5 h-3.5 text-[#1E407C]" />
                </div>
                <span className="text-xs text-[#0F172A]">{tool.label}</span>
                <ChevronRight className="w-3 h-3 text-[#94A3B8] ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
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
      <div className="p-3">
        <Button
          onClick={onNewChat}
          className="w-full bg-[#001E44] hover:bg-[#1E407C] text-white gap-2 h-9 text-sm"
          data-testid="new-chat-button"
        >
          <Plus className="w-4 h-4" />
          New conversation
        </Button>
      </div>

      {/* Chat History */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="px-3 py-1.5">
          <p className="text-[10px] font-medium text-[#475569] uppercase tracking-wider">
            Previous chats
          </p>
        </div>
        <ScrollArea className="flex-1 px-2">
          <div className="space-y-0.5 pb-3" data-testid="chat-history">
            {isLoading ? (
              <div className="space-y-1.5 px-1">
                {[1, 2, 3].map(i => (
                  <div key={i} className="animate-pulse h-8 bg-[#E2E8F0] rounded-md" />
                ))}
              </div>
            ) : chatSessions.length > 0 ? (
              chatSessions.map(session => (
                <div
                  key={session.id}
                  onClick={() => onSelectChat(session.id)}
                  className={`group flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-all duration-150 ${
                    currentChatId === session.id 
                      ? 'bg-[#96BEE6]/20 text-[#001E44]' 
                      : 'hover:bg-[#F1F5F9] text-[#475569]'
                  }`}
                  data-testid={`chat-item-${session.id}`}
                >
                  <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 opacity-60" />
                  <span className="flex-1 text-xs truncate">{session.title}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => handleDeleteChat(e, session.id)}
                    data-testid={`delete-chat-${session.id}`}
                  >
                    <Trash2 className="w-2.5 h-2.5 text-[#94A3B8] hover:text-red-500" />
                  </Button>
                </div>
              ))
            ) : (
              <p className="px-3 py-4 text-xs text-[#94A3B8] text-center">
                No previous conversations
              </p>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-[#E2E8F0]">
        <p className="text-[10px] text-[#94A3B8] text-center">
          Penn State Academic Support
        </p>
      </div>
    </aside>
  );
};

export default LeftSidebar;
