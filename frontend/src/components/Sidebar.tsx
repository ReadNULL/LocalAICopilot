'use client';

import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, Loader2, Database, CheckCircle2, AlertCircle } from 'lucide-react';
import { uploadDocument } from '../lib/api';

interface UploadedFile {
    name: string;
    chunks: number;
}

export default function Sidebar() {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [status, setStatus] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
    const [files, setFiles] = useState<UploadedFile[]>([]);

    // 触发隐藏的 file input
    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    // 处理文件选择与上传
    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        setStatus(null);

        try {
            const response = await uploadDocument(file);
            // 上传成功，追加到本地列表
            setFiles((prev) => [...prev, { name: response.filename, chunks: response.chunks_count }]);
            setStatus({ type: 'success', text: `成功解析 ${response.chunks_count} 个知识块` });
        } catch (error) {
            setStatus({ type: 'error', text: '文档处理失败，请检查后端日志' });
        } finally {
            setIsUploading(false);
            // 清空 input 的值，确保下次选同一个文件也能触发 onChange
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    return (
        <div className="w-72 bg-gray-50 border-r border-gray-200 h-screen flex flex-col p-4">
            {/* 标题区 */}
            <div className="flex items-center gap-2 mb-8 px-2">
                <Database className="w-6 h-6 text-blue-600" />
                <h1 className="text-xl font-bold text-gray-800">Local Copilot</h1>
            </div>

            {/* 上传区 */}
            <div className="mb-6">
                <input
                    type="file"
                    className="hidden"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept=".pdf,.md,.doc,.docx,.txt"
                />
                <button
                    onClick={handleUploadClick}
                    disabled={isUploading}
                    className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-all ${
                        isUploading
                            ? 'bg-blue-100 text-blue-400 cursor-not-allowed'
                            : 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm'
                    }`}
                >
                    {isUploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <UploadCloud className="w-5 h-5" />}
                    {isUploading ? '正在解析入库...' : '上传本地文档'}
                </button>

                {/* 状态提示 */}
                {status && (
                    <div className={`mt-3 text-sm flex items-start gap-1.5 p-2 rounded-md ${
                        status.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                    }`}>
                        {status.type === 'success' ? (
                            <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        ) : (
                            <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        )}
                        <span>{status.text}</span>
                    </div>
                )}
            </div>

            {/* 文件列表区 */}
            <div className="flex-1 overflow-y-auto">
                <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 px-2">
                    当前会话知识库
                </h2>
                {files.length === 0 ? (
                    <div className="text-sm text-gray-400 px-2 italic">暂无文档，请上传文件以增强大模型记忆。</div>
                ) : (
                    <ul className="space-y-2">
                        {files.map((file, idx) => (
                            <li key={idx} className="flex items-center gap-3 p-3 bg-white border border-gray-100 rounded-lg shadow-sm">
                                <FileText className="w-5 h-5 text-gray-400 flex-shrink-0" />
                                <div className="overflow-hidden">
                                    <p className="text-sm font-medium text-gray-700 truncate" title={file.name}>
                                        {file.name}
                                    </p>
                                    <p className="text-xs text-gray-400">
                                        包含 {file.chunks} 个数据块
                                    </p>
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}