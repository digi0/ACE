import { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { ACEResponse } from './ACEResponse';
import { 
  Send, 
  Plus, 
  GraduationCap,
  Sparkles,
  Calendar,
  AlertCircle,
  Target,
  Menu,
  PanelLeft
} from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const QUICK_STARTERS = [
  { icon: Target, text: "Help me plan this semester", color: "text-[#1E407C]" },
  { icon: Sparkles, text: "What should I focus on this week?", color: "text-amber-600" },
  { icon: AlertCircle, text: "I'm worried about a deadline", color: "text-red-500" },
  { icon: Calendar, text: "Check my schedule", color: "text-emerald-600" },
];

export const ChatWorkspace = ({ 
  chatId, 
  studentId, 
  onChatCreated,
  messages,
  setMessages,
  prefillPrompt,
  clearPrefill,
  sidebarCollapsed,
  onToggleSidebar,
  onToggleMobileMenu
}) => {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    // Scroll to bottom when messages change
    if (scrollRef.current) {
      const scrollElement = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [messages]);

  useEffect(() => {
    // Focus input on mount and when chat changes
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [chatId]);

  // Handle prefill prompt from intelligence card
  useEffect(() => {
    if (prefillPrompt && !isLoading) {
      setInput(prefillPrompt);
      if (clearPrefill) clearPrefill();
      // Auto-send after a brief delay
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 100);
    }
  }, [prefillPrompt, clearPrefill, isLoading]);

  const sendMessage = async (messageText) => {
    if (!messageText.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: messageText.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API}/chat/send`, {
        chat_id: chatId || null,
        message: messageText.trim(),
        student_id: studentId
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response.direct_answer,
        timestamp: new Date().toISOString(),
        structured_response: response.data.response
      };

      setMessages(prev => [...prev, assistantMessage]);

      // If this was a new chat, notify parent
      if (!chatId && response.data.chat_id) {
        onChatCreated(response.data.chat_id);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'I apologize, but I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        structured_response: {
          direct_answer: 'I apologize, but I encountered an error processing your request. Please try again.',
          next_steps: ['Refresh the page', 'Try rephrasing your question'],
          sources_used: [],
          risk_level: 'low',
          advisor_needed: false
        }
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleQuickStart = (text) => {
    sendMessage(text);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div 
      className="flex-1 flex flex-col h-screen bg-[#F4F6F8]"
      data-testid="chat-workspace"
    >
      {/* Header */}
      <header className="h-16 px-6 flex items-center border-b border-[#E2E8F0] bg-white/80 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-[#001E44] rounded-lg flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-white" />
          </div>
          <span className="font-heading font-bold text-[#001E44] text-lg">ACE</span>
        </div>
      </header>

      {/* Messages Area */}
      <ScrollArea className="flex-1" ref={scrollRef}>
        <div className="max-w-3xl mx-auto px-6 py-8" data-testid="messages-container">
          {messages.length === 0 ? (
            // Welcome state
            <div className="text-center py-16" data-testid="welcome-state">
              <div className="w-16 h-16 mx-auto mb-6 bg-[#001E44] rounded-2xl flex items-center justify-center">
                <GraduationCap className="w-9 h-9 text-white" />
              </div>
              <h2 className="font-heading text-2xl font-bold text-[#001E44] mb-2">
                How can I help you today?
              </h2>
              <p className="text-[#475569] max-w-md mx-auto">
                I'm ACE, your academic advisor assistant. Ask me about courses, deadlines, policies, or academic planning.
              </p>
            </div>
          ) : (
            // Messages
            <div className="space-y-6">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in-up`}
                  data-testid={`message-${index}`}
                >
                  {message.role === 'user' ? (
                    <div 
                      className="bg-[#001E44] text-white rounded-2xl rounded-tr-sm px-5 py-3 max-w-[80%] shadow-sm"
                      data-testid="user-message"
                    >
                      <p className="leading-relaxed">{message.content}</p>
                    </div>
                  ) : (
                    <div className="max-w-[90%]" data-testid="assistant-message">
                      <ACEResponse response={message.structured_response} />
                    </div>
                  )}
                </div>
              ))}
              
              {/* Loading indicator */}
              {isLoading && (
                <div className="flex justify-start animate-fade-in-up">
                  <div className="bg-white border border-[#E2E8F0] rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-[#001E44] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-[#001E44] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-[#001E44] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="border-t border-[#E2E8F0] bg-white p-4">
        <div className="max-w-3xl mx-auto">
          {/* Quick Starters */}
          {messages.length === 0 && (
            <div className="flex flex-wrap gap-2 mb-4" data-testid="quick-starters">
              {QUICK_STARTERS.map((starter, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={() => handleQuickStart(starter.text)}
                  className="bg-white hover:bg-[#F8FAFC] border-[#E2E8F0] hover:border-[#96BEE6] text-[#475569] gap-2 transition-all"
                  data-testid={`quick-starter-${index}`}
                >
                  <starter.icon className={`w-4 h-4 ${starter.color}`} />
                  {starter.text}
                </Button>
              ))}
            </div>
          )}

          {/* Input Form */}
          <form onSubmit={handleSubmit} className="relative">
            <div className="flex items-center gap-2 bg-white border border-[#E2E8F0] rounded-xl px-4 py-2 focus-within:ring-2 focus-within:ring-[#96BEE6] focus-within:border-[#96BEE6] transition-all shadow-sm">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-[#94A3B8] hover:text-[#475569] hover:bg-[#F1F5F9]"
                data-testid="upload-button"
              >
                <Plus className="w-5 h-5" />
              </Button>
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type, paste, or upload…"
                className="flex-1 bg-transparent border-none outline-none text-[#0F172A] placeholder:text-[#94A3B8] py-2"
                disabled={isLoading}
                data-testid="message-input"
              />
              <Button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="h-9 w-9 bg-[#001E44] hover:bg-[#1E407C] disabled:bg-[#E2E8F0] disabled:text-[#94A3B8] rounded-lg"
                data-testid="send-button"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </form>

          {/* Disclaimer */}
          <p className="text-xs text-[#94A3B8] text-center mt-3">
            ACE provides guidance based on Penn State policies. Always verify with official sources.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatWorkspace;
