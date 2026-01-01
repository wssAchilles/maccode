"use client";

/**
 * StrategyCards 组件
 * 展示 RAG 检索到的挽留策略列表
 * Glassmorphism 风格 + 交互动效
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sparkles, BrainCircuit, FileText, Lightbulb } from "lucide-react";

interface Recommendation {
    id: string;
    type: string;
    description: string;
    score: number;
}

interface StrategyCardsProps {
    strategies: Recommendation[] | string[] | null;
}

export function StrategyCards({ strategies }: StrategyCardsProps) {
    // 空状态处理
    if (!strategies || strategies.length === 0) {
        return (
            <Card className="glass-card-strong h-full">
                <CardHeader>
                    <CardTitle className="text-sm font-heading font-medium text-slate-300 flex items-center gap-2">
                        <BrainCircuit className="w-4 h-4 text-violet-400" />
                        RAG 策略检索
                    </CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col items-center justify-center py-12 text-slate-500">
                    <FileText className="w-12 h-12 mb-3 opacity-30" />
                    <p className="text-sm">暂无策略建议</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="glass-card-strong h-full overflow-hidden">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-heading font-medium text-slate-300 flex items-center gap-2">
                        <BrainCircuit className="w-4 h-4 text-violet-400" />
                        RAG 策略检索
                    </CardTitle>
                    <Badge
                        variant="outline"
                        className="border-violet-500/30 text-violet-400 bg-violet-500/10 flex items-center gap-1"
                    >
                        <Sparkles className="w-3 h-3" />
                        AI Retrieval
                    </Badge>
                </div>
            </CardHeader>

            <CardContent className="p-0">
                <ScrollArea className="h-[320px] px-4 pb-4">
                    <div className="space-y-3">
                        {strategies.map((strategy, index) => {
                            const isObj = typeof strategy === 'object' && strategy !== null;
                            const text = isObj ? (strategy as Recommendation).description : (strategy as string);
                            const type = isObj ? (strategy as Recommendation).type : null;
                            const score = isObj ? (strategy as Recommendation).score : null;

                            return (
                                <div
                                    key={index}
                                    className="group p-4 rounded-xl bg-slate-800/40 border border-slate-700/40 
                                               hover:border-violet-500/40 hover:bg-slate-800/60
                                               transition-all duration-200 cursor-pointer glow-border"
                                >
                                    <div className="flex items-start gap-3">
                                        {/* 序号标记 - 渐变背景 */}
                                        <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-gradient-to-br from-violet-600 to-fuchsia-600 
                                                        text-white text-xs font-bold flex items-center justify-center 
                                                        shadow-glow-sm group-hover:shadow-glow-md transition-shadow">
                                            {index + 1}
                                        </div>

                                        {/* 策略内容 */}
                                        <div className="flex-1 min-w-0 space-y-2">
                                            <p className="text-sm text-slate-200 leading-relaxed">
                                                {text}
                                            </p>

                                            {/* 标签行 */}
                                            <div className="flex items-center gap-2 flex-wrap">
                                                {type && (
                                                    <Badge
                                                        variant="secondary"
                                                        className="text-[10px] px-2 h-5 bg-slate-700/50 text-slate-400 
                                                                   border border-slate-600/30 hover:bg-slate-700"
                                                    >
                                                        {type}
                                                    </Badge>
                                                )}
                                                {score && score > 0.8 && (
                                                    <Badge
                                                        variant="outline"
                                                        className="text-[10px] px-2 h-5 border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                                                    >
                                                        高相关度
                                                    </Badge>
                                                )}
                                            </div>
                                        </div>

                                        {/* Hover 指示器 */}
                                        <Lightbulb className="w-4 h-4 text-slate-600 group-hover:text-amber-400 transition-colors flex-shrink-0" />
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* 底部说明 */}
                    <div className="mt-4 pt-3 border-t border-slate-700/50">
                        <p className="text-xs text-slate-500 text-center flex items-center justify-center gap-1">
                            <Sparkles className="w-3 h-3 text-violet-400" />
                            以上策略由 Vector Search 从知识库中检索
                        </p>
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}
