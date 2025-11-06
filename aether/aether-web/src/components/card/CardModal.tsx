/**
 * 卡片详情模态框
 * 用于查看和编辑卡片的详细信息
 */

'use client';

import { useState, useEffect } from 'react';
import { X, Calendar, Users } from 'lucide-react';
import { useBoardStore } from '@/store/boardStore';

export default function CardModal() {
  const { 
    isCardModalOpen, 
    currentCardId, 
    board, 
    closeCardModal, 
    updateCardDetails 
  } = useBoardStore();

  const [editableTitle, setEditableTitle] = useState('');
  const [editableDescription, setEditableDescription] = useState('');
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [isEditingDescription, setIsEditingDescription] = useState(false);

  // 查找当前卡片
  const currentCard = board?.lists
    .flatMap(list => list.cards)
    .find(card => card.id === currentCardId);

  // 当卡片变化时，更新本地编辑状态
  useEffect(() => {
    if (currentCard) {
      setEditableTitle(currentCard.title);
      setEditableDescription(currentCard.description || '');
    }
  }, [currentCard]);

  // 如果模态框未打开或没有卡片，返回 null
  if (!isCardModalOpen || !currentCard) {
    return null;
  }

  // 保存标题
  const handleTitleBlur = async () => {
    setIsEditingTitle(false);
    if (editableTitle.trim() && editableTitle !== currentCard.title) {
      await updateCardDetails(currentCard.id, { title: editableTitle.trim() });
    } else {
      // 恢复原值
      setEditableTitle(currentCard.title);
    }
  };

  // 保存描述
  const handleDescriptionBlur = async () => {
    setIsEditingDescription(false);
    if (editableDescription !== (currentCard.description || '')) {
      await updateCardDetails(currentCard.id, { description: editableDescription });
    }
  };

  // 关闭模态框
  const handleClose = () => {
    closeCardModal();
    setIsEditingTitle(false);
    setIsEditingDescription(false);
  };

  // 点击遮罩层关闭
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      handleClose();
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleOverlayClick}
    >
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-gray-200">
          <div className="flex-1 pr-8">
            {/* Title - 可编辑 */}
            {isEditingTitle ? (
              <input
                type="text"
                value={editableTitle}
                onChange={(e) => setEditableTitle(e.target.value)}
                onBlur={handleTitleBlur}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleTitleBlur();
                  if (e.key === 'Escape') {
                    setEditableTitle(currentCard.title);
                    setIsEditingTitle(false);
                  }
                }}
                className="w-full text-2xl font-bold text-gray-900 border-2 border-indigo-500 rounded px-2 py-1 focus:outline-none"
                placeholder="卡片标题"
                aria-label="卡片标题"
                autoFocus
              />
            ) : (
              <h2
                className="text-2xl font-bold text-gray-900 cursor-text hover:bg-gray-50 rounded px-2 py-1 -ml-2"
                onClick={() => setIsEditingTitle(true)}
              >
                {currentCard.title}
              </h2>
            )}
            <p className="text-sm text-gray-500 mt-1">
              卡片 ID: {currentCard.id}
            </p>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition"
            aria-label="关闭"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Description */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">描述</h3>
            {isEditingDescription ? (
              <textarea
                value={editableDescription}
                onChange={(e) => setEditableDescription(e.target.value)}
                onBlur={handleDescriptionBlur}
                placeholder="添加更详细的描述..."
                className="w-full min-h-[120px] border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-vertical"
                autoFocus
              />
            ) : (
              <div
                onClick={() => setIsEditingDescription(true)}
                className="min-h-[80px] border border-gray-200 rounded-lg px-3 py-2 cursor-text hover:bg-gray-50 transition whitespace-pre-wrap"
              >
                {currentCard.description || (
                  <span className="text-gray-400">点击添加描述...</span>
                )}
              </div>
            )}
          </div>

          {/* Metadata Section */}
          <div className="grid grid-cols-2 gap-4">
            {/* Due Date - 占位 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <Calendar size={16} />
                截止日期
              </h3>
              <div className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-500">
                {currentCard.dueDate
                  ? new Date(currentCard.dueDate).toLocaleDateString('zh-CN', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })
                  : '未设置'}
              </div>
            </div>

            {/* Assignees - 占位 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <Users size={16} />
                分配成员
              </h3>
              <div className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-500">
                未分配 (功能开发中)
              </div>
            </div>
          </div>

          {/* Timestamps */}
          <div className="pt-4 border-t border-gray-200">
            <div className="grid grid-cols-2 gap-4 text-xs text-gray-500">
              <div>
                <span className="font-medium">创建时间：</span>
                {new Date(currentCard.createdAt).toLocaleString('zh-CN')}
              </div>
              <div>
                <span className="font-medium">最后更新：</span>
                {new Date(currentCard.updatedAt).toLocaleString('zh-CN')}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <div className="flex justify-end gap-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
