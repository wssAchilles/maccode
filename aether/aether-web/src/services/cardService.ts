/**
 * 卡片相关 API 服务
 * 严格对应后端 CardController 的端点
 */

import apiClient from '@/lib/apiClient';
import type {
  CardResponse,
  CreateCardRequest,
  UpdateCardRequest,
  MoveCardRequest,
} from '@/types/api';

/**
 * 获取卡片详情
 * GET /api/v1/cards/{cardId}
 */
export const getCardById = async (cardId: number): Promise<CardResponse> => {
  const response = await apiClient.get<CardResponse>(`/cards/${cardId}`);
  return response.data;
};

/**
 * 创建新卡片
 * POST /api/v1/cards?listId={listId}
 */
export const createCard = async (
  data: CreateCardRequest
): Promise<CardResponse> => {
  const response = await apiClient.post<CardResponse>(
    `/cards?listId=${data.listId}`,
    { title: data.title, description: data.description, dueDate: data.dueDate }
  );
  return response.data;
};

/**
 * 更新卡片
 * PUT /api/v1/cards/{cardId}
 */
export const updateCard = async (
  cardId: number,
  data: UpdateCardRequest
): Promise<CardResponse> => {
  const response = await apiClient.put<CardResponse>(`/cards/${cardId}`, data);
  return response.data;
};

/**
 * 移动卡片（拖拽卡片）
 * PATCH /api/v1/cards/{cardId}/move
 */
export const moveCard = async (
  cardId: number,
  data: MoveCardRequest
): Promise<void> => {
  await apiClient.patch(`/cards/${cardId}/move`, data);
};

/**
 * 删除卡片
 * DELETE /api/v1/cards/{cardId}
 */
export const deleteCard = async (cardId: number): Promise<void> => {
  await apiClient.delete(`/cards/${cardId}`);
};
