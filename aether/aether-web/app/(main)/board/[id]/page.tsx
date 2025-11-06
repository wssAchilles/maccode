'use client';

import { useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { useBoardStore } from '@/store/boardStore';
import BoardContainer from '@/components/board/BoardContainer';
import CardModal from '@/components/card/CardModal';

export default function BoardPage() {
  const router = useRouter();
  const params = useParams();
  const boardId = Number(params.id);

  const { board, loading, error, fetchBoard, clearBoard, connectWebSocket, disconnectWebSocket } = useBoardStore();

  useEffect(() => {
    fetchBoard(boardId);
    connectWebSocket(boardId);

    // 清理:离开页面时清空看板数据并断开 WebSocket
    return () => {
      disconnectWebSocket();
      clearBoard();
    };
  }, [boardId, fetchBoard, clearBoard, connectWebSocket, disconnectWebSocket]);

  // Loading State
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="animate-spin text-indigo-600 mx-auto mb-4" size={48} />
          <p className="text-gray-600">加载看板中...</p>
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 text-lg mb-4">{error}</p>
          <button
            onClick={() => router.push('/dashboard')}
            className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 transition"
          >
            返回项目列表
          </button>
        </div>
      </div>
    );
  }

  if (!board) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-full px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push(`/project/${board.projectId}`)}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition"
              >
                <ArrowLeft size={20} />
                返回项目
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {board.name}
                </h1>
                <p className="text-xs text-gray-500 mt-1">
                  {board.lists.length} 个列表 •{' '}
                  {board.lists.reduce((acc, list) => acc + list.cards.length, 0)}{' '}
                  张卡片
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Board Content */}
      <main className="p-6">
        <BoardContainer boardId={boardId} />
      </main>

      {/* Card Details Modal */}
      <CardModal />
    </div>
  );
}
