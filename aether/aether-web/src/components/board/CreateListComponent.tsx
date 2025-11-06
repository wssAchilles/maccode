'use client';

import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import { useBoardStore } from '@/store/boardStore';

interface CreateListComponentProps {
  boardId: number;
}

export default function CreateListComponent({ boardId }: CreateListComponentProps) {
  const [isAdding, setIsAdding] = useState(false);
  const [name, setName] = useState('');
  const { addList } = useBoardStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!name.trim()) return;
    
    await addList(boardId, name.trim());
    setName('');
    setIsAdding(false);
  };

  const handleCancel = () => {
    setName('');
    setIsAdding(false);
  };

  if (!isAdding) {
    return (
      <button
        onClick={() => setIsAdding(true)}
        className="flex-shrink-0 w-72 p-4 bg-white/50 hover:bg-white/70 rounded-lg border-2 border-dashed border-gray-300 transition flex items-center justify-center gap-2 text-gray-600"
      >
        <Plus size={20} />
        添加列表
      </button>
    );
  }

  return (
    <div className="flex-shrink-0 w-72 p-4 bg-white rounded-lg shadow-lg">
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="输入列表标题..."
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900 bg-white placeholder-gray-400"
          autoFocus
        />
        <div className="flex items-center gap-2 mt-3">
          <button
            type="submit"
            disabled={!name.trim()}
            className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            添加列表
          </button>
          <button
            type="button"
            onClick={handleCancel}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-md transition"
            aria-label="取消"
          >
            <X size={16} />
          </button>
        </div>
      </form>
    </div>
  );
}
