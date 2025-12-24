/**
 * SentinEL 前端类型定义
 * 与后端 Pydantic Schema 保持严格一致
 */

// ============ API 请求类型 ============

/**
 * 用户分析请求体
 */
export interface UserAnalysisRequest {
    user_id: string;
}

// ============ API 响应类型 ============

/**
 * 用户特征画像
 * 从 BigQuery 流失预测模型返回
 */
export interface UserFeatures {
    country?: string;
    traffic_source?: string;
    monetary_90d?: number;
    recency_days?: number;
    frequency_90d?: number;
    [key: string]: unknown; // 允许扩展属性
}

/**
 * 用户分析响应体
 * 包含风险评估、RAG 策略和生成的邮件
 */
export interface UserAnalysisResponse {
    user_id: string;
    risk_level: "High" | "Low"; // 风险等级
    churn_probability: number;  // 流失概率 (0-1)
    recommended_action: string; // 推荐操作
    generated_email: string | null; // AI 生成的挽留邮件
    retention_policies: string[] | null; // RAG 检索到的策略
    user_features: UserFeatures | null; // 用户特征画像
    analysis_id: string; // 后端生成的分析记录 ID (用于反馈)
}

/**
 * 用户反馈请求类型
 */
export type FeedbackType = "thumbs_up" | "thumbs_down";

export interface FeedbackRequest {
    analysis_id: string;
    user_id: string;
    feedback_type: FeedbackType;
}

// ============ UI 状态类型 ============

/**
 * Dashboard 页面的加载状态
 */
export interface DashboardState {
    isLoading: boolean;
    data: UserAnalysisResponse | null;
    error: string | null;
}
