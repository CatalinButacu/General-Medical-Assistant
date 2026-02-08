import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Send,
  X,
  Bot,
  User,
  Loader2,
  AlertTriangle,
  Zap,
  ExternalLink,
  Wifi,
  WifiOff
} from 'lucide-react';
import { toast } from 'sonner';
import type { Message } from '../types';
import { searchMedicines, isApiConfigured } from '../services/api';

export default function Chat() {
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isOnline, setIsOnline] = useState(isApiConfigured());

  useEffect(() => {
    const welcomeMessage: Message = {
      id: Date.now().toString(),
      content: `System ready. Connected to Secure Patient Cloud.
      
Ask about symptoms or medicines to query our medical knowledge base.`,
      sender: 'ai',
      timestamp: new Date()
    };
    setMessages([welcomeMessage]);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage.trim(),
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setIsTyping(true);

    try {
      const aiResponse = await searchMedicines(userMessage.content);
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: aiResponse,
        sender: 'ai',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiMessage]);
      setIsOnline(true);
    } catch (error: any) {
      console.error("API Error:", error);
      setIsOnline(false);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `Connection Error: ${error.message || "The Zurich backend is currently unreachable."}\n\nTechnical details: Error 503 or VITE_BACKEND_URL mismatch.`,
        sender: 'ai',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const quickSearches = ["headache", "fever", "cold", "Ibuprofen"];

  const handleQuickSearch = (query: string) => {
    setInputMessage(query);
    inputRef.current?.focus();
  };

  return (
    <div className="h-full flex flex-col bg-gray-50 overflow-hidden">
      <div className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <button onClick={() => navigate('/')} className="p-2 hover:bg-gray-100 rounded-full transition-colors font-bold text-gray-400 hover:text-gray-800">
              <X size={20} />
            </button>
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full flex items-center justify-center shadow-lg shadow-blue-100">
                <Bot className="text-white" size={20} />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-800 tracking-tight leading-none">Health Assistant</h1>
                <div className="flex items-center mt-1">
                  {isOnline ? (
                    <span className="text-[9px] font-bold text-green-600 uppercase tracking-widest flex items-center bg-green-50 px-1.5 py-0.5 rounded-full">
                      <div className="w-1 h-1 bg-green-500 rounded-full mr-1 animate-pulse" /> Zurich Cloud Active
                    </span>
                  ) : (
                    <span className="text-[9px] font-bold text-red-600 uppercase tracking-widest flex items-center bg-red-50 px-1.5 py-0.5 rounded-full">
                      <div className="w-1 h-1 bg-red-500 rounded-full mr-1" /> Offline
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="w-10 h-10" /> {/* Spacer */}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scroll-smooth bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-md mx-auto px-4 py-6">
          <div className="space-y-6">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom duration-300`}>
                <div className={`flex items-start space-x-3 max-w-[88%] ${message.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm ${message.sender === 'user' ? 'bg-blue-600' : 'bg-white border border-gray-100'}`}>
                    {message.sender === 'user' ? <User className="text-white" size={16} /> : <Bot className="text-blue-600" size={16} />}
                  </div>

                  <div className={`rounded-2xl px-4 py-3 shadow-sm ${message.sender === 'user' ? 'bg-gradient-to-br from-blue-600 to-indigo-700 text-white' : 'bg-white border border-gray-100 text-gray-800'}`}>
                    <p className="text-sm font-medium leading-relaxed whitespace-pre-wrap">{message.content}</p>
                    <div className="flex items-center justify-end mt-2 space-x-1 opacity-40">
                      <span className="text-[8px] font-bold uppercase tracking-tighter">
                        {message.sender === 'user' ? 'Sent' : 'Assistant'} • {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex justify-start animate-pulse">
                <div className="flex items-start space-x-3 max-w-[85%] text-gray-400">
                  <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 bg-white border border-gray-100">
                    <Loader2 className="animate-spin text-blue-500" size={16} />
                  </div>
                  <div className="bg-white border border-gray-100 rounded-2xl px-4 py-3">
                    <div className="flex space-x-1">
                      <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce"></div>
                      <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                      <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:0.4s]"></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {messages.length <= 1 && (
            <div className="mt-12 animate-in fade-in duration-700">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-[0.2em] ml-1">Quick Actions</h3>
                <div className="h-[1px] flex-1 bg-gray-100 ml-4"></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {quickSearches.map((query, index) => (
                  <button
                    key={index}
                    onClick={() => handleQuickSearch(query)}
                    className="group text-left p-4 bg-white border border-gray-100 rounded-2xl hover:border-blue-200 hover:shadow-lg hover:shadow-blue-50 transition-all active:scale-[0.98]"
                  >
                    <div className="flex items-center mb-1">
                      <Zap className="text-blue-500 mr-2 flex-shrink-0 group-hover:fill-blue-500" size={14} />
                      <span className="text-xs font-bold text-gray-700 capitalize">{query}</span>
                    </div>
                    <p className="text-[9px] text-gray-400 font-medium">Ask about {query}</p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white border-t border-gray-100 p-4 pb-8 transition-all">
        <div className="max-w-md mx-auto relative group">
          <textarea
            ref={inputRef as any}
            rows={1}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="Describe your symptoms..."
            className="w-full pl-5 pr-14 py-4 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500/20 font-medium text-sm resize-none shadow-inner transition-all placeholder:text-gray-400"
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="absolute right-2 top-2 bg-blue-600 text-white p-2.5 rounded-xl hover:bg-blue-700 disabled:opacity-20 transition-all shadow-md active:scale-90"
          >
            {isLoading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
          </button>
        </div>
        <div className="flex items-center justify-center mt-3 space-x-2">
          <AlertTriangle className="text-amber-500" size={10} />
          <p className="text-[9px] text-gray-400 font-bold uppercase tracking-tight">AI Demo • Verified Medical Database</p>
        </div>
      </div>
    </div>
  );
}
