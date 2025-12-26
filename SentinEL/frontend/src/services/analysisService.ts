/**
 * SentinEL API 服务层
 * 封装所有与后端的通信逻辑
 */

import { UserAnalysisRequest, UserAnalysisResponse } from "@/types";

// 后端 API 基础地址
// 后端 API 基础地址
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
export const API_KEY = "sentinel_top_secret_2025"; // Hardcoded for demo parity

export const analysisService = {
    /**
     * 健康检查 - 验证后端服务是否可用
     * @returns boolean - 服务是否健康
     */
    checkHealth: async (): Promise<boolean> => {
        try {
            const response = await fetch(`${API_URL}/health`, {
                headers: {
                    "X-API-KEY": API_KEY
                }
            });
            return response.ok;
        } catch (error) {
            console.error('Health check failed:', error);
            return false;
        }
    },

    /**
     * 分析用户流失风险 (带异步轮询)
     * @param userId - 目标用户 ID
     * @returns UserAnalysisResponse - 包含风险评估和 AI 生成内容
     * @throws Error - 网络错误或后端返回错误时抛出
     */
    analyzeUser: async (userId: string, imageData?: string | null): Promise<UserAnalysisResponse> => {
        const endpoint = `${API_URL}/api/v1/analyze`;

        const requestBody: UserAnalysisRequest = {
            user_id: userId,
            image_data: imageData || undefined, // Send if present
        };

        try {
            // 1. 提交分析请求 (获取 analysis_id)
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-KEY": API_KEY
                },
                body: JSON.stringify(requestBody),
            });

            // 处理 HTTP 错误
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorMessage = errorData.detail || `服务器错误: ${response.status}`;
                throw new Error(errorMessage);
            }

            const asyncResponse = await response.json();
            const analysisId = asyncResponse.analysis_id;

            if (!analysisId) {
                throw new Error("未获取到分析 ID");
            }

            // 2. 轮询等待分析完成
            const maxAttempts = 60; // 最多轮询 60 次
            const pollInterval = 1000; // 每秒轮询一次

            for (let attempt = 0; attempt < maxAttempts; attempt++) {
                await new Promise(resolve => setTimeout(resolve, pollInterval));

                const statusResponse = await fetch(`${API_URL}/api/v1/analyze/${analysisId}`, {
                    headers: { "X-API-KEY": API_KEY }
                });

                if (!statusResponse.ok) {
                    continue; // 重试
                }

                const statusData = await statusResponse.json();

                if (statusData.status === "COMPLETED") {
                    // 返回完整的分析结果
                    return {
                        user_id: statusData.user_id || userId,
                        risk_level: statusData.risk_level || "Low",
                        churn_probability: statusData.churn_probability ?? 0,
                        user_features: statusData.user_features || {},
                        retention_policies: statusData.retention_policies || [],
                        generated_email: statusData.generated_email || null,
                        call_script: statusData.call_script || null,
                        generated_audio: statusData.generated_audio || null,
                        recommended_action: statusData.recommended_action || "",
                        analysis_id: analysisId,
                        experiment_group: statusData.experiment_group,
                        model_used: statusData.model_used,
                        processing_time_ms: statusData.processing_time_ms
                    } as UserAnalysisResponse;
                }

                if (statusData.status === "FAILED") {
                    throw new Error(statusData.error_message || "分析失败");
                }

                // QUEUED 或 PROCESSING 状态继续轮询
            }

            throw new Error("分析超时，请稍后重试");

        } catch (error) {
            // 区分网络错误和业务错误
            if (error instanceof TypeError && error.message.includes("fetch")) {
                throw new Error("无法连接到 SentinEL 后端服务，请检查服务是否运行");
            }
            // 重新抛出其他错误
            throw error;
        }
    },

    /**
     * 提交用户对 AI 生成邮件的反馈
     * @param analysisId -分析记录 ID
     * @param userId - 用户 ID
     * @param feedbackType - 反馈类型 ('thumbs_up' | 'thumbs_down')
     * @returns boolean - 提交是否成功
     */
    submitFeedback: async (
        analysisId: string,
        userId: string,
        feedbackType: "thumbs_up" | "thumbs_down"
    ): Promise<boolean> => {
        const endpoint = `${API_URL}/api/v1/feedback`;

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-KEY": API_KEY
                },
                body: JSON.stringify({
                    analysis_id: analysisId,
                    user_id: userId,
                    feedback_type: feedbackType,
                }),
            });

            return response.ok;
        } catch (error) {
            console.error("Failed to submit feedback:", error);
            return false;
        }
    },

    /**
     * 触发数据工厂管道 (MLOps)
     * @returns object - 包含 job_id 和 status
     */
    runDataPipeline: async (): Promise<{ status: string; job_id: string; console_url: string; message: string }> => {
        const endpoint = `${API_URL}/api/v1/train`;

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-KEY": API_KEY
                },
            });

            if (!response.ok) {
                throw new Error("Failed to trigger data pipeline");
            }

            return await response.json();
        } catch (error) {
            console.error("Pipeline trigger failed:", error);
            throw error;
        }
    },

    /**
     * 获取用户推荐策略 (双塔召回)
     * @param userId -  用户 ID
     * @returns List of strategies
     */
    getRecommendations: async (userId: string): Promise<any[]> => {
        // 这是一个新的 API 端点
        const endpoint = `${API_URL}/api/v1/recommendations/${userId}`;
        try {
            const response = await fetch(endpoint, {
                headers: { "X-API-KEY": API_KEY }
            });
            if (!response.ok) return [];
            return await response.json();
        } catch (e) {
            console.error("Failed to get recommendations:", e);
            return [];
        }
    }
};

// Also export standalone functions for backward compatibility if needed, 
// or cleaner imports in other files. 
// But since we are changing the default, let's stick to the object or standalone.
// The previous errors suggested "analyzeUser" was missing from export.
// Let's also export them as destuctured from the object to be safe/mix-friendly.
export const { analyzeUser, submitFeedback, checkHealth, runDataPipeline, getRecommendations } = analysisService;
