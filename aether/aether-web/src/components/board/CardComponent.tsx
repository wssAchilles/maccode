/**
 * 卡片组件
 * 可拖拽的卡片，显示卡片标题和基本信息
 */

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Calendar } from 'lucide-react';
import type { CardResponse } from '@/types/api';
import { useBoardStore } from '@/store/boardStore';

interface CardComponentProps {
  card: CardResponse;
}

export default function CardComponent({ card }: CardComponentProps) {
  const { openCardModal } = useBoardStore();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: card.id,
    data: {
      type: 'CARD',
      card,
    },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const handleClick = (e: React.MouseEvent) => {
    // 阻止拖拽时触发点击
    if (isDragging) return;
    openCardModal(card.id);
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition cursor-pointer group"
      onClick={handleClick}
    >
      <div className="p-3">
        {/* Drag Handle */}
        <div className="flex items-start gap-2">
          <div
            {...attributes}
            {...listeners}
            className="opacity-0 group-hover:opacity-100 transition cursor-grab active:cursor-grabbing"
          >
            <GripVertical size={16} className="text-gray-400" />
          </div>
          <div className="flex-1">
            {/* Card Title */}
            <h4 className="text-sm font-medium text-gray-900 mb-2">
              {card.title}
            </h4>

            {/* Card Metadata */}
            <div className="flex items-center gap-3 text-xs text-gray-500">
              {card.dueDate && (
                <div className="flex items-center gap-1">
                  <Calendar size={12} />
                  <span>
                    {new Date(card.dueDate).toLocaleDateString('zh-CN')}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
