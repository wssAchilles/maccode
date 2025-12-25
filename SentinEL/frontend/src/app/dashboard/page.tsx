"use client";

/**
 * SentinEL Command Center - 核心仪表盘页面
 * 
 * 布局: Bento Grid + 实时活动流侧边栏
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
    Database,
    Sparkles
} from "lucide-react";

import { RiskGauge } from "@/components/business/RiskGauge";
import { StrategyCards } from "@/components/business/StrategyCards";
import { EmailPreview } from "@/components/business/EmailPreview";
import { LiveActivityFeed } from "@/components/business/LiveActivityFeed";
import { analyzeUser, runDataPipeline } from "@/services/analysisService";
import { UserAnalysisResponse, DashboardState } from "@/types";

export default function DashboardPage() {
    // ============ 状态管理 ============
    const [userId, setUserId] = useState("63826"); // 默认测试用户
    const [state, setState] = useState<DashboardState>({
        isLoading: false,
        data: null,
        error: null,
    });
    const [isPipelineRunning, setIsPipelineRunning] = useState(false);
    const [pipelineMessage, setPipelineMessage] = useState<string | null>(null);

    // ============ 事件处理 ============
    const handleAnalyze = async () => {
        if (!userId.trim()) return;

        setState({ isLoading: true, data: null, error: null });

        try {
            const result = await analyzeUser(userId);
            setState({ isLoading: false, data: result, error: null });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "未知错误";
            setState({ isLoading: false, data: null, error: errorMessage });
        }
    };

    const handleRunPipeline = async () => {
        setIsPipelineRunning(true);
        setPipelineMessage(null);
        try {
            const result = await runDataPipeline();
            setPipelineMessage("Pipeline Started: " + result.job_id);
            // Auto hide message after 5 seconds
            setTimeout(() => setPipelineMessage(null), 5000);
        } catch (error) {
            console.error(error);
            setPipelineMessage("Pipeline Failed to Start");
        } finally {
            setIsPipelineRunning(false);
        }
    };

    // 回车触发搜索
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") handleAnalyze();
    };

    // ============ 渲染 ============
    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
            {/* Header 区域 */}
            <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-xl sticky top-0 z-50">
                <div className="container mx-auto px-4 py-4">
                    <div className="flex items-center justify-between gap-4">
                        {/* Logo & Title */}
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-gradient-to-br from-violet-600 to-fuchsia-600">
                                <ShieldCheck className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-xl font-bold text-white">SentinEL Command Center</h1>
                                <p className="text-xs text-slate-500">AI-Powered Customer Retention Platform</p>
                            </div>
                        </div>

                        {/* 搜索栏 */}
                        <div className="flex items-center gap-2 flex-1 max-w-md">
                            <div className="relative flex-1">
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <Input
                                    placeholder="输入用户 ID..."
                                    value={userId}
                                    onChange={(e) => setUserId(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    className="pl-9 bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500
                             focus:border-violet-500 focus:ring-violet-500/20"
                                />
                            </div>
                            <Button
                                onClick={handleAnalyze}
                                disabled={state.isLoading || !userId.trim()}
                                className="bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-700 hover:to-fuchsia-700
                           text-white shadow-lg shadow-violet-500/25"
                            >
                                <Search className="w-4 h-4 mr-2" />
                                {state.isLoading ? "分析中..." : "分析"}
                            </Button>
                        </div>

                        {/* 状态指示器 */}
                        <Badge variant="outline" className="border-emerald-500/50 text-emerald-400 hidden sm:flex">
                            <Zap className="w-3 h-3 mr-1" />
                            Gemini 2.5 Pro
                        </Badge>
                    </div>
                </div>
            </header>

            {/* Main Content - 70/30 布局 */}
            <main className="container mx-auto px-4 py-6">
                {/* 错误提示 */}
                {state.error && (
                    <div className="mb-6 p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400">
                        <p className="text-sm">{state.error}</p>
                    </div>
                )}

                {/* 主布局: 左侧分析结果 (70%) + 右侧活动流 (30%) */}
                <div className="grid grid-cols-1 xl:grid-cols-10 gap-6">
                    {/* 左侧区域 - 分析结果 (70%) */}
                    <div className="xl:col-span-7">
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                            {/* 风险评估 & 用户画像 */}
                            <div className="space-y-4">
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
                                    <EmptyState message="输入用户 ID 开始分析" />
                                )}
                            </div>

                            {/* RAG 策略 */}
                            <div>
                                {state.isLoading ? (
                                    <LoadingSkeleton type="cards" />
                                ) : state.data ? (
                                    <StrategyCards strategies={state.data.retention_policies} />
                                ) : (
                                    <EmptyState message="策略将在分析后展示" />
                                )}
                            </div>

                            {/* 邮件预览 */}
                            <div>
                                {state.isLoading ? (
                                    <LoadingSkeleton type="email" />
                                ) : state.data ? (
                                    <EmailPreview
                                        emailContent={state.data.generated_email}
                                        userId={state.data.user_id}
                                        analysisId={state.data.analysis_id}
                                    />
                                ) : (
                                    <EmptyState message="AI 生成邮件将在此显示" />
                                )}
                            </div>
                        </div>
                    </div>

                    {/* 右侧区域 - 实时活动流 (30%) */}
                    <div className="xl:col-span-3">
                        <LiveActivityFeed />

                        {/* MLOps Status Card */}
                        <Card className="mt-6 bg-slate-900/50 border-slate-700/50 backdrop-blur-sm">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                                    <Database className="w-4 h-4 text-emerald-400" />
                                    MLOps Status
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/30">
                                    <div className="flex justify-between items-center mb-1">
                                        <span className="text-xs text-slate-500">Training Samples Ready</span>
                                        <span className="text-xs font-mono text-emerald-400">128</span>
                                    </div>
                                    <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                                        <div className="h-full bg-emerald-500 w-[35%]" />
                                    </div>
                                </div>

                                <Button
                                    onClick={handleRunPipeline}
                                    disabled={isPipelineRunning}
                                    className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
                                >
                                    {isPipelineRunning ? (
                                        <>
                                            <Clock className="w-4 h-4 mr-2 animate-spin" />
                                            Pipeline Running...
                                        </>
                                    ) : (
                                        <>
                                            <Sparkles className="w-4 h-4 mr-2 text-fuchsia-400" />
                                            Trigger Data Refinery
                                        </>
                                    )}
                                </Button>

                                {pipelineMessage && (
                                    <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400 text-center">
                                        {pipelineMessage}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </main>
        </div>
    );
}


// ============ 子组件 ============

/**
 * 用户画像卡片
 */
function UserProfileCard({ data }: { data: UserAnalysisResponse }) {
    const features = data.user_features;

    return (
        <Card className="bg-slate-900/50 border-slate-700/50 backdrop-blur-sm">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                    <User className="w-4 h-4" />
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
                <div className="pt-2 border-t border-slate-800">
                    <p className="text-xs text-slate-500">
                        推荐操作: <span className="text-slate-300">{data.recommended_action}</span>
                    </p>
                </div>
            </CardContent>
        </Card>
    );
}

function ProfileItem({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
    return (
        <div className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/30">
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
                {icon}
                {label}
            </div>
            <p className="text-sm text-slate-200 font-medium truncate">{value}</p>
        </div>
    );
}

/**
 * 骨架屏加载状态
 */
function LoadingSkeleton({ type }: { type: "gauge" | "cards" | "email" }) {
    return (
        <Card className="bg-slate-900/50 border-slate-700/50 backdrop-blur-sm h-full">
            <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24 bg-slate-800" />
            </CardHeader>
            <CardContent className="space-y-4">
                {type === "gauge" && (
                    <>
                        <Skeleton className="h-20 w-20 rounded-full mx-auto bg-slate-800" />
                        <Skeleton className="h-2 w-full bg-slate-800" />
                        <Skeleton className="h-3 w-3/4 mx-auto bg-slate-800" />
                    </>
                )}
                {type === "cards" && (
                    <>
                        <Skeleton className="h-16 w-full bg-slate-800" />
                        <Skeleton className="h-16 w-full bg-slate-800" />
                        <Skeleton className="h-16 w-full bg-slate-800" />
                    </>
                )}
                {type === "email" && (
                    <>
                        <Skeleton className="h-12 w-full bg-slate-800" />
                        <Skeleton className="h-32 w-full bg-slate-800" />
                        <Skeleton className="h-8 w-full bg-slate-800" />
                    </>
                )}
            </CardContent>
        </Card>
    );
}

/**
 * 空状态占位
 */
function EmptyState({ message }: { message: string }) {
    return (
        <Card className="bg-slate-900/50 border-slate-700/50 backdrop-blur-sm h-full min-h-[200px] flex items-center justify-center">
            <p className="text-sm text-slate-500">{message}</p>
        </Card>
    );
}
