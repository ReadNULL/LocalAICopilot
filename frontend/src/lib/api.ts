import axios from 'axios';

// 读取我们在 .env.local 中配置的后端地址
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// ==========================================
// 1. 对话接口 (对应 backend/app/api/chat.py)
// ==========================================
export interface ChatResponse {
    answer: string;
    is_hallucinated: boolean;
}

export const chatWithAgent = async (query: string): Promise<ChatResponse> => {
    try {
        const response = await apiClient.post('/api/chat/', { query });
        return response.data;
    } catch (error) {
        console.error('Chat API Error:', error);
        throw error;
    }
};

// ==========================================
// 2. 文件上传接口 (对应 backend/app/api/rag.py)
// ==========================================
export interface UploadResponse {
    filename: string;
    message: string;
    chunks_count: number;
}

export const uploadDocument = async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    try {
        // 注意：上传文件必须使用 multipart/form-data
        const response = await apiClient.post('/api/rag/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    } catch (error) {
        console.error('Upload API Error:', error);
        throw error;
    }
};