'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
    Send, Bot, User, AlertTriangle, Loader2, Database,
    FileText, Paperclip, ChevronDown, ChevronUp, FileCode2, FileType2, AlignLeft
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { streamChatWithAgent } from '../lib/api';

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
    validityCheck?: string;
    sources?: Source[];
    snippets?: string;
}

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
            <div className="w-10 h-10 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 border border-indigo-100 shadow-sm">
                <Bot className="w-6 h-6" />
            </div>
            <div className="flex-1 max-w-[85%]">
                <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-gray-800 text-sm">Local Copilot</span>
                    <span className="text-xs text-gray-400">{msg.timestamp}</span>
                </div>

                <div className="text-gray-700 text-[15px] leading-relaxed mb-4 prose prose-sm max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>

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

                {msg.validityCheck && (
                    <div className="mt-2 border border-gray-200 rounded-lg overflow-hidden bg-white shadow-sm">
                        <div className="px-4 py-3 bg-gray-50/50 text-xs font-medium text-gray-700">
                            事实核查报告
                        </div>
                        <div className="px-4 py-3 border-t border-gray-100 bg-white text-xs text-gray-600 leading-relaxed whitespace-pre-wrap">
                            {msg.validityCheck}
                        </div>
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

    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [mode, setMode] = useState<'rag' | 'chat'>('rag');
    const [showModeDropdown, setShowModeDropdown] = useState(false);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const modeDropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (modeDropdownRef.current && !modeDropdownRef.current.contains(e.target as Node)) {
                setShowModeDropdown(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    useEffect(() => {
        // 正在打字时用瞬间滚动 (auto)，打字结束后再用平滑滚动 (smooth)
        messagesEndRef.current?.scrollIntoView({ behavior: isLoading ? 'auto' : 'smooth' });
    }, [messages, isLoading]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        abortControllerRef.current?.abort();

        const historyToSend = messages
            .filter(msg => msg.id !== 'welcome' && !msg.content.includes('❌'))
            .slice(-6)
            .map(msg => ({
                role: msg.role,
                content: msg.content
            }));

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input.trim(),
            timestamp: getCurrentTime()
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        const aiMessageId = (Date.now() + 1).toString();
        const initialAiMessage: Message = {
            id: aiMessageId,
            role: 'assistant',
            content: '',
            timestamp: getCurrentTime(),
            sources: [],
            isHallucinated: false
        };
        setMessages((prev) => [...prev, initialAiMessage]);

        try {
            await streamChatWithAgent(
                {
                    query: userMessage.content,
                    mode,
                    history: historyToSend
                },
                {
                    onSource: (sources) => {
                        const combinedSnippets = sources
                            .filter(s => s.content)
                            .map((s, i) => `**来源 ${i + 1} (${s.docName})**:\n${s.content}`)
                            .join('\n\n---\n\n');

                        setMessages((prev) => prev.map(msg =>
                            msg.id === aiMessageId ? { ...msg, sources, snippets: combinedSnippets } : msg
                        ));
                    },
                    onChunk: (chunk) => {
                        setMessages((prev) => prev.map(msg =>
                            msg.id === aiMessageId ? { ...msg, content: msg.content + chunk } : msg
                        ));
                    },
                    onVerify: (isHallucinated, validityCheck) => {
                        setMessages((prev) => prev.map(msg =>
                            msg.id === aiMessageId ? { ...msg, isHallucinated, validityCheck } : msg
                        ));
                    },
                    onError: (err) => {
                        setMessages((prev) => prev.map(msg =>
                            msg.id === aiMessageId ? { ...msg, content: msg.content + `\n\n❌ 抱歉，发生错误: ${err}` } : msg
                        ));
                    },
                    onDone: () => {}
                }
            );
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
            <header className="h-16 border-b border-gray-200 bg-white flex items-center px-6 text-sm flex-shrink-0 shadow-sm z-10">
                <h2 className="font-semibold text-gray-800 text-base">新会话</h2>

                <div className="ml-8 flex items-center gap-6 text-gray-600">
                    <div className="relative" ref={modeDropdownRef}>
                        <button
                            onClick={() => setShowModeDropdown(!showModeDropdown)}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                                mode === 'rag'
                                    ? 'bg-green-50 border-green-200 text-green-700'
                                    : 'bg-blue-50 border-blue-200 text-blue-700'
                            }`}
                        >
                            {mode === 'rag' ? (
                                <>
                                    <Database className="w-3.5 h-3.5" />RAG 增强模式
                                </>
                            ) : (
                                <>
                                    <Bot className="w-3.5 h-3.5" />普通对话
                                </>
                            )}
                            <ChevronDown className={`w-3 h-3 ml-1 transition-transform ${showModeDropdown ? 'rotate-180' : ''}`} />
                        </button>
                        {showModeDropdown && (
                            <div className="absolute top-full mt-1 left-0 w-44 bg-white border border-gray-200 rounded-lg shadow-lg z-50 overflow-hidden">
                                <button
                                    onClick={() => { setMode('rag'); setShowModeDropdown(false); }}
                                    className={`w-full flex items-center gap-2 px-3 py-2.5 text-xs font-medium transition-colors hover:bg-gray-50 ${
                                        mode === 'rag' ? 'text-green-700 bg-green-50/50' : 'text-gray-600'
                                    }`}
                                >
                                    <Database className="w-3.5 h-3.5" />
                                    RAG 增强模式
                                    {mode === 'rag' && <span className="ml-auto text-green-500">✓</span>}
                                </button>
                                <button
                                    onClick={() => { setMode('chat'); setShowModeDropdown(false); }}
                                    className={`w-full flex items-center gap-2 px-3 py-2.5 text-xs font-medium transition-colors hover:bg-gray-50 ${
                                        mode === 'chat' ? 'text-blue-700 bg-blue-50/50' : 'text-gray-600'
                                    }`}
                                >
                                    <Bot className="w-3.5 h-3.5" />
                                    普通对话
                                    {mode === 'chat' && <span className="ml-auto text-blue-500">✓</span>}
                                </button>
                            </div>
                        )}
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

            <div className="absolute bottom-0 left-80 right-0 p-6 bg-gradient-to-t from-[#F9FAFB] via-[#F9FAFB] to-transparent">
                <div className="max-w-4xl mx-auto">

                    <div className="bg-white border border-gray-200 rounded-2xl shadow-md p-3 flex items-end gap-3 transition-shadow focus-within:shadow-lg focus-within:border-blue-300">

                        <div className="mb-0.5 ml-1 shrink-0 flex items-center gap-2">
                            <button
                                onClick={() => setMode('rag')}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                                    mode === 'rag' 
                                        ? 'bg-green-50 text-green-700 border border-green-200 shadow-sm' 
                                        : 'bg-gray-50 text-gray-500 border border-transparent hover:bg-gray-100'
                                }`}
                            >
                                <Database className="w-3.5 h-3.5" />
                                RAG 增强模式
                            </button>

                            <button
                                onClick={() => setMode('chat')}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                                    mode === 'chat' 
                                        ? 'bg-blue-50 text-blue-700 border border-blue-200 shadow-sm' 
                                        : 'bg-gray-50 text-gray-500 border border-transparent hover:bg-gray-100'
                                }`}
                            >
                                <Bot className="w-3.5 h-3.5" />
                                普通对话
                            </button>
                        </div>

                        {/* 单行文字垂直居中 */}
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="输入你的问题，或 / 选择技能，Shift + Enter 换行"
                            className="flex-1 bg-transparent resize-none outline-none text-[15px] leading-normal px-2 py-2.5 text-gray-700 placeholder:text-gray-400 max-h-32"
                            rows={1}
                        />

                        <div className="flex items-center gap-2 mb-0.5 shrink-0">
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