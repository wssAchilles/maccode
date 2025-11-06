/**
 * aether 项目的 TypeScript 类型定义
 * 严格基于 database.md 和后端 DTO 结构
 */

// ============== 用户相关类型 ==============
export interface UserResponse {
  uid: string;
  email: string;
  username: string;
  avatarUrl: string | null;
  createdAt: string;
  updatedAt: string;
}

// ============== 项目相关类型 ==============
export interface ProjectResponse {
  id: number;
  name: string;
  description: string | null;
  ownerUid: string;
  boards: BoardResponse[];
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

// ============== 项目成员相关类型 ==============
export enum ProjectRole {
  OWNER = 'OWNER',
  ADMIN = 'ADMIN',
  MEMBER = 'MEMBER'
}

export interface ProjectMemberResponse {
  userId: string;
  projectId: number;
  role: ProjectRole;
  joinedAt: string;
}

// ============== 看板相关类型 ==============
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

// ============== 列表相关类型 ==============
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
  position?: number;
}

export interface UpdateListOrderRequest {
  listIds: number[];
}

// ============== 卡片相关类型 ==============
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
  listId: number;
  position?: number;
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

// ============== 完整看板数据结构 ==============
export interface FullBoardResponse {
  id: number;
  name: string;
  projectId: number;
  lists: CardListResponse[];
  createdAt: string;
}

// ============== 活动日志相关类型 ==============
export interface ActivityLogResponse {
  id: number;
  message: string;
  projectId: number;
  userUid: string;
  createdAt: string;
}

// ============== API 错误响应 ==============
export interface ApiError {
  message: string;
  status: number;
  timestamp: string;
}
