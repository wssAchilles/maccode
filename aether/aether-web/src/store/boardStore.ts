/**
 * 看板状态管理 Store (Zustand)
 * 负责管理看板、列表、卡片的状态和拖拽操作
 * 集成 WebSocket 实现实时同步
 */

import { create } from 'zustand';
import { Client } from '@stomp/stompjs';
import SockJS from 'sockjs-client';
import type { FullBoardResponse, CardResponse, CardListResponse } from '@/types/api';
import * as boardService from '@/services/boardService';
import * as cardService from '@/services/cardService';
import * as cardListService from '@/services/cardListService';

interface BoardState {
  board: FullBoardResponse | null;
  loading: boolean;
  error: string | null;
  stompClient: Client | null;
  
  // Modal State
  isCardModalOpen: boolean;
  currentCardId: number | null;
  
  // Actions - 基础
  fetchBoard: (boardId: number) => Promise<void>;
  clearBoard: () => void;
  
  // Actions - 创建
  addList: (boardId: number, name: string) => Promise<void>;
  addCard: (listId: number, title: string) => Promise<void>;
  
  // Actions - Modal
  openCardModal: (cardId: number) => void;
  closeCardModal: () => void;
  updateCardDetails: (cardId: number, data: { title?: string; description?: string }) => Promise<void>;
  
  // Actions - 乐观更新 - 列表排序
  optimisticMoveList: (sourceIndex: number, destIndex: number) => void;
  moveList: (boardId: number, sourceIndex: number, destIndex: number) => Promise<void>;
  
  // Actions - 乐观更新 - 卡片移动
  optimisticMoveCard: (
    cardId: number,
    sourceListId: number,
    destListId: number,
    destIndex: number
  ) => void;
  moveCard: (
    cardId: number,
    sourceListId: number,
    destListId: number,
    destIndex: number
  ) => Promise<void>;
  
  // Actions - WebSocket
  connectWebSocket: (boardId: number) => void;
  disconnectWebSocket: () => void;
  handleRealtimeCardMove: (payload: any) => void;
  handleRealtimeCardCreated: (payload: any) => void;
  handleRealtimeListCreated: (payload: any) => void;
}

export const useBoardStore = create<BoardState>((set, get) => ({
  board: null,
  loading: false,
  error: null,
  stompClient: null,
  isCardModalOpen: false,
  currentCardId: null,

  /**
   * 获取看板完整数据
   */
  fetchBoard: async (boardId: number) => {
    set({ loading: true, error: null });
    try {
      const board = await boardService.getFullBoard(boardId);
      set({ board, loading: false });
    } catch (error: any) {
      set({ error: error.message || '获取看板失败', loading: false });
    }
  },

  /**
   * 清空看板状态
   */
  clearBoard: () => {
    set({ board: null, loading: false, error: null });
  },

  /**
   * 添加列表
   */
  addList: async (boardId: number, name: string) => {
    try {
      const newList = await cardListService.createCardList(boardId, { name, boardId });
      
      const { board } = get();
      if (!board) return;
      
      set({
        board: {
          ...board,
          lists: [...board.lists, { ...newList, cards: [] }],
        },
      });
    } catch (error: any) {
      console.error('创建列表失败:', error);
      set({ error: error.message || '创建列表失败' });
    }
  },

  /**
   * 添加卡片
   */
  addCard: async (listId: number, title: string) => {
    try {
      const newCard = await cardService.createCard({ listId, title });
      
      const { board } = get();
      if (!board) return;
      
      const newLists = board.lists.map((list) =>
        list.id === listId
          ? { ...list, cards: [...list.cards, newCard] }
          : list
      );
      
      set({
        board: {
          ...board,
          lists: newLists,
        },
      });
    } catch (error: any) {
      console.error('创建卡片失败:', error);
      set({ error: error.message || '创建卡片失败' });
    }
  },

  /**
   * 乐观更新 - 立即更新本地列表顺序
   */
  optimisticMoveList: (sourceIndex: number, destIndex: number) => {
    const { board } = get();
    if (!board) return;

    const newLists = [...board.lists];
    const [movedList] = newLists.splice(sourceIndex, 1);
    newLists.splice(destIndex, 0, movedList);

    set({
      board: {
        ...board,
        lists: newLists,
      },
    });
  },

  /**
   * 移动列表 - 调用后端 API
   */
  moveList: async (boardId: number, sourceIndex: number, destIndex: number) => {
    const { board } = get();
    if (!board) return;

    // 先执行乐观更新
    get().optimisticMoveList(sourceIndex, destIndex);

    try {
      // 获取新的列表 ID 顺序
      const listIds = board.lists.map((list) => list.id);
      const newListIds = [...listIds];
      const [movedId] = newListIds.splice(sourceIndex, 1);
      newListIds.splice(destIndex, 0, movedId);

      // 调用后端 API
      await boardService.updateListOrder(boardId, newListIds);
    } catch (error: any) {
      // 如果失败，重新获取数据恢复状态
      console.error('移动列表失败:', error);
      get().fetchBoard(boardId);
    }
  },

  /**
   * 乐观更新 - 立即更新本地卡片位置
   */
  optimisticMoveCard: (
    cardId: number,
    sourceListId: number,
    destListId: number,
    destIndex: number
  ) => {
    const { board } = get();
    if (!board) return;

    const newLists = [...board.lists];
    const sourceListIndex = newLists.findIndex(
      (list) => list.id === sourceListId
    );
    const destListIndex = newLists.findIndex((list) => list.id === destListId);

    if (sourceListIndex === -1 || destListIndex === -1) return;

    // 从源列表移除卡片
    const sourceList = { ...newLists[sourceListIndex] };
    const cardIndex = sourceList.cards.findIndex((card) => card.id === cardId);
    if (cardIndex === -1) return;

    const [movedCard] = sourceList.cards.splice(cardIndex, 1);
    newLists[sourceListIndex] = sourceList;

    // 添加到目标列表
    const destList = { ...newLists[destListIndex] };
    destList.cards.splice(destIndex, 0, movedCard);
    newLists[destListIndex] = destList;

    set({
      board: {
        ...board,
        lists: newLists,
      },
    });
  },

  /**
   * 移动卡片 - 调用后端 API
   */
  moveCard: async (
    cardId: number,
    sourceListId: number,
    destListId: number,
    destIndex: number
  ) => {
    const { board } = get();
    if (!board) return;

    // 先执行乐观更新
    get().optimisticMoveCard(cardId, sourceListId, destListId, destIndex);

    try {
      // 计算新的 position
      // 如果是空列表，position 为 1.0
      // 否则根据目标位置计算
      const destList = board.lists.find((list) => list.id === destListId);
      if (!destList) return;

      let newPosition: number;
      
      if (destList.cards.length === 0) {
        newPosition = 1.0;
      } else if (destIndex === 0) {
        // 插入到最前面
        newPosition = destList.cards[0].position / 2;
      } else if (destIndex >= destList.cards.length) {
        // 插入到最后面
        newPosition = destList.cards[destList.cards.length - 1].position + 1.0;
      } else {
        // 插入到中间
        const prevPosition = destList.cards[destIndex - 1].position;
        const nextPosition = destList.cards[destIndex].position;
        newPosition = (prevPosition + nextPosition) / 2;
      }

      // 调用后端 API
      await cardService.moveCard(cardId, {
        targetListId: destListId,
        newPosition,
      });
    } catch (error: any) {
      // 如果失败，重新获取数据恢复状态
      console.error('移动卡片失败:', error);
      if (board) {
        get().fetchBoard(board.id);
      }
    }
  },

  /**
   * 连接 WebSocket
   */
  connectWebSocket: (boardId: number) => {
    const { stompClient } = get();
    
    // 如果已连接，先断开
    if (stompClient?.connected) {
      console.log('WebSocket 已连接，跳过重复连接');
      return;
    }
    
    console.log(`正在连接 WebSocket for board ${boardId}...`);
    
    // 创建 STOMP 客户端
    const client = new Client({
      webSocketFactory: () => new SockJS('http://localhost:8080/ws'),
      debug: (str) => {
        console.log('[STOMP Debug]', str);
      },
      reconnectDelay: 5000,
      heartbeatIncoming: 4000,
      heartbeatOutgoing: 4000,
    });
    
    // 连接成功回调
    client.onConnect = () => {
      console.log('✅ WebSocket 连接成功');
      
      // 订阅看板主题
      client.subscribe(`/topic/board/${boardId}`, (message) => {
        try {
          const event = JSON.parse(message.body);
          console.log('📨 收到 WebSocket 消息:', event);
          
          // 根据事件类型分发处理
          switch (event.actionType) {
            case 'CARD_MOVED':
              get().handleRealtimeCardMove(event.payload);
              break;
            case 'CARD_CREATED':
              get().handleRealtimeCardCreated(event.payload);
              break;
            case 'LIST_CREATED':
              get().handleRealtimeListCreated(event.payload);
              break;
            default:
              console.log('未处理的事件类型:', event.actionType);
          }
        } catch (error) {
          console.error('处理 WebSocket 消息失败:', error);
        }
      });
    };
    
    // 连接错误回调
    client.onStompError = (frame) => {
      console.error('❌ WebSocket 连接错误:', frame.headers['message']);
      console.error('详细信息:', frame.body);
    };
    
    // 激活连接
    client.activate();
    set({ stompClient: client });
  },

  /**
   * 断开 WebSocket
   */
  disconnectWebSocket: () => {
    const { stompClient } = get();
    if (stompClient?.connected) {
      console.log('断开 WebSocket 连接...');
      stompClient.deactivate();
      set({ stompClient: null });
    }
  },

  /**
   * 处理实时卡片移动事件
   */
  handleRealtimeCardMove: (payload: any) => {
    console.log('🔄 处理实时卡片移动:', payload);
    
    const { board } = get();
    if (!board) return;
    
    const { cardId, targetListId, newPosition } = payload;
    
    // 找到卡片和列表
    let movedCard: CardResponse | null = null;
    let sourceListId: number | null = null;
    
    const newLists = board.lists.map((list) => {
      const cardIndex = list.cards.findIndex((card) => card.id === cardId);
      if (cardIndex !== -1) {
        movedCard = list.cards[cardIndex];
        sourceListId = list.id;
        return {
          ...list,
          cards: list.cards.filter((card) => card.id !== cardId),
        };
      }
      return list;
    });
    
    if (!movedCard || sourceListId === null) {
      console.warn('未找到要移动的卡片');
      return;
    }
    
    // 更新卡片位置并添加到目标列表
    const updatedCard: CardResponse = { ...(movedCard as CardResponse), position: newPosition };
    const finalLists = newLists.map((list) => {
      if (list.id === targetListId) {
        const cards = [...list.cards, updatedCard].sort((a, b) => a.position - b.position);
        return { ...list, cards };
      }
      return list;
    });
    
    set({ board: { ...board, lists: finalLists } });
  },

  /**
   * 处理实时卡片创建事件
   */
  handleRealtimeCardCreated: (payload: any) => {
    console.log('➕ 处理实时卡片创建:', payload);
    
    const { board } = get();
    if (!board) return;
    
    const newCard: CardResponse = payload;
    
    const newLists = board.lists.map((list) => {
      if (list.id === newCard.listId) {
        return {
          ...list,
          cards: [...list.cards, newCard],
        };
      }
      return list;
    });
    
    set({ board: { ...board, lists: newLists } });
  },

  /**
   * 处理实时列表创建事件
   */
  handleRealtimeListCreated: (payload: any) => {
    console.log('➕ 处理实时列表创建:', payload);
    
    const { board } = get();
    if (!board) return;
    
    const newList: CardListResponse = { ...payload, cards: [] };
    
    set({
      board: {
        ...board,
        lists: [...board.lists, newList],
      },
    });
  },

  /**
   * 打开卡片详情模态框
   */
  openCardModal: (cardId: number) => {
    set({ isCardModalOpen: true, currentCardId: cardId });
  },

  /**
   * 关闭卡片详情模态框
   */
  closeCardModal: () => {
    set({ isCardModalOpen: false, currentCardId: null });
  },

  /**
   * 更新卡片详情
   */
  updateCardDetails: async (cardId: number, data: { title?: string; description?: string }) => {
    try {
      // 1. 乐观更新本地状态
      const { board } = get();
      if (!board) return;

      const newLists = board.lists.map((list) => ({
        ...list,
        cards: list.cards.map((card) =>
          card.id === cardId
            ? { ...card, ...data }
            : card
        ),
      }));

      set({ board: { ...board, lists: newLists } });

      // 2. 调用 API 更新后端
      await cardService.updateCard(cardId, data);
    } catch (error: any) {
      console.error('更新卡片详情失败:', error);
      set({ error: error.message || '更新卡片详情失败' });
    }
  },
}));
