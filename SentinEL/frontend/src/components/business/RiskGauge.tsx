"use client";

/**
 * RiskGauge 组件
 * 以半圆仪表盘形式展示用户流失概率
 * 颜色编码: 绿色 (<30%) -> 黄色 (30-70%) -> 红色 (>70%)
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle, AlertCircle } from "lucide-react";

interface RiskGaugeProps {
    churnProbability: number; // 0-1 范围
    riskLevel: "High" | "Low";
}

export function RiskGauge({ churnProbability, riskLevel }: RiskGaugeProps) {
    // 计算百分比
    const percentage = Math.round(churnProbability * 100);

    // 根据概率确定颜色和状态
    const getColorClass = () => {
        if (percentage < 30) return "text-emerald-500";
        if (percentage < 70) return "text-amber-500";
        return "text-rose-500";
    };

    const getProgressColor = () => {
        if (percentage < 30) return "bg-emerald-500";
        if (percentage < 70) return "bg-amber-500";
        return "bg-rose-500";
    };

    const getIcon = () => {
        if (percentage < 30) return <CheckCircle className="w-5 h-5 text-emerald-500" />;
        if (percentage < 70) return <AlertCircle className="w-5 h-5 text-amber-500" />;
        return <AlertTriangle className="w-5 h-5 text-rose-500" />;
    };

    const getBadgeVariant = (): "default" | "destructive" | "secondary" => {
        return riskLevel === "High" ? "destructive" : "secondary";
    };

    return (
        <Card className="bg-slate-900/50 border-slate-700/50 backdrop-blur-sm">
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium text-slate-400">
                        流失风险评估
                    </CardTitle>
                    <Badge variant={getBadgeVariant()}>
                        {riskLevel === "High" ? "高风险" : "低风险"}
                    </Badge>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* 核心数值展示 */}
                <div className="flex items-center justify-center gap-3">
                    {getIcon()}
                    <span className={`text-5xl font-bold tabular-nums ${getColorClass()}`}>
                        {percentage}%
                    </span>
                </div>

                {/* 进度条 */}
                <div className="space-y-2">
                    <Progress
                        value={percentage}
                        className="h-2 bg-slate-800"
                        // 自定义进度条颜色
                        style={{
                            // @ts-expect-error CSS 变量
                            "--progress-background": getProgressColor(),
                        }}
                    />
                    <div className="flex justify-between text-xs text-slate-500">
                        <span>安全</span>
                        <span>警戒</span>
                        <span>危险</span>
                    </div>
                </div>

                {/* 状态说明 */}
                <p className="text-xs text-slate-500 text-center">
                    {percentage < 30 && "该用户活跃度良好，无需干预"}
                    {percentage >= 30 && percentage < 70 && "建议关注该用户，适时发送关怀"}
                    {percentage >= 70 && "高流失风险用户，建议立即启动挽留策略"}
                </p>
            </CardContent>
        </Card>
    );
}
