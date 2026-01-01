"use client";

/**
 * SentinEL Command Center - 核心仪表盘页面
 * 
 * 布局: Bento Grid + 实时活动流侧边栏 + Glassmorphism 设计
 * - 左侧 (70%): 分析结果 (Risk Gauge, Strategy Cards, Email Preview)
 * - 右侧 (30%): 实时活动流 (LiveActivityFeed)
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
    Search,
    ShieldCheck,
    User,
    Globe,
    TrendingUp,
    Clock,
    Zap,
    Bot,
    Sparkles
} from "lucide-react";

import { RiskGauge } from "@/components/business/RiskGauge";
import { StrategyCards } from "@/components/business/StrategyCards";
import { EmailPreview } from "@/components/business/EmailPreview";
import { CompetitorUpload } from "@/components/business/CompetitorUpload";
import { LiveActivityFeed } from "@/components/business/LiveActivityFeed";
import { MlopsPanel } from "@/components/business/MlopsPanel";
import { ExperimentDashboard } from "@/components/business/ExperimentDashboard";
import AgentReasoningLog, { TraceStep } from "@/components/business/AgentReasoningLog";
import { analyzeUser, analyzeFlow } from "@/services/analysisService";
import { UserAnalysisResponse, DashboardState } from "@/types";

export default function DashboardPage() {
    // ============ 状态管理 ============
    const [userId, setUserId] = useState("63826");
    const [imageData, setImageData] = useState<string | null>(null);
    const [agentLogs, setAgentLogs] = useState<TraceStep[]>([]);
    const [state, setState] = useState<DashboardState>({
        isLoading: false,
        data: null,
        error: null,
    });

    // ============ 事件处理 ============
    const handleAnalyze = async () => {
        if (!userId.trim()) return;

        setState({ isLoading: true, data: null, error: null });
        setAgentLogs([]);

        try {
            const flowResult = await analyzeFlow(userId);
            setAgentLogs(flowResult.trace_log);

            const result = await analyzeUser(userId, imageData);
            setState({ isLoading: false, data: result, error: null });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "未知错误";
            setState({ isLoading: false, data: null, error: errorMessage });
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") handleAnalyze();
    };

    // ============ 渲染 ============
    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 relative overflow-hidden">
            {/* 背景装饰 - 渐变光晕 */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl" />
                <div className="absolute top-1/2 -left-40 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl" />
                <div className="absolute -bottom-40 right-1/3 w-72 h-72 bg-orange-500/10 rounded-full blur-3xl" />
            </div>

            {/* 浮动导航栏 - Glassmorphism */}
            <header className="sticky top-4 mx-4 z-50 rounded-2xl glass-nav">
                <div className="container mx-auto px-6 py-4">
                    <div className="flex items-center justify-between gap-4">
                        {/* Logo & Title */}
                        <div className="flex items-center gap-3">
                            <div className="p-2.5 rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-600 shadow-glow-md">
                                <ShieldCheck className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-xl font-heading font-bold text-white tracking-tight">
                                    SentinEL
                                </h1>
                                <p className="text-xs text-slate-400">AI-Powered Retention Platform</p>
                            </div>
                        </div>

                        {/* 搜索栏 - 增强样式 */}
                        <div className="flex items-center gap-3 flex-1 max-w-md">
                            <div className="relative flex-1 group">
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
                                <Input
                                    placeholder="输入用户 ID..."
                                    value={userId}
                                    onChange={(e) => setUserId(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    className="pl-10 bg-slate-900/50 border-slate-700/50 text-white placeholder:text-slate-500
                                               focus:border-blue-500/50 focus:ring-blue-500/20 focus:bg-slate-900/70
                                               rounded-xl transition-all duration-200"
                                />
                            </div>
                            <Button
                                onClick={handleAnalyze}
                                disabled={state.isLoading || !userId.trim()}
                                className="bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-700 hover:to-violet-700
                                           text-white shadow-glow-sm hover:shadow-glow-md
                                           rounded-xl px-6 transition-all duration-200 font-medium"
                            >
                                {state.isLoading ? (
                                    <>
                                        <Sparkles className="w-4 h-4 mr-2 animate-pulse" />
                                        分析中...
                                    </>
                                ) : (
                                    <>
                                        <Search className="w-4 h-4 mr-2" />
                                        分析
                                    </>
                                )}
                            </Button>
                        </div>

                        {/* 状态指示器 */}
                        <Badge
                            variant="outline"
                            className="border-emerald-500/30 text-emerald-400 bg-emerald-500/10 
                                       hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg"
                        >
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                            </span>
                            Gemini 2.5 Pro
                        </Badge>
                    </div>
                </div>
            </header>

            {/* 主内容区 - 带顶部留白 */}
            <main className="container mx-auto px-4 py-8 relative z-10">
                {/* 错误提示 */}
                {state.error && (
                    <div className="mb-6 p-4 rounded-xl glass-card border-rose-500/30 bg-rose-500/10 text-rose-400 animate-fade-in">
                        <p className="text-sm">{state.error}</p>
                    </div>
                )}

                {/* 主布局: 左侧分析结果 (70%) + 右侧活动流 (30%) */}
                <div className="grid grid-cols-1 xl:grid-cols-10 gap-6">
                    {/* 左侧区域 - 分析结果 */}
                    <div className="xl:col-span-7 space-y-6">
                        {/* 上半部分: 双列布局 */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* 风险评估 & 用户画像 */}
                            <div className="space-y-6">
                                {state.isLoading ? (
                                    <LoadingSkeleton type="gauge" />
                                ) : state.data ? (
                                    <>
                                        <RiskGauge
                                            churnProbability={state.data.churn_probability}
                                            riskLevel={state.data.risk_level as "High" | "Low"}
                                        />
                                        <UserProfileCard data={state.data} />
                                    </>
                                ) : (
                                    <EmptyState message="输入用户 ID 开始分析" icon={<User className="w-8 h-8" />} />
                                )}
                            </div>

                            {/* Competitor Upload + Strategy Cards */}
                            <div className="space-y-6">
                                <CompetitorUpload onImageSelect={setImageData} />
                                {state.isLoading ? (
                                    <LoadingSkeleton type="cards" />
                                ) : state.data ? (
                                    <StrategyCards
                                        strategies={
                                            (state.data.recommended_strategies && state.data.recommended_strategies.length > 0)
                                                ? state.data.recommended_strategies
                                                : state.data.retention_policies
                                        }
                                    />
                                ) : (
                                    <EmptyState message="策略将在分析后展示" icon={<Zap className="w-8 h-8" />} />
                                )}
                            </div>
                        </div>

                        {/* 邮件预览 - 全宽 */}
                        <div className="animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
                            {state.isLoading ? (
                                <LoadingSkeleton type="email" />
                            ) : state.data ? (
                                <EmailPreview
                                    emailContent={state.data.generated_email}
                                    userId={state.data.user_id}
                                    analysisId={state.data.analysis_id}
                                    callScript={state.data.call_script}
                                    audioBase64={state.data.generated_audio}
                                />
                            ) : (
                                <EmptyState message="AI 生成邮件将在此显示" icon={<Sparkles className="w-8 h-8" />} />
                            )}
                        </div>

                        {/* Agent Reasoning Log */}
                        <div className="animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
                            <div className="flex items-center gap-2 mb-3">
                                <Bot className="w-5 h-5 text-emerald-400" />
                                <h3 className="text-sm font-heading font-medium text-slate-300">
                                    AI Decision Process
                                </h3>
                            </div>
                            <AgentReasoningLog logs={agentLogs} isLoading={state.isLoading} />
                        </div>
                    </div>

                    {/* 右侧区域 - 实时活动流 */}
                    <div className="xl:col-span-3">
                        <div className="sticky top-24">
                            <LiveActivityFeed />
                        </div>
                    </div>
                </div>

                {/* Enterprise MLOps Panel */}
                <div className="mt-8 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
                    <MlopsPanel />
                </div>

                {/* A/B 测试实验看板 */}
                <div className="mt-8 animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
                    <ExperimentDashboard />
                </div>
            </main>
        </div>
    );
}

// ============ 子组件 ============

/**
 * 用户画像卡片 - Glassmorphism 风格
 */
function UserProfileCard({ data }: { data: UserAnalysisResponse }) {
    const features = data.user_features;

    return (
        <Card className="glass-card-strong hover-lift cursor-pointer">
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-heading font-medium text-slate-300 flex items-center gap-2">
                    <User className="w-4 h-4 text-blue-400" />
                    用户画像
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                    <ProfileItem
                        icon={<Globe className="w-4 h-4 text-blue-400" />}
                        label="地区"
                        value={features?.country || "Unknown"}
                    />
                    <ProfileItem
                        icon={<TrendingUp className="w-4 h-4 text-emerald-400" />}
                        label="来源"
                        value={features?.traffic_source || "Unknown"}
                    />
                    <ProfileItem
                        icon={<Zap className="w-4 h-4 text-amber-400" />}
                        label="90天消费"
                        value={`¥${features?.monetary_90d?.toFixed(2) || 0}`}
                    />
                    <ProfileItem
                        icon={<Clock className="w-4 h-4 text-violet-400" />}
                        label="最近活跃"
                        value={`${features?.recency_days || 0} 天前`}
                    />
                </div>
                <div className="pt-3 border-t border-slate-700/50">
                    <p className="text-xs text-slate-500">
                        推荐操作: <span className="text-slate-300 font-medium">{data.recommended_action}</span>
                    </p>
                </div>
            </CardContent>
        </Card>
    );
}

function ProfileItem({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
    return (
        <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/30 hover:border-slate-600/50 transition-colors cursor-default">
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-1.5">
                {icon}
                {label}
            </div>
            <p className="text-sm text-slate-200 font-medium truncate">{value}</p>
        </div>
    );
}

/**
 * 骨架屏加载状态 - Glassmorphism 风格
 */
function LoadingSkeleton({ type }: { type: "gauge" | "cards" | "email" }) {
    return (
        <Card className="glass-card-strong animate-pulse">
            <CardHeader className="pb-3">
                <Skeleton className="h-4 w-24 bg-slate-700/50" />
            </CardHeader>
            <CardContent className="space-y-4">
                {type === "gauge" && (
                    <>
                        <Skeleton className="h-24 w-24 rounded-full mx-auto bg-slate-700/50" />
                        <Skeleton className="h-2 w-full bg-slate-700/50" />
                        <Skeleton className="h-3 w-3/4 mx-auto bg-slate-700/50" />
                    </>
                )}
                {type === "cards" && (
                    <>
                        <Skeleton className="h-20 w-full rounded-xl bg-slate-700/50" />
                        <Skeleton className="h-20 w-full rounded-xl bg-slate-700/50" />
                        <Skeleton className="h-20 w-full rounded-xl bg-slate-700/50" />
                    </>
                )}
                {type === "email" && (
                    <>
                        <Skeleton className="h-12 w-full rounded-xl bg-slate-700/50" />
                        <Skeleton className="h-32 w-full rounded-xl bg-slate-700/50" />
                        <Skeleton className="h-10 w-full rounded-xl bg-slate-700/50" />
                    </>
                )}
            </CardContent>
        </Card>
    );
}

/**
 * 空状态占位 - Glassmorphism 风格
 */
function EmptyState({ message, icon }: { message: string; icon?: React.ReactNode }) {
    return (
        <Card className="glass-card h-full min-h-[200px] flex flex-col items-center justify-center cursor-default">
            {icon && (
                <div className="text-slate-600 mb-3">
                    {icon}
                </div>
            )}
            <p className="text-sm text-slate-500">{message}</p>
        </Card>
    );
}
