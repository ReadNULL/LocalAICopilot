import axios from 'axios';

// ================================
// 基础配置
// ================================
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ================================
// 通用错误处理
// ================================
const handleError = (error: any, tag: string): never => {
  console.error(`${tag} Error:`, error?.response?.data || error.message);
  throw error;
};

// ================================
// 1️⃣ Chat
// ================================

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

export interface ChatRequest {
  query: string;
  mode?: 'rag' | 'chat'; // 默认 rag
  doc_ids?: string[]; // 参与检索的文档
  history?: ChatMessage[]; // 历史对话上下文
}

export interface Source {
  docName: string;
  chunkId: number;
  score: number;
  content?: string; // 🔥 为后续“检索片段展示”准备
}

export interface ChatResponse {
  answer: string;
  is_hallucinated?: boolean;
  sources?: Source[];
}

export const chatWithAgent = async (
  payload: ChatRequest
): Promise<ChatResponse> => {
  try {
    const res = await apiClient.post('/api/chat/', payload);
    return res.data;
  } catch (error) {
    return handleError(error, 'Chat API');
  }
};

// ================================
// 2️⃣ 上传文档
// ================================

export interface UploadResponse {
  id: string;
  filename: string;
  chunks_count: number;
  status: 'processing' | 'ready' | 'error';
}

export const uploadDocument = async (
  file: File
): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await apiClient.post('/api/rag/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return res.data;
  } catch (error) {
    return handleError(error, 'Upload API');
  }
};

// ================================
// 3️⃣ 文档管理
// ================================

export interface DocumentItem {
  id: string;
  name: string;
  chunks: number;
  status: 'processing' | 'ready' | 'error';
  enabled: boolean;
  created_at: string;
}

// 获取文档列表
export const fetchDocuments = async (): Promise<DocumentItem[]> => {
  try {
    const res = await apiClient.get('/api/rag/documents');
    return res.data;
  } catch (error) {
    return handleError(error, 'Fetch Documents');
  }
};

// 启用 / 禁用文档
export const toggleDocument = async (
  id: string,
  enabled: boolean
) => {
  try {
    await apiClient.patch(`/api/rag/document/${id}`, { enabled });
  } catch (error) {
    handleError(error, 'Toggle Document');
  }
};

// 删除文档
export const deleteDocument = async (id: string) => {
  try {
    await apiClient.delete(`/api/rag/document/${id}`);
  } catch (error) {
    handleError(error, 'Delete Document');
  }
};

// ================================
// 4️⃣ 知识库
// ================================

export interface KnowledgeBase {
  id: string;
  name: string;
}

// 获取知识库列表
export const fetchKnowledgeBases = async (): Promise<KnowledgeBase[]> => {
  try {
    const res = await apiClient.get('/api/kb');
    return res.data;
  } catch (error) {
    return handleError(error, 'Fetch KB');
  }
};

// ================================
// 5️⃣ 健康检查
// ================================

export const checkHealth = async (): Promise<boolean> => {
  try {
    await apiClient.get('/health');
    return true;
  } catch {
    return false;
  }
};

// ================================
// 流式对话接口 (SSE)
// ================================
export const streamChatWithAgent = async (
    payload: ChatRequest,
    callbacks: {
        onSource: (sources: Source[]) => void;
        onChunk: (chunk: string) => void;
        onVerify: (isHallucinated: boolean) => void;
        onError: (err: string) => void;
        onDone: () => void;
    }
) => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/chat/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.body) throw new Error('No response body stream');

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ''; // 保留未完整的片段

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6);
                    try {
                        const data = JSON.parse(dataStr);
                        if (data.type === 'sources') callbacks.onSource(data.data);
                        else if (data.type === 'chunk') callbacks.onChunk(data.content);
                        else if (data.type === 'verification') callbacks.onVerify(data.is_hallucinated);
                        else if (data.type === 'error') callbacks.onError(data.content);
                        else if (data.type === 'done') callbacks.onDone();
                    } catch (e) {
                        console.error("JSON parse error for SSE message:", dataStr);
                    }
                }
            }
        }
    } catch (error: any) {
        callbacks.onError(error.message);
    }
};