/**
 * 看板容器组件
 * 实现拖拽功能的核心组件
 * 处理列表拖拽和卡片拖拽
 */

'use client';

import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
  DragOverEvent,
} from '@dnd-kit/core';
import { SortableContext, horizontalListSortingStrategy } from '@dnd-kit/sortable';
import { useState } from 'react';
import CardListComponent from './CardListComponent';
import CardComponent from './CardComponent';
import CreateListComponent from './CreateListComponent';
import { useBoardStore } from '@/store/boardStore';
import type { CardResponse, CardListResponse } from '@/types/api';

interface BoardContainerProps {
  boardId: number;
}

export default function BoardContainer({ boardId }: BoardContainerProps) {
  const { board, moveList, moveCard } = useBoardStore();
  const [activeItem, setActiveItem] = useState<{
    type: 'LIST' | 'CARD';
    data: CardListResponse | CardResponse;
  } | null>(null);

  // 配置拖拽传感器
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 移动 8px 后才触发拖拽
      },
    })
  );

  if (!board) {
    return null;
  }

  /**
   * 拖拽开始
   */
  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    setActiveItem(active.data.current as any);
  };

  /**
   * 拖拽过程中 (可选，用于实时预览)
   */
  const handleDragOver = (event: DragOverEvent) => {
    // 可以在这里实现实时预览效果
  };

  /**
   * 拖拽结束 - 核心逻辑
   */
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveItem(null);

    if (!over) return;

    const activeData = active.data.current as any;
    const overData = over.data.current as any;

    // 场景1：拖拽列表
    if (activeData?.type === 'LIST' && overData?.type === 'LIST') {
      const oldIndex = board.lists.findIndex((list) => list.id === active.id);
      const newIndex = board.lists.findIndex((list) => list.id === over.id);

      if (oldIndex !== newIndex) {
        moveList(boardId, oldIndex, newIndex);
      }
      return;
    }

    // 场景2：拖拽卡片
    if (activeData?.type === 'CARD') {
      const activeCard = activeData.card as CardResponse;
      const sourceListId = activeCard.listId;

      // 2.1: 卡片拖到另一张卡片上
      if (overData?.type === 'CARD') {
        const overCard = overData.card as CardResponse;
        const destListId = overCard.listId;

        const destList = board.lists.find((list) => list.id === destListId);
        if (!destList) return;

        const destIndex = destList.cards.findIndex(
          (card) => card.id === overCard.id
        );

        moveCard(activeCard.id, sourceListId, destListId, destIndex);
        return;
      }

      // 2.2: 卡片拖到列表上（空列表或列表底部）
      if (overData?.type === 'LIST') {
        const destList = overData.list as CardListResponse;
        const destListId = destList.id;
        const destIndex = destList.cards.length; // 添加到列表末尾

        moveCard(activeCard.id, sourceListId, destListId, destIndex);
        return;
      }
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4">
        <SortableContext
          items={board.lists.map((list) => list.id)}
          strategy={horizontalListSortingStrategy}
        >
          {board.lists.map((list) => (
            <CardListComponent key={list.id} list={list} />
          ))}
        </SortableContext>

        {/* Add List Component */}
        <CreateListComponent boardId={boardId} />
      </div>

      {/* Drag Overlay */}
      <DragOverlay>
        {activeItem?.type === 'LIST' && (
          <div className="w-80 opacity-90">
            <CardListComponent list={activeItem.data as CardListResponse} />
          </div>
        )}
        {activeItem?.type === 'CARD' && (
          <div className="w-80 opacity-90">
            <CardComponent card={activeItem.data as CardResponse} />
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
