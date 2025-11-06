/**
 * 看板相关 API 服务
 * 严格对应后端 BoardController 的端点
 */

import apiClient from '@/lib/apiClient';
import type {
  BoardResponse,
  CreateBoardRequest,
  FullBoardResponse,
  UpdateCardListOrderRequest,
} from '@/types/api';

/**
 * 获取项目下的所有看板
 * GET /api/v1/projects/{projectId}/boards
 */
export const getBoardsByProject = async (
  projectId: number
): Promise<BoardResponse[]> => {
  const response = await apiClient.get<BoardResponse[]>(
    `/projects/${projectId}/boards`
  );
  return response.data;
};

/**
 * 获取看板完整详情（包含所有列表和卡片）
 * GET /api/v1/boards/{boardId}
 */
export const getFullBoard = async (
  boardId: number
): Promise<FullBoardResponse> => {
  const response = await apiClient.get<FullBoardResponse>(`/boards/${boardId}`);
  return response.data;
};

/**
 * 创建新看板
 * POST /api/v1/boards?projectId={projectId}
 */
export const createBoard = async (
  data: CreateBoardRequest
): Promise<BoardResponse> => {
  const response = await apiClient.post<BoardResponse>(
    `/boards?projectId=${data.projectId}`,
    { name: data.name }
  );
  return response.data;
};

/**
 * 更新列表顺序（拖拽列表）
 * PATCH /api/v1/boards/{boardId}/lists/order
 */
export const updateListOrder = async (
  boardId: number,
  listIds: number[]
): Promise<void> => {
  await apiClient.patch(`/boards/${boardId}/lists/order`, { listIds });
};

/**
 * 删除看板
 * DELETE /api/v1/boards/{boardId}
 */
export const deleteBoard = async (boardId: number): Promise<void> => {
  await apiClient.delete(`/boards/${boardId}`);
};
