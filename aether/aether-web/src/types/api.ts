/**
 * API 类型定义
 * 严格对应后端 DTO 结构
 */

// ==================== 项目相关类型 ====================

export interface ProjectResponse {
  id: number;
  name: string;
  description: string | null;
  ownerUid: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
}

// ==================== 看板相关类型 ====================

export interface BoardResponse {
  id: number;
  name: string;
  projectId: number;
  createdAt: string;
}

export interface CreateBoardRequest {
  name: string;
  projectId: number;
}

// ==================== 列表相关类型 ====================

export interface CardListResponse {
  id: number;
  name: string;
  position: number;
  boardId: number;
  cards: CardResponse[];
}

export interface CreateCardListRequest {
  name: string;
  boardId: number;
}

export interface UpdateCardListOrderRequest {
  listIds: number[];
}

// ==================== 卡片相关类型 ====================

export interface CardResponse {
  id: number;
  title: string;
  description: string | null;
  position: number;
  dueDate: string | null;
  listId: number;
  createdAt: string;
  updatedAt: string;
}

export interface CreateCardRequest {
  title: string;
  description?: string;
  dueDate?: string;
  listId: number;
}

export interface UpdateCardRequest {
  title?: string;
  description?: string;
  dueDate?: string;
}

export interface MoveCardRequest {
  targetListId: number;
  newPosition: number;
}

// ==================== 完整看板类型 ====================

export interface FullBoardResponse {
  id: number;
  name: string;
  projectId: number;
  createdAt: string;
  lists: CardListResponse[];
}

// ==================== 用户相关类型 ====================

export interface UserResponse {
  uid: string;
  email: string;
  username: string;
  avatarUrl: string | null;
  createdAt: string;
  updatedAt: string;
}
