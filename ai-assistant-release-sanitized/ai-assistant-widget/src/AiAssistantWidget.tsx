import React, { useState, useEffect, useRef } from 'react';
import type { WidgetProps } from './types';
import { postChat } from './api';

const containerStyle: React.CSSProperties = {
  border: '1px solid #ddd', borderRadius: 8, padding: 12,
  width: '100%', maxWidth: 720, background: '#fff'
};

const AiAssistantWidget: React.FC<WidgetProps> = ({ apiBaseUrl, modelId, autoScroll = true, onError }) => {
  const [messages, setMessages] = useState<{role:string; content:string}[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const send = async () => {
    const text = input.trim(); if (!text) return;
    const user = { role: 'user', content: text };
    setMessages(m => [...m, user]);
    setInput('');
    setLoading(true);
    try {
      const resp = await postChat(apiBaseUrl, { message: text, model_id: modelId });
      const reply = resp?.content ?? '';
      setMessages(m => [...m, { role: 'assistant', content: reply }]);
    } catch (e: any) {
      onError?.(e?.message ?? 'Unknown error');
    } finally {
      setLoading(false);
      if (autoScroll) endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Auto scroll on new messages
  useEffect(() => {
    if (autoScroll) endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="ai-assistant-widget" style={containerStyle}>
      <div style={{ height: 320, overflowY: 'auto', padding: 6, border: '1px solid #eee', borderRadius: 6 }}>
        {messages.map((m, idx) => (
          <div key={idx} style={{ textAlign: m.role === 'user' ? 'right' : 'left', margin: '6px 0' }}>
            <span style={{ display: 'inline-block', padding: '8px 12px', borderRadius: 12, background: m.role === 'user' ? '#e6f7ff' : '#f0f0f0' }}>{m.content}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <input value={input} onChange={e => setInput(e.target.value)} placeholder="输入消息" style={{ flex: 1, padding: 10, borderRadius: 6, border: '1px solid #ddd' }} onKeyDown={e => e.key === 'Enter' && send()} />
        <button onClick={send} disabled={loading} style={{ padding: '10px 14px', borderRadius: 6 }}>发送</button>
      </div>
    </div>
  );
};

export default AiAssistantWidget; 
