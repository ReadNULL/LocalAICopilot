'use client';

import React, { useRef, useState, useEffect } from 'react';
import {
    FileText, Loader2, Database, CheckCircle2, AlertCircle,
    Settings, Plus, Search, Layers, FileCode2, FileType2, AlignLeft
} from 'lucide-react';
import { uploadDocument, fetchDocuments, toggleDocument } from '../lib/api';

interface DocFile {
    id: string;
    name: string;
    chunks: number;
    status: 'processing' | 'ready' | 'error';
    enabled: boolean;
    createdAt: string;
    type: 'pdf' | 'md' | 'docx' | 'txt';
}

export default function Sidebar() {
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [files, setFiles] = useState<DocFile[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [activeTab, setActiveTab] = useState<'all' | 'enabled' | 'disabled'>('all');

    useEffect(() => {
        const loadDocs = async () => {
            try {
                const docs = await fetchDocuments();
                const formattedDocs: DocFile[] = docs.map(d => ({
                    id: d.id,
                    name: d.name,
                    chunks: d.chunks,
                    status: d.status,
                    enabled: d.enabled,
                    createdAt: d.created_at,
                    type: (d.name.split('.').pop()?.toLowerCase() || 'txt') as any
                }));
                setFiles(formattedDocs);
            } catch (error) {
                console.error("加载文档失败", error);
            }
        };
        loadDocs();
    }, []);

    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const tempId = Date.now().toString();
        const ext = file.name.split('.').pop()?.toLowerCase();
        let type: 'pdf' | 'md' | 'docx' | 'txt' = 'txt';
        if (['pdf', 'md', 'docx', 'txt'].includes(ext || '')) {
            type = ext as 'pdf' | 'md' | 'docx' | 'txt';
        }

        const newDoc: DocFile = {
            id: tempId,
            name: file.name,
            chunks: 0,
            status: 'processing',
            enabled: true,
            createdAt: '刚刚',
            type
        };

        setFiles(prev => [newDoc, ...prev]);
        setIsUploading(true);

        try {
            const res = await uploadDocument(file);
            setFiles(prev =>
                prev.map(doc =>
                    doc.id === tempId
                        ? { ...doc, chunks: res.chunks_count, status: 'ready' }
                        : doc
                )
            );
        } catch {
            setFiles(prev =>
                prev.map(doc =>
                    doc.id === tempId
                        ? { ...doc, status: 'error' }
                        : doc
                )
            );
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const handleToggleEnable = async (id: string, currentEnabled: boolean) => {
        // 乐观更新 UI
        setFiles(prev => prev.map(f => f.id === id ? { ...f, enabled: !currentEnabled } : f));
        try {
            await toggleDocument(id, !currentEnabled);
        } catch (error) {
            // 失败则回滚
            setFiles(prev => prev.map(f => f.id === id ? { ...f, enabled: currentEnabled } : f));
        }
    };

    const filteredFiles = files.filter(f => {
        const matchesSearch = f.name.toLowerCase().includes(searchTerm.toLowerCase());
        if (!matchesSearch) return false;
        if (activeTab === 'enabled') return f.enabled;
        if (activeTab === 'disabled') return !f.enabled;
        return true;
    });

    const getFileIcon = (type: string) => {
        const baseClass = "w-5 h-5 mt-0.5";
        switch(type) {
            case 'pdf': return <FileText className={`${baseClass} text-red-500`} fill="currentColor" fillOpacity={0.2} />;
            case 'md': return <FileCode2 className={`${baseClass} text-blue-500`} fill="currentColor" fillOpacity={0.2} />;
            case 'docx': return <FileType2 className={`${baseClass} text-blue-600`} fill="currentColor" fillOpacity={0.2} />;
            case 'txt': return <AlignLeft className={`${baseClass} text-gray-500`} fill="currentColor" fillOpacity={0.2} />;
            default: return <FileText className={`${baseClass} text-gray-400`} />;
        }
    };

    return (
        // 边框改为浅灰色 border-gray-200，并加了轻量阴影
        <div className="w-80 bg-white border-r border-gray-200 h-screen flex flex-col z-20 shadow-sm relative">

            {/* Header / Logo */}
            <div className="p-5 pb-4 border-b border-gray-100 flex items-center gap-3">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-sm">
                    <Database className="w-4 h-4 text-white" />
                </div>
                <h1 className="text-[17px] font-bold text-gray-900 tracking-tight">Local Copilot</h1>
            </div>

            <div className="p-5 flex flex-col gap-5 flex-1 overflow-hidden">

                {/* 知识库选择器 */}
                <div className="space-y-2">
                    <div className="text-xs font-medium text-gray-500">知识库</div>
                    <div className="flex items-center gap-2">
                        <select className="flex-1 bg-gray-50 border border-gray-200 text-gray-800 text-sm rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-blue-100 transition-shadow appearance-none cursor-pointer">
                            <option>默认知识库</option>
                        </select>
                        <button className="p-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors">
                            <Settings className="w-4 h-4" />
                        </button>
                        <button className="p-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors">
                            <Plus className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {/* 上传区域 */}
                <div>
                    <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileChange} />
                    <button
                        onClick={handleUploadClick}
                        disabled={isUploading}
                        className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all shadow-sm ${
                            isUploading
                                ? 'bg-blue-100 text-blue-400'
                                : 'bg-blue-600 text-white hover:bg-blue-700 hover:shadow'
                        }`}
                    >
                        {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                        {isUploading ? '解析中...' : '上传文档'}
                    </button>
                    <div className="text-center text-[11px] text-gray-400 mt-2">
                        支持: pdf / docx / md / txt
                    </div>
                </div>

                {/* 搜索框 */}
                <div className="relative">
                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                        type="text"
                        placeholder="搜索文档..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-9 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-100 transition-shadow placeholder:text-gray-400"
                    />
                </div>

                {/* Tabs */}
                <div className="flex bg-gray-100/80 p-1 rounded-lg text-xs font-medium">
                    <button
                        onClick={() => setActiveTab('all')}
                        className={`flex-1 py-1.5 rounded-md transition-all ${activeTab === 'all' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        全部 {files.length}
                    </button>
                    <button
                        onClick={() => setActiveTab('enabled')}
                        className={`flex-1 py-1.5 rounded-md transition-all ${activeTab === 'enabled' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        启用中 {files.filter(f => f.enabled).length}
                    </button>
                    <button
                        onClick={() => setActiveTab('disabled')}
                        className={`flex-1 py-1.5 rounded-md transition-all ${activeTab === 'disabled' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        未启用 {files.filter(f => !f.enabled).length}
                    </button>
                </div>

                {/* 文档列表 */}
                <div className="flex-1 overflow-y-auto -mx-2 px-2 divide-y divide-gray-100 hide-scrollbar">
                    {filteredFiles.length === 0 ? (
                        <div className="text-sm text-gray-400 text-center mt-10">暂无文档</div>
                    ) : (
                        filteredFiles.map(file => (
                            <div key={file.id} className="group p-3 hover:bg-gray-50 transition-colors cursor-default flex items-start gap-3">
                                {getFileIcon(file.type)}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between mb-1">
                                        <h3 className="text-[13px] font-medium text-gray-800 truncate" title={file.name}>
                                            {file.name}
                                        </h3>
                                        <span className="text-[10px] text-gray-400 whitespace-nowrap ml-2">
                                            {file.createdAt}
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <div className="text-[11px] text-gray-500 flex items-center gap-1.5">
                                            <span>Chunks: {file.chunks}</span>
                                            <span className="text-gray-300">·</span>

                                            {/* 状态指示器 */}
                                            {file.status === 'processing' && (
                                                <span className="text-amber-500 flex items-center gap-1">
                                                    <Loader2 className="w-3 h-3 animate-spin" /> 解析中
                                                </span>
                                            )}
                                            {file.status === 'ready' && (
                                                <span className="text-green-500 flex items-center gap-1">
                                                    已解析
                                                </span>
                                            )}
                                            {file.status === 'error' && (
                                                <span className="text-red-500 flex items-center gap-1">
                                                    解析失败
                                                </span>
                                            )}
                                        </div>

                                        {/* 启用开关 */}
                                        <label className="relative inline-flex items-center cursor-pointer">
                                            <input
                                                type="checkbox"
                                                className="sr-only peer"
                                                checked={file.enabled}
                                                onChange={() => handleToggleEnable(file.id, file.enabled)}
                                            />
                                            <div className="w-7 h-4 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-blue-600"></div>
                                        </label>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* 底部管理入口与头像区的重构 */}
            <div className="mt-auto flex flex-col">
                <div className="p-4 border-t border-gray-100 bg-gray-50/50">
                    <button className="w-full flex items-center justify-center gap-2 py-2.5 text-sm text-blue-600 font-medium bg-white hover:bg-blue-50 border border-blue-100 rounded-lg shadow-sm transition-colors">
                        <Layers className="w-4 h-4" />
                        管理知识库
                    </button>
                </div>

                {/* 头像区域独立占位在最下面，背景与底部融合 */}
                <div className="p-16 pb-6 border-t border-gray-100 bg-white flex justify-center">
                </div>
            </div>
        </div>
    );
}