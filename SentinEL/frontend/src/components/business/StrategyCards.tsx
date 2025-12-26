"use client";

/**
 * StrategyCards 组件
 * 展示 RAG 检索到的挽留策略列表
 * 每张卡片带有 "AI Retrieval" 标签，体现智能检索来源
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, BrainCircuit, FileText } from "lucide-react";

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
            <Card className="bg-slate-900/50 border-slate-700/50 backdrop-blur-sm h-full">
                <CardHeader>
                    <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                        <BrainCircuit className="w-4 h-4" />
                        RAG 策略检索
                    </CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col items-center justify-center py-8 text-slate-500">
                    <FileText className="w-12 h-12 mb-3 opacity-50" />
                    <p className="text-sm">暂无策略建议</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="bg-slate-900/50 border-slate-700/50 backdrop-blur-sm h-full">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                        <BrainCircuit className="w-4 h-4" />
                        RAG 策略检索
                    </CardTitle>
                    <Badge variant="outline" className="border-violet-500/50 text-violet-400">
                        <Sparkles className="w-3 h-3 mr-1" />
                        AI Retrieval
                    </Badge>
                </div>
            </CardHeader>
            <CardContent className="space-y-3 max-h-[400px] overflow-y-auto">
                {strategies.map((strategy, index) => {
                    const isObj = typeof strategy === 'object' && strategy !== null;
                    const text = isObj ? (strategy as Recommendation).description : (strategy as string);
                    const type = isObj ? (strategy as Recommendation).type : null;

                    return (
                        <div
                            key={index}
                            className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 
                       hover:border-violet-500/30 transition-colors duration-200"
                        >
                            <div className="flex flex-col gap-2">
                                <div className="flex items-start gap-3">
                                    {/* 序号标记 */}
                                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-violet-500/20 
                                 text-violet-400 text-xs font-medium flex items-center justify-center mt-0.5">
                                        {index + 1}
                                    </span>
                                    {/* 策略内容 */}
                                    <div className="flex flex-col gap-1 w-full">
                                        <p className="text-sm text-slate-300 leading-relaxed">
                                            {text}
                                        </p>
                                        {type && (
                                            <div className="flex gap-2">
                                                <Badge variant="secondary" className="text-[10px] px-1.5 h-5 bg-slate-700/50 text-slate-400 hover:bg-slate-700">
                                                    {type}
                                                </Badge>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )
                })}

                {/* 底部说明 */}
                <p className="text-xs text-slate-500 text-center pt-2 border-t border-slate-800">
                    以上策略由 Vector Search 从知识库中检索
                </p>
            </CardContent>
        </Card>
    );
}
