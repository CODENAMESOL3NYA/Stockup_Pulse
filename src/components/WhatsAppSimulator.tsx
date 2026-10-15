import React, { useState, useRef, useEffect } from 'react';
import { sendWhatsAppMessage } from '../services/api';

interface Message {
  id: string;
  sender: 'owner' | 'bot';
  text: string;
  timestamp: string;
  image?: string;
  hasOrderDoc?: boolean;
}

export const WhatsAppSimulator: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);

  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSend = async (customText?: string) => {
    const textToSend = customText || input;
    if (!textToSend.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'owner',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    if (!customText) setInput('');
    setIsTyping(true);

    try {
      const response = await sendWhatsAppMessage(textToSend);
      const orderSummary = response.orders?.map(order =>
        `${order.order_number} (${order.supplier}): R ${order.total_spend.toFixed(2)}`
      ).join('\n') || '';
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: 'bot',
        text: orderSummary ? `${response.reply}\n\n${orderSummary}` : response.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        hasOrderDoc: Boolean(response.orders?.length)
      }]);
    } catch (error) {
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: 'bot',
        text: error instanceof Error ? error.message : 'Request failed.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
      return;
    }
    setIsTyping(false);
  };

  return (
    <div className="p-6 md:p-8 max-w-4xl mx-auto space-y-6 text-white font-sans">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] font-mono font-bold tracking-widest text-[#E50000] uppercase mb-1">
            CHANNEL 2 // AUTHENTICATED WHATSAPP SIMULATOR
          </div>
          <h2 className="text-2xl font-black text-white tracking-wider uppercase">
            WHATSAPP RESTOCKING CHANNEL
          </h2>
          <p className="text-xs text-[#888888] mt-1 tracking-wide">
            Approval messages use your saved plan. Leaflet ingestion and provider delivery are not connected.
          </p>
        </div>
        <div className="text-right">
          <span className="text-[10px] font-mono font-bold px-2.5 py-1 rounded-[2px] bg-[#1A1A1A] text-[#00CC66] border border-[#00CC66]/40 uppercase">
            SIMULATOR
          </span>
          <div className="text-[11px] text-[#888888] font-mono mt-1">POST /api/whatsapp/webhook</div>
        </div>
      </div>

      {/* Interactive Quick Action Prompts */}
      <div className="flex flex-wrap gap-2 text-xs font-mono">
        <span className="text-[#888888] font-bold py-1 uppercase">QUICK ACTIONS:</span>
        <button
          onClick={() => handleSend('Here is my new Makro leaflet photo')}
          className="px-3 py-1 bg-[#1A1A1A] border border-[#333333] hover:border-[#E50000] rounded-[2px] text-white cursor-pointer transition-colors"
        >
          SEND LEAFLET PHOTO
        </button>
        <button
          onClick={() => handleSend('APPROVE')}
          className="px-3 py-1 bg-[#E50000] text-white rounded-[2px] hover:bg-[#CC0000] font-bold cursor-pointer transition-colors shadow-sm"
        >
          APPROVE (CLEAR GATE)
        </button>
        <button
          onClick={() => handleSend('What is my remaining Rand budget?')}
          className="px-3 py-1 bg-[#1A1A1A] border border-[#333333] hover:border-[#E50000] rounded-[2px] text-white cursor-pointer transition-colors"
        >
          CHECK BUDGET
        </button>
      </div>

      {/* Chat Terminal Frame */}
      <div className="max-w-md mx-auto rounded-[4px] overflow-hidden shadow-2xl border border-[#333333] bg-[#0B0B0B] flex flex-col h-[580px]">
        {/* Terminal Header */}
        <div className="bg-[#1A1A1A] text-white px-4 py-3 flex items-center justify-between shrink-0 border-b border-[#333333]">
          <div>
            <div className="font-bold text-xs uppercase tracking-wider font-mono">STOCKUP PULSE AGENT</div>
            <div className="text-[10px] text-[#888888] font-mono">LOCAL SIMULATOR</div>
          </div>
          <span className="text-[10px] font-mono text-[#888888]">SECURED WEBHOOK</span>
        </div>

        {/* Messages Body */}
        <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-[#0B0B0B]">
          <div className="text-center my-1">
            <span className="text-[9px] bg-[#1A1A1A] text-[#888888] px-2 py-0.5 rounded-[2px] border border-[#333333] uppercase font-mono">
              END-TO-END ENCRYPTED CHANNEL
            </span>
          </div>

          {messages.map((m) => {
            const isOwner = m.sender === 'owner';
            return (
              <div
                key={m.id}
                className={`flex ${isOwner ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-[4px] p-3 text-xs leading-relaxed font-mono ${
                    isOwner
                      ? 'bg-[#1A1A1A] text-white border border-[#333333] border-r-2 border-r-[#E50000]'
                      : 'bg-[#1A1A1A] text-[#CCCCCC] border border-[#333333] border-l-2 border-l-[#00CC66]'
                  }`}
                >
                  {m.image && (
                    <div className="mb-2 rounded-[2px] overflow-hidden border border-[#333333]">
                      <img src={m.image} alt="Wholesale Leaflet" className="w-full h-36 object-cover" />
                    </div>
                  )}

                  <div className="whitespace-pre-wrap">{m.text}</div>

                  {m.hasOrderDoc && (
                    <div className="mt-2.5 pt-2 border-t border-[#333333] flex items-center justify-between text-[11px] text-[#00CC66]">
                      <span className="font-bold uppercase">PO-2026-SUNNYSIDE.PDF</span>
                      <span className="text-[#888888]">[READY]</span>
                    </div>
                  )}

                  <div className="text-[9px] text-[#888888] text-right mt-1.5">
                    {m.timestamp}
                  </div>
                </div>
              </div>
            );
          })}

          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-[#1A1A1A] border border-[#333333] rounded-[4px] px-3 py-2 text-xs font-mono text-[#888888]">
                AMD Agent processing leaflet...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Footer */}
        <div className="p-3 bg-[#1A1A1A] border-t border-[#333333] flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Type message or 'APPROVE'..."
            className="flex-1 px-3 py-2 bg-[#0B0B0B] border border-[#333333] text-white text-xs font-mono rounded-[2px] focus:border-[#E50000] focus:outline-none"
          />
          <button
            onClick={() => handleSend()}
            className="px-4 py-2 bg-[#E50000] hover:bg-[#CC0000] text-white text-xs font-bold uppercase rounded-[2px] transition-colors cursor-pointer"
          >
            SEND
          </button>
        </div>
      </div>
    </div>
  );
};
