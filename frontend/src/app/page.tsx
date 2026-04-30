import Sidebar from '@/components/Sidebar';
import ChatWindow from '@/components/ChatWindow';

export default function Home() {
  return (
    <main className="flex h-screen w-full bg-white overflow-hidden text-gray-900">
      {/* 左侧侧边栏：文件管理 */}
      <Sidebar />

      {/* 右侧主聊天区 */}
      <ChatWindow />
    </main>
  );
}