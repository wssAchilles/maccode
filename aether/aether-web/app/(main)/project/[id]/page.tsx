'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useParams } from 'next/navigation';
import { ArrowLeft, Plus, LayoutGrid, Loader2 } from 'lucide-react';
import * as projectService from '@/services/projectService';
import * as boardService from '@/services/boardService';
import type { ProjectResponse, BoardResponse } from '@/types/api';

export default function ProjectDetailPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [boards, setBoards] = useState<BoardResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // 创建看板 Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [boardName, setBoardName] = useState('');

  useEffect(() => {
    loadProjectData();
  }, [projectId]);

  const loadProjectData = async () => {
    try {
      setLoading(true);
      const [projectData, boardsData] = await Promise.all([
        projectService.getProjectById(projectId),
        boardService.getBoardsByProject(projectId),
      ]);
      setProject(projectData);
      setBoards(boardsData);
      setError('');
    } catch (err: any) {
      setError(err.message || '加载项目数据失败');
      console.error('加载项目失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBoard = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!boardName.trim()) {
      alert('请输入看板名称');
      return;
    }

    try {
      setCreateLoading(true);
      await boardService.createBoard({
        name: boardName,
        projectId,
      });

      // 重新加载看板列表
      const boardsData = await boardService.getBoardsByProject(projectId);
      setBoards(boardsData);

      // 重置表单并关闭 Modal
      setBoardName('');
      setShowCreateModal(false);
    } catch (err: any) {
      alert(err.message || '创建看板失败');
      console.error('创建看板失败:', err);
    } finally {
      setCreateLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <Loader2 className="animate-spin text-indigo-600" size={48} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/dashboard')}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition"
              >
                <ArrowLeft size={20} />
                返回
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {project?.name}
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                  {project?.description || '暂无描述'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-bold text-gray-900">项目看板</h2>
            <p className="text-gray-600 mt-2">管理这个项目的所有看板</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-3 rounded-lg hover:bg-indigo-700 transition font-medium shadow-lg hover:shadow-xl"
          >
            <Plus size={20} />
            创建看板
          </button>
        </div>

        {/* Empty State */}
        {boards.length === 0 && (
          <div className="text-center py-12">
            <LayoutGrid className="mx-auto text-gray-400" size={64} />
            <h3 className="mt-4 text-lg font-semibold text-gray-900">
              还没有看板
            </h3>
            <p className="mt-2 text-gray-600">创建第一个看板开始管理任务</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-6 inline-flex items-center gap-2 bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 transition font-medium"
            >
              <Plus size={20} />
              创建看板
            </button>
          </div>
        )}

        {/* Boards Grid */}
        {boards.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {boards.map((board) => (
              <div
                key={board.id}
                onClick={() => router.push(`/board/${board.id}`)}
                className="bg-white rounded-lg shadow-md hover:shadow-xl transition cursor-pointer border border-gray-200 overflow-hidden group"
              >
                <div className="bg-gradient-to-r from-green-500 to-blue-500 h-2"></div>
                <div className="p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-indigo-600 transition">
                    {board.name}
                  </h3>
                  <div className="flex items-center justify-between text-xs text-gray-500 mt-4">
                    <span>
                      创建于{' '}
                      {new Date(board.createdAt).toLocaleDateString('zh-CN')}
                    </span>
                    <LayoutGrid size={16} className="text-green-400" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create Board Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
            <h3 className="text-2xl font-bold text-gray-900 mb-4">
              创建新看板
            </h3>
            <form onSubmit={handleCreateBoard}>
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  看板名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={boardName}
                  onChange={(e) => setBoardName(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900 bg-white placeholder-gray-400"
                  placeholder="输入看板名称"
                  required
                  autoFocus
                />
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setBoardName('');
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="flex-1 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {createLoading ? '创建中...' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
