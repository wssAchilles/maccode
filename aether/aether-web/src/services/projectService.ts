/**
 * 项目相关 API 服务
 * 严格对应后端 ProjectController 的端点
 */

import apiClient from '@/lib/apiClient';
import type {
  ProjectResponse,
  CreateProjectRequest,
  UpdateProjectRequest,
} from '@/types/api';

/**
 * 获取当前用户的所有项目
 * GET /api/v1/projects
 */
export const getProjects = async (): Promise<ProjectResponse[]> => {
  const response = await apiClient.get<ProjectResponse[]>('/projects');
  return response.data;
};

/**
 * 根据 ID 获取项目详情
 * GET /api/v1/projects/{id}
 */
export const getProjectById = async (id: number): Promise<ProjectResponse> => {
  const response = await apiClient.get<ProjectResponse>(`/projects/${id}`);
  return response.data;
};

/**
 * 创建新项目
 * POST /api/v1/projects
 */
export const createProject = async (
  data: CreateProjectRequest
): Promise<ProjectResponse> => {
  const response = await apiClient.post<ProjectResponse>('/projects', data);
  return response.data;
};

/**
 * 更新项目
 * PUT /api/v1/projects/{id}
 */
export const updateProject = async (
  id: number,
  data: UpdateProjectRequest
): Promise<ProjectResponse> => {
  const response = await apiClient.put<ProjectResponse>(
    `/projects/${id}`,
    data
  );
  return response.data;
};

/**
 * 删除项目
 * DELETE /api/v1/projects/{id}
 */
export const deleteProject = async (id: number): Promise<void> => {
  await apiClient.delete(`/projects/${id}`);
};
