import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Send,
  X,
  Bot,
  User,
  Loader2,
  AlertTriangle,
  MessageCircle,
  Zap,
  ExternalLink
} from 'lucide-react';
import { toast } from 'sonner';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

// Simple offline medicine database for demo
const MEDICINE_RESPONSES: Record<string, string> = {
  'ibuprofen': `**Ibuprofen (Nurofen, Advil)**

📋 **Ce este:** Antiinflamator nesteroidian (AINS)

💊 **Utilizări:** Durere, febră, inflamație

⚠️ **Efecte secundare:**
- Dureri de stomac, greață
- Risc de ulcer la utilizare prelungită
- Poate afecta rinichii

🚫 **Contraindicații:**
- Ulcer gastric activ
- Insuficiență renală
- Sarcină (trimestrul 3)

💡 **Sfat:** Luați cu mâncare pentru a proteja stomacul.`,

  'paracetamol': `**Paracetamol (Tylenol, Panadol)**

📋 **Ce este:** Analgezic și antipiretic

💊 **Utilizări:** Durere ușoară-moderată, febră

⚠️ **Efecte secundare:** Rare la doze normale

🚫 **Contraindicații:**
- Afecțiuni hepatice severe
- Nu depășiți 4g/zi

💡 **Sfat:** Sigur în sarcină. Nu consumați alcool!`,

  'default': `Mulțumesc pentru întrebare! 

Aceasta este o versiune **demo** fără conexiune la backend.

🌐 Pentru recomandări complete bazate pe **1200+ medicamente**, vizitați:
**[RAG Pharma Assistant pe HuggingFace](https://huggingface.co/spaces)**

Sau întrebați despre:
- Ibuprofen
- Paracetamol
- Durere de cap
- Febră`
};

function getAIResponse(message: string): string {
  const lowerMsg = message.toLowerCase();

  if (lowerMsg.includes('ibuprofen') || lowerMsg.includes('nurofen') || lowerMsg.includes('advil')) {
    return MEDICINE_RESPONSES['ibuprofen'];
  }
  if (lowerMsg.includes('paracetamol') || lowerMsg.includes('tylenol') || lowerMsg.includes('panadol')) {
    return MEDICINE_RESPONSES['paracetamol'];
  }
  if (lowerMsg.includes('durere') || lowerMsg.includes('cap') || lowerMsg.includes('febr')) {
    return `**Pentru durere și febră:**

💊 **Opțiuni fără rețetă:**
- **Paracetamol 500mg** - Sigur pentru majoritatea persoanelor
- **Ibuprofen 200-400mg** - Pentru durere + inflamație

⚠️ **Important:** 
- Nu combinați mai multe analgezice
- Consultați medicul dacă simptomele persistă >3 zile

🌐 Pentru mai multe recomandări: vizitați HuggingFace Space`;
  }

  return MEDICINE_RESPONSES['default'];
}

export default function Chat() {
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    // Add welcome message on mount
    const welcomeMessage: Message = {
      id: Date.now().toString(),
      content: `👋 Bună! Sunt asistentul tău medical AI.

🔬 **Mode:** Demo Offline
💊 **Bază de date:** 1200+ medicamente

Pot răspunde la întrebări despre medicamente comune. Pentru versiunea completă, vizitați **HuggingFace Space**.

Întrebați-mă despre ibuprofen, paracetamol, sau simptome generale!`,
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

    // Simulate AI thinking
    await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 700));

    const aiResponse = getAIResponse(userMessage.content);

    const aiMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: aiResponse,
      sender: 'ai',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, aiMessage]);
    setIsLoading(false);
    setIsTyping(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const quickQuestions = [
    "Ce efecte secundare are ibuprofenul?",
    "Paracetamol pentru febră?",
    "Am durere de cap, ce iau?",
    "Ce medicamente pentru răceală?"
  ];

  const handleQuickQuestion = (question: string) => {
    setInputMessage(question);
    inputRef.current?.focus();
  };

  const openHuggingFace = () => {
    window.open('https://huggingface.co/spaces', '_blank');
    toast.info('Se deschide HuggingFace Space...');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => navigate('/')}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <X size={20} />
            </button>
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                <Bot className="text-white" size={16} />
              </div>
              <div>
                <h1 className="text-lg font-semibold">AI Assistant</h1>
                <p className="text-xs text-gray-600">Demo Mode</p>
              </div>
            </div>
            <button
              onClick={openHuggingFace}
              className="p-2 hover:bg-gray-100 rounded-lg text-purple-600"
              title="Open Full Version"
            >
              <ExternalLink size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* HuggingFace Banner */}
      <div className="bg-gradient-to-r from-purple-600 to-pink-500 text-white">
        <div className="max-w-md mx-auto px-4 py-3">
          <button
            onClick={openHuggingFace}
            className="w-full flex items-center justify-between"
          >
            <span className="text-sm font-medium">🚀 Versiunea completă pe HuggingFace</span>
            <ExternalLink size={16} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-md mx-auto px-4 py-6">
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex items-start space-x-2 max-w-[85%] ${message.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                  }`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${message.sender === 'user'
                      ? 'bg-blue-600'
                      : 'bg-gradient-to-r from-purple-500 to-pink-500'
                    }`}>
                    {message.sender === 'user' ? (
                      <User className="text-white" size={16} />
                    ) : (
                      <Bot className="text-white" size={16} />
                    )}
                  </div>

                  <div className={`rounded-2xl px-4 py-3 ${message.sender === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-gray-200 text-gray-800'
                    }`}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                      {message.content}
                    </p>
                    <p className={`text-xs mt-2 ${message.sender === 'user' ? 'text-blue-100' : 'text-gray-500'
                      }`}>
                      {message.timestamp.toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </p>
                  </div>
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex justify-start">
                <div className="flex items-start space-x-2 max-w-[85%]">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-gradient-to-r from-purple-500 to-pink-500">
                    <Bot className="text-white" size={16} />
                  </div>
                  <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Questions */}
          {messages.length <= 1 && (
            <div className="mt-8">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Întrebări rapide</h3>
              <div className="grid grid-cols-1 gap-2">
                {quickQuestions.map((question, index) => (
                  <button
                    key={index}
                    onClick={() => handleQuickQuestion(question)}
                    className="text-left p-3 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-purple-300 transition-colors"
                  >
                    <div className="flex items-center">
                      <Zap className="text-purple-500 mr-2 flex-shrink-0" size={16} />
                      <span className="text-sm text-gray-700">{question}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Safety Warning */}
      <div className="bg-amber-50 border-t border-amber-200">
        <div className="max-w-md mx-auto px-4 py-3">
          <div className="flex items-center">
            <AlertTriangle className="text-amber-600 mr-2 flex-shrink-0" size={16} />
            <p className="text-xs text-amber-700">
              Demo mode. Pentru recomandări complete, vizitați versiunea HuggingFace.
            </p>
          </div>
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-end space-x-3">
            <div className="flex-1">
              <input
                ref={inputRef}
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Întreabă despre medicamente..."
                className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                disabled={isLoading}
              />
            </div>
            <button
              onClick={sendMessage}
              disabled={!inputMessage.trim() || isLoading}
              className="bg-purple-600 text-white p-3 rounded-2xl hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <Loader2 className="animate-spin" size={20} />
              ) : (
                <Send size={20} />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}