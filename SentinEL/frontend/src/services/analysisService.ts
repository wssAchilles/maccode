/**
 * SentinEL API 服务层
 * 封装所有与后端的通信逻辑
 */

import { UserAnalysisRequest, UserAnalysisResponse } from "@/types";

// 后端 API 基础地址
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8080";

/**
 * 分析用户流失风险
 * @param userId - 目标用户 ID
 * @returns UserAnalysisResponse - 包含风险评估和 AI 生成内容
 * @throws Error - 网络错误或后端返回错误时抛出
 */
export async function analyzeUser(userId: string): Promise<UserAnalysisResponse> {
    const endpoint = `${API_BASE_URL}/api/v1/analyze`;

    const requestBody: UserAnalysisRequest = {
        user_id: userId,
    };

    try {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(requestBody),
        });

        // 处理 HTTP 错误
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || `服务器错误: ${response.status}`;
            throw new Error(errorMessage);
        }

        // 解析并返回响应
        const data: UserAnalysisResponse = await response.json();
        return data;

    } catch (error) {
        // 区分网络错误和业务错误
        if (error instanceof TypeError && error.message.includes("fetch")) {
            throw new Error("无法连接到 SentinEL 后端服务，请检查服务是否运行");
        }
        // 重新抛出其他错误
        throw error;
    }
}

/**
 * 健康检查 - 验证后端服务是否可用
 * @returns boolean - 服务是否健康
 */
export async function checkHealth(): Promise<boolean> {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        return response.ok;
    } catch {
        return false;
    }
}
