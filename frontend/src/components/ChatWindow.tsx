'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
    Send, Bot, User, AlertTriangle, Loader2, Database,
    FileText, Paperclip, ChevronDown, ChevronUp, FileCode2, FileType2, AlignLeft
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { chatWithAgent } from '../lib/api';

interface Source {
    docName: string;
    chunkId: number;
    score: number;
    type?: 'pdf' | 'md' | 'docx' | 'txt';
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    isHallucinated?: boolean;
    sources?: Source[];
    snippets?: string;
}

// 单独抽离的助手消息组件（管理引用和片段的折叠状态）
const AssistantMessage = ({ msg }: { msg: Message }) => {
    const [showSources, setShowSources] = useState(true);
    const [showSnippets, setShowSnippets] = useState(false);

    const getFileIcon = (type?: string) => {
        switch(type) {
            case 'pdf': return <FileText className="w-4 h-4 text-red-500" />;
            case 'md': return <FileCode2 className="w-4 h-4 text-blue-500" />;
            case 'docx': return <FileType2 className="w-4 h-4 text-blue-600" />;
            default: return <AlignLeft className="w-4 h-4 text-gray-500" />;
        }
    };

    return (
        <div className="flex gap-4">
            {/* 头像加了轻量阴影和浅边框 */}
            <div className="w-10 h-10 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 border border-indigo-100 shadow-sm">
                <Bot className="w-6 h-6" />
            </div>
            <div className="flex-1 max-w-[85%]">
                <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-gray-800 text-sm">Local Copilot</span>
                    <span className="text-xs text-gray-400">{msg.timestamp}</span>
                </div>

                {/* ✅ 修复了 ReactMarkdown 的类名报错，将 prose 样式移到外层 div */}
                <div className="text-gray-700 text-[15px] leading-relaxed mb-4 prose prose-sm max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>

                {/* 引用来源 - 增加浅色边框(border-gray-200)和投影(shadow-sm) */}
                {msg.sources && msg.sources.length > 0 && (
                    <div className="mb-3 border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
                        <button
                            onClick={() => setShowSources(!showSources)}
                            className="w-full flex items-center justify-between px-4 py-3 bg-gray-50/50 hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors"
                        >
                            <span>引用来源 ({msg.sources.length})</span>
                            {showSources ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                        </button>
                        {showSources && (
                            <div className="px-4 py-3 border-t border-gray-100 flex flex-wrap gap-3 bg-white">
                                {msg.sources.map((s, i) => (
                                    <div key={i} className="flex items-start gap-3 p-3 border border-gray-200 rounded-lg bg-gray-50/50 min-w-[200px] shadow-sm hover:shadow-md transition-shadow">
                                        <div className="mt-0.5">{getFileIcon(s.type)}</div>
                                        <div>
                                            <div className="text-sm font-medium text-gray-800 mb-1">{s.docName}</div>
                                            <div className="text-xs text-gray-500">
                                                chunk {s.chunkId} · 相似度 {s.score.toFixed(2)}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* 检索片段 - 增加浅色边框和投影 */}
                {msg.snippets && (
                    <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
                        <button
                            onClick={() => setShowSnippets(!showSnippets)}
                            className="w-full flex items-center justify-between px-4 py-3 bg-gray-50/50 hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors"
                        >
                            <span>检索片段 (点击展开)</span>
                            {showSnippets ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                        </button>
                        {showSnippets && (
                            <div className="px-4 py-3 border-t border-gray-100 bg-white text-sm text-gray-600 leading-relaxed">
                                {msg.snippets}
                            </div>
                        )}
                    </div>
                )}

                {msg.isHallucinated && (
                    <div className="mt-2 text-xs text-amber-600 flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" /> 可能缺乏知识库依据
                    </div>
                )}
            </div>
        </div>
    );
};

export default function ChatWindow() {
    const getCurrentTime = () => {
        const now = new Date();
        return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    };

    const [messages, setMessages] = useState<Message[]>([
        // ✅ 补全了用户的历史提问，以完全匹配截图效果
        {
            id: 'user-1',
            role: 'user',
            content: '什么是 Transformer？它的核心思想是什么？',
            timestamp: '11:20'
        },
        {
            id: 'welcome',
            role: 'assistant',
            content: 'Transformer 是一种基于注意力机制（Attention Mechanism）的深度学习模型，最早由 Google 在 2017 年提出，论文名为《Attention Is All You Need》。\n\n它的核心思想是：完全摒弃了传统的循环神经网络 (RNN) 和卷积神经网络 (CNN) 结构，转而依赖自注意力机制 (Self-Attention) 来建模输入序列中任意两个位置之间的依赖关系。\n\n主要特点包括：\n* **自注意力机制**：计算序列内部元素之间的关联，而不依赖于位置的远近。\n* **并行计算**：相比 RNN，Transformer 可以并行处理整个序列，大大提升训练效率。\n* **编码器-解码器结构**：由多个编码器层和解码器层堆叠而成，广泛应用于自然语言处理任务。',
            timestamp: '11:20',
            sources: [
                { docName: 'Transformer论文.pdf', chunkId: 12, score: 0.89, type: 'pdf' },
                { docName: 'attention机制.md', chunkId: 3, score: 0.83, type: 'md' },
                { docName: '大模型综述.docx', chunkId: 25, score: 0.76, type: 'docx' },
            ],
            snippets: 'Transformer uses self-attention to compute representations of its input and output without using sequence aligned RNNs or convolution...'
        }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [mode, setMode] = useState<'rag' | 'chat'>('rag');

    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input.trim(),
            timestamp: getCurrentTime()
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await chatWithAgent({ query: userMessage.content, mode });

            const aiMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.answer,
                timestamp: getCurrentTime(),
                isHallucinated: response.is_hallucinated,
                sources: response.sources || [],
                snippets: 'Mocked snippet content for demonstration based on the query...'
            };

            setMessages((prev) => [...prev, aiMessage]);
        } catch {
            setMessages((prev) => [
                ...prev,
                {
                    id: Date.now().toString(),
                    role: 'assistant',
                    content: '❌ 抱歉，与本地 Agent 通信失败，请检查后端服务。',
                    timestamp: getCurrentTime()
                }
            ]);
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
        <div className="flex-1 flex flex-col h-screen bg-[#F9FAFB]">
            {/* 顶部状态栏 - 显式指定浅灰色边框 */}
            <header className="h-16 border-b border-gray-200 bg-white flex items-center px-6 text-sm flex-shrink-0 shadow-sm z-10">
                <h2 className="font-semibold text-gray-800 text-base">新会话</h2>

                <div className="ml-8 flex items-center gap-6 text-gray-600">
                    <div className="flex items-center gap-2 bg-green-50 border border-green-100 text-green-700 px-3 py-1.5 rounded-md text-xs font-medium cursor-pointer">
                        <Database className="w-3.5 h-3.5" />
                        RAG 增强模式
                        <ChevronDown className="w-3 h-3 ml-1" />
                    </div>
                    <span>当前知识库：<span className="font-medium text-gray-800">默认知识库</span></span>
                    <span className="flex items-center gap-1.5">
                        <FileText className="w-4 h-4 text-gray-400" />
                        使用文档：5个
                    </span>
                    <button className="flex items-center gap-1.5 border border-gray-200 px-3 py-1.5 rounded-md hover:bg-gray-50 transition-colors shadow-sm">
                        <AlignLeft className="w-3.5 h-3.5" />
                        检索日志
                    </button>
                </div>

                <div className="ml-auto flex items-center gap-2 text-gray-600 text-sm">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
                    </span>
                    Agent 待命区
                    <ChevronDown className="w-4 h-4" />
                </div>
            </header>

            {/* 消息区 */}
            <div className="flex-1 overflow-y-auto px-10 py-8 space-y-8 pb-32">
                {messages.map((msg) => (
                    <div key={msg.id}>
                        {msg.role === 'user' ? (
                            <div className="flex gap-4 flex-row-reverse">
                                <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0 shadow-sm">
                                    <User className="w-6 h-6" />
                                </div>
                                <div className="flex flex-col items-end max-w-[70%]">
                                    <div className="text-xs text-gray-400 mb-1">{msg.timestamp}</div>
                                    <div className="px-5 py-3 rounded-2xl bg-blue-50/80 text-gray-800 text-[15px] rounded-tr-sm shadow-sm border border-blue-100/50">
                                        {msg.content}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <AssistantMessage msg={msg} />
                        )}
                    </div>
                ))}

                {isLoading && (
                    <div className="flex gap-4">
                        <div className="w-10 h-10 rounded-full bg-indigo-50 flex items-center justify-center shrink-0 border border-indigo-100 shadow-sm">
                            <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
                        </div>
                        <div className="flex flex-col justify-center">
                            <div className="text-sm text-gray-500 flex items-center gap-2">
                                正在检索知识库并生成回答 <span className="animate-pulse">...</span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* 输入区（底部悬浮风格） */}
            <div className="absolute bottom-0 left-80 right-0 p-6 bg-gradient-to-t from-[#F9FAFB] via-[#F9FAFB] to-transparent">
                <div className="max-w-4xl mx-auto">

                    {/* ✅ 增加了浅灰边框 border-gray-200 和明显的中等投影 shadow-md */}
                    <div className="bg-white border border-gray-200 rounded-2xl shadow-md p-3 flex items-end gap-3 transition-shadow focus-within:shadow-lg focus-within:border-blue-300">

                        {/* 左侧模式选择 Pill */}
                        <div className="mb-1 ml-1 shrink-0">
                            <button
                                onClick={() => setMode(mode === 'rag' ? 'chat' : 'rag')}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                                    mode === 'rag' ? 'bg-green-50 text-green-600 border border-green-100' : 'bg-blue-50 text-blue-600 border border-blue-100'
                                }`}
                            >
                                {mode === 'rag' ? <Database className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                                {mode === 'rag' ? 'RAG 增强模式' : '普通对话'}
                                <ChevronDown className="w-3 h-3" />
                            </button>
                        </div>

                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="输入你的问题，或 / 选择技能，Shift + Enter 换行"
                            className="flex-1 bg-transparent resize-none outline-none text-[15px] px-2 py-2 text-gray-700 placeholder:text-gray-400 max-h-32 min-h-[44px]"
                            rows={1}
                        />

                        <div className="flex items-center gap-2 mb-1 shrink-0">
                            <button className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors">
                                <Paperclip className="w-5 h-5" />
                            </button>
                            <button
                                onClick={handleSend}
                                disabled={!input.trim() || isLoading}
                                className="p-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors shadow-sm"
                            >
                                <Send className="w-4 h-4 ml-0.5" />
                            </button>
                        </div>
                    </div>

                    <div className="text-center text-xs text-gray-400 mt-4 font-medium">
                        内容由 AI 生成，仅供参考，请核实重要信息。
                    </div>
                </div>
            </div>
        </div>
    );
}