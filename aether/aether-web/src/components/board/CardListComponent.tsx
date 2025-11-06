/**
 * 列表组件
 * 可拖拽的列表容器，包含多个卡片
 */

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { GripVertical } from 'lucide-react';
import CardComponent from './CardComponent';
import CreateCardComponent from './CreateCardComponent';
import type { CardListResponse } from '@/types/api';

interface CardListComponentProps {
  list: CardListResponse;
}

export default function CardListComponent({
  list,
}: CardListComponentProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: list.id,
    data: {
      type: 'LIST',
      list,
    },
  });

  const dragStyle = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={dragStyle} className="flex-shrink-0 w-80">
      <div className="bg-gray-100 rounded-lg shadow-sm border border-gray-200">
        {/* List Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-300">
          <div className="flex items-center gap-2 flex-1">
            <div
              {...attributes}
              {...listeners}
              className="cursor-grab active:cursor-grabbing"
            >
              <GripVertical size={18} className="text-gray-400" />
            </div>
            <h3 className="font-semibold text-gray-900">{list.name}</h3>
            <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
              {list.cards.length}
            </span>
          </div>
        </div>

        {/* Cards Container */}
        <div className="p-3 space-y-2 max-h-[calc(100vh-250px)] overflow-y-auto">
          <SortableContext
            items={list.cards.map((card) => card.id)}
            strategy={verticalListSortingStrategy}
          >
            {list.cards.map((card) => (
              <CardComponent key={card.id} card={card} />
            ))}
          </SortableContext>

          {/* Empty State */}
          {list.cards.length === 0 && (
            <div className="text-center py-8 text-gray-400 text-sm">
              拖拽卡片到这里
            </div>
          )}
        </div>

        {/* Add Card Component */}
        <div className="p-3 border-t border-gray-300">
          <CreateCardComponent listId={list.id} />
        </div>
      </div>
    </div>
  );
}
