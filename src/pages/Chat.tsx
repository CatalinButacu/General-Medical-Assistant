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
import { searchMedicines, HF_SPACE_URL } from '../services/api';

export default function Chat() {
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    const welcomeMessage: Message = {
      id: Date.now().toString(),
      content: `System ready. Connected to RAG Backend.
      
Ask about symptoms or medicines for accurate results from the database.`,
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
        content: `Error: ${error.message || "Could not reach the backend system."}\nPlease ensure the Hugging Face Space is running and the API URL is correct.`,
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

  const openHuggingFace = () => {
    window.open(HF_SPACE_URL, '_blank');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <button onClick={() => navigate('/')} className="p-2 hover:bg-gray-100 rounded-lg">
              <X size={20} />
            </button>
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gray-800 rounded-full flex items-center justify-center">
                <Bot className="text-white" size={16} />
              </div>
              <div>
                <h1 className="text-lg font-semibold">Pharma RAG</h1>
                <div className="flex items-center space-x-1">
                  {isOnline ? (
                    <span className="text-xs text-green-600 flex items-center">
                      <Wifi size={12} className="mr-1" /> Online
                    </span>
                  ) : (
                    <span className="text-xs text-red-600 flex items-center">
                      <WifiOff size={12} className="mr-1" /> Offline
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button onClick={openHuggingFace} className="p-2 hover:bg-gray-100 rounded-lg text-gray-600" title="Open Space">
              <ExternalLink size={20} />
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-md mx-auto px-4 py-6">
          <div className="space-y-4">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex items-start space-x-2 max-w-[85%] ${message.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${message.sender === 'user' ? 'bg-blue-600' : 'bg-gray-700'}`}>
                    {message.sender === 'user' ? <User className="text-white" size={16} /> : <Bot className="text-white" size={16} />}
                  </div>

                  <div className={`rounded-2xl px-4 py-3 ${message.sender === 'user' ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200 text-gray-800 shadow-sm'}`}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                    <p className={`text-[10px] mt-2 opacity-50 ${message.sender === 'user' ? 'text-white' : 'text-gray-500'}`}>
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex justify-start">
                <div className="flex items-start space-x-2 max-w-[85%] text-gray-400">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-gray-200">
                    <Loader2 className="animate-spin" size={16} />
                  </div>
                  <span className="text-xs pt-2 italic">Querying RAG system...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {messages.length <= 1 && (
            <div className="mt-8">
              <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Quick Search</h3>
              <div className="grid grid-cols-2 gap-2">
                {quickSearches.map((query, index) => (
                  <button key={index} onClick={() => handleQuickSearch(query)} className="text-left p-3 bg-white border border-gray-200 rounded-lg hover:border-gray-400 transition-colors shadow-sm">
                    <div className="flex items-center">
                      <Zap className="text-gray-400 mr-2 flex-shrink-0" size={14} />
                      <span className="text-sm text-gray-600">{query}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-gray-100 border-t border-gray-200">
        <div className="max-w-md mx-auto px-4 py-2">
          <div className="flex items-center justify-center">
            <AlertTriangle className="text-gray-400 mr-1" size={12} />
            <p className="text-[10px] text-gray-500 uppercase font-bold tracking-tight">Medical accuracy provided by RAG backend</p>
          </div>
        </div>
      </div>

      <div className="bg-white border-t border-gray-200 pb-safe">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-end space-x-2">
            <div className="flex-1">
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
                placeholder="Search database..."
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-1 focus:ring-gray-400 focus:border-transparent outline-none text-sm resize-none"
                disabled={isLoading}
              />
            </div>
            <button onClick={sendMessage} disabled={!inputMessage.trim() || isLoading} className="bg-gray-800 text-white p-3 rounded-2xl hover:bg-black disabled:opacity-30 transition-all shadow-md">
              {isLoading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
