"use client";

/**
 * RiskGauge 组件
 * 以半圆仪表盘形式展示用户流失概率
 * Glassmorphism 风格 + 脉冲发光效果
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle, AlertCircle, TrendingDown } from "lucide-react";

interface RiskGaugeProps {
    churnProbability: number; // 0-1 范围
    riskLevel: "High" | "Low";
}

export function RiskGauge({ churnProbability, riskLevel }: RiskGaugeProps) {
    const percentage = Math.round(churnProbability * 100);

    // 根据概率确定颜色配置
    const getColorConfig = () => {
        if (percentage < 30) return {
            text: "text-emerald-400",
            bg: "bg-emerald-500",
            glow: "shadow-[0_0_30px_rgba(16,185,129,0.4)]",
            gradient: "from-emerald-500 to-cyan-400",
            badgeBg: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
        };
        if (percentage < 70) return {
            text: "text-amber-400",
            bg: "bg-amber-500",
            glow: "shadow-[0_0_30px_rgba(245,158,11,0.4)]",
            gradient: "from-amber-500 to-orange-400",
            badgeBg: "bg-amber-500/10 border-amber-500/30 text-amber-400",
        };
        return {
            text: "text-rose-400",
            bg: "bg-rose-500",
            glow: "shadow-[0_0_30px_rgba(244,63,94,0.4)]",
            gradient: "from-rose-500 to-orange-500",
            badgeBg: "bg-rose-500/10 border-rose-500/30 text-rose-400",
        };
    };

    const colors = getColorConfig();

    const getIcon = () => {
        if (percentage < 30) return <CheckCircle className="w-6 h-6 text-emerald-400" />;
        if (percentage < 70) return <AlertCircle className="w-6 h-6 text-amber-400" />;
        return <AlertTriangle className="w-6 h-6 text-rose-400" />;
    };

    return (
        <Card className="glass-card-strong hover-lift cursor-default overflow-hidden relative">
            {/* 背景渐变光晕 */}
            <div className={`absolute -top-20 -right-20 w-40 h-40 rounded-full blur-3xl opacity-20 bg-gradient-to-br ${colors.gradient}`} />

            <CardHeader className="pb-3 relative">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-heading font-medium text-slate-300 flex items-center gap-2">
                        <TrendingDown className="w-4 h-4 text-blue-400" />
                        流失风险评估
                    </CardTitle>
                    <Badge
                        variant="outline"
                        className={`${colors.badgeBg} font-medium`}
                    >
                        {riskLevel === "High" ? "高风险" : "低风险"}
                    </Badge>
                </div>
            </CardHeader>

            <CardContent className="space-y-5 relative">
                {/* 核心数值展示 - 带发光效果 */}
                <div className="flex flex-col items-center justify-center py-4">
                    <div className={`relative flex items-center justify-center w-28 h-28 rounded-full bg-slate-800/50 border border-slate-700/50 ${colors.glow} transition-shadow duration-500`}>
                        {/* 外圈进度环 */}
                        <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 100 100">
                            {/* 背景环 */}
                            <circle
                                cx="50"
                                cy="50"
                                r="42"
                                stroke="currentColor"
                                strokeWidth="6"
                                fill="none"
                                className="text-slate-700/50"
                            />
                            {/* 进度环 */}
                            <circle
                                cx="50"
                                cy="50"
                                r="42"
                                stroke="url(#riskGradient)"
                                strokeWidth="6"
                                fill="none"
                                strokeLinecap="round"
                                strokeDasharray={`${percentage * 2.64} 264`}
                                className="transition-all duration-700 ease-out"
                            />
                            <defs>
                                <linearGradient id="riskGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                    {percentage < 30 && (
                                        <>
                                            <stop offset="0%" stopColor="#10b981" />
                                            <stop offset="100%" stopColor="#22d3ee" />
                                        </>
                                    )}
                                    {percentage >= 30 && percentage < 70 && (
                                        <>
                                            <stop offset="0%" stopColor="#f59e0b" />
                                            <stop offset="100%" stopColor="#fb923c" />
                                        </>
                                    )}
                                    {percentage >= 70 && (
                                        <>
                                            <stop offset="0%" stopColor="#f43f5e" />
                                            <stop offset="100%" stopColor="#f97316" />
                                        </>
                                    )}
                                </linearGradient>
                            </defs>
                        </svg>

                        {/* 中心数值 */}
                        <div className="flex flex-col items-center z-10">
                            <span className={`text-4xl font-heading font-bold tabular-nums ${colors.text}`}>
                                {percentage}
                            </span>
                            <span className="text-xs text-slate-500 font-medium">%</span>
                        </div>
                    </div>

                    {/* 图标 */}
                    <div className="mt-3">
                        {getIcon()}
                    </div>
                </div>

                {/* 线性进度条 */}
                <div className="space-y-2">
                    <div className="relative h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className={`absolute inset-y-0 left-0 bg-gradient-to-r ${colors.gradient} rounded-full transition-all duration-700 ease-out`}
                            style={{ width: `${percentage}%` }}
                        />
                    </div>
                    <div className="flex justify-between text-xs text-slate-500">
                        <span>安全</span>
                        <span>警戒</span>
                        <span>危险</span>
                    </div>
                </div>

                {/* 状态说明 */}
                <p className="text-xs text-slate-400 text-center leading-relaxed">
                    {percentage < 30 && "该用户活跃度良好，无需干预"}
                    {percentage >= 30 && percentage < 70 && "建议关注该用户，适时发送关怀"}
                    {percentage >= 70 && "高流失风险用户，建议立即启动挽留策略"}
                </p>
            </CardContent>
        </Card>
    );
}
