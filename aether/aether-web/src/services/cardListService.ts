/**
 * 卡片列表相关 API 服务
 * 严格对应后端 CardListController 的端点
 */

import apiClient from '@/lib/apiClient';
import type { CardListResponse, CreateCardListRequest } from '@/types/api';

/**
 * 创建新列表
 * POST /api/v1/boards/{boardId}/lists
 */
export const createCardList = async (
  boardId: number,
  data: CreateCardListRequest
): Promise<CardListResponse> => {
  const response = await apiClient.post<CardListResponse>(
    `/boards/${boardId}/lists`,
    data
  );
  return response.data;
};

/**
 * 删除列表
 * DELETE /api/v1/lists/{listId}
 */
export const deleteCardList = async (listId: number): Promise<void> => {
  await apiClient.delete(`/lists/${listId}`);
};
