'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, AlertTriangle, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { chatWithAgent } from '../lib/api';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    isHallucinated?: boolean;
}

export default function ChatWindow() {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: 'welcome',
            role: 'assistant',
            content: '你好！我是你的 Local AI Copilot。你可以向我提问，或者在左侧上传文档后让我基于知识库回答。',
        }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // 用于自动滚动到底部
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input.trim(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            // 调用我们封装好的 API 桥梁
            const response = await chatWithAgent(userMessage.content);

            const aiMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.answer,
                isHallucinated: response.is_hallucinated,
            };

            setMessages((prev) => [...prev, aiMessage]);
        } catch (error) {
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: '❌ 抱歉，与本地 Agent 通信失败，请检查后端服务是否正常运行。',
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex-1 flex flex-col h-screen bg-white relative">
            {/* 顶部栏 */}
            <header className="h-16 border-b border-gray-200 flex items-center px-6 bg-white shrink-0">
                <h2 className="text-lg font-semibold text-gray-800">新会话</h2>
                <div className="ml-auto flex items-center gap-2 text-sm text-gray-500">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                    Agent 待命区
                </div>
            </header>

            {/* 消息列表区 */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 scroll-smooth">
                {messages.map((msg) => (
                    <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                        {/* 头像 */}
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                            msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-indigo-100 text-indigo-600'
                        }`}>
                            {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-6 h-6" />}
                        </div>

                        {/* 气泡内容 */}
                        <div className={`max-w-[80%] xl:max-w-[70%] flex flex-col gap-1 ${
                            msg.role === 'user' ? 'items-end' : 'items-start'
                        }`}>
                            <div className={`px-5 py-3.5 rounded-2xl shadow-sm prose prose-sm max-w-none ${
                                msg.role === 'user' 
                                    ? 'bg-blue-600 text-white rounded-tr-sm' 
                                    : 'bg-gray-50 border border-gray-100 text-gray-800 rounded-tl-sm'
                            }`}>
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                            </div>

                            {/* 幻觉校验警告 */}
                            {msg.isHallucinated && (
                                <div className="flex items-center gap-1.5 text-xs text-amber-600 mt-1 bg-amber-50 px-2 py-1 rounded-md">
                                    <AlertTriangle className="w-3.5 h-3.5" />
                                    <span>AI 校验发现：部分内容可能缺乏知识库依据，请谨慎参考。</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {/* 加载动画 */}
                {isLoading && (
                    <div className="flex gap-4 flex-row">
                        <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0">
                            <Loader2 className="w-6 h-6 animate-spin" />
                        </div>
                        <div className="px-5 py-4 rounded-2xl bg-gray-50 border border-gray-100 rounded-tl-sm flex items-center gap-2">
                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></span>
                            <span className="ml-2 text-sm text-gray-500">Agent 正在思考并执行任务...</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* 底部输入区 */}
            <div className="p-4 bg-white border-t border-gray-200 shrink-0">
                <div className="max-w-4xl mx-auto relative flex items-end gap-2 bg-gray-50 border border-gray-300 rounded-2xl focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-500 transition-all p-2 shadow-sm">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="输入你的问题，或者让 Copilot 帮你执行代码 (Shift + Enter 换行)..."
                        className="w-full max-h-32 min-h-[44px] bg-transparent border-none focus:ring-0 resize-none py-2 px-3 text-sm text-gray-800 placeholder-gray-400"
                        rows={1}
                        // 简单的自动拉伸高度技巧
                        style={{ height: 'auto', outline: 'none' }}
                        onInput={(e) => {
                            const target = e.target as HTMLTextAreaElement;
                            target.style.height = 'auto';
                            target.style.height = target.scrollHeight + 'px';
                        }}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || isLoading}
                        className="p-2.5 rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors mb-0.5 mr-0.5 shadow-sm"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </div>
                <div className="text-center mt-2 text-xs text-gray-400">
                    Copilot 可能会犯错。请核实重要的信息。
                </div>
            </div>
        </div>
    );
}