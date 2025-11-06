'use client';

import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import { useBoardStore } from '@/store/boardStore';

interface CreateCardComponentProps {
  listId: number;
}

export default function CreateCardComponent({ listId }: CreateCardComponentProps) {
  const [isAdding, setIsAdding] = useState(false);
  const [title, setTitle] = useState('');
  const { addCard } = useBoardStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!title.trim()) return;
    
    await addCard(listId, title.trim());
    setTitle('');
    setIsAdding(false);
  };

  const handleCancel = () => {
    setTitle('');
    setIsAdding(false);
  };

  if (!isAdding) {
    return (
      <button
        onClick={() => setIsAdding(true)}
        className="w-full px-3 py-2 text-left text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition flex items-center gap-2"
      >
        <Plus size={16} />
        添加卡片
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="p-2 bg-white rounded-lg shadow-sm">
      <textarea
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="输入卡片标题..."
        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md resize-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900 bg-white placeholder-gray-400"
        rows={3}
        autoFocus
      />
      <div className="flex items-center gap-2 mt-2">
        <button
          type="submit"
          disabled={!title.trim()}
          className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          添加
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
  );
}
