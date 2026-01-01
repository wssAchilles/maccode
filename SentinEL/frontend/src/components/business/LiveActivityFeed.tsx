"use client";

/**
 * LiveActivityFeed 组件
 * 
 * 实时监听 Firestore 中的 analysis_logs 集合
 * Glassmorphism 风格 + 实时脉冲动画
 */

import { useEffect, useState } from "react";
import { collection, query, orderBy, limit, onSnapshot } from "firebase/firestore";
import { db } from "@/lib/firebase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Activity, User, AlertTriangle, CheckCircle, Loader2, Clock, Radio } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

// 分析日志记录类型
interface AnalysisLog {
    doc_id: string;
    user_id: string;
    churn_probability?: number;
    risk_level?: "High" | "Low";
    status?: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
    email_subject?: string;
    processing_time_ms?: number;
    timestamp?: { seconds: number; nanoseconds: number };
}

export function LiveActivityFeed() {
    const [logs, setLogs] = useState<AnalysisLog[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const logsQuery = query(
            collection(db, "analysis_logs"),
            orderBy("timestamp", "desc"),
            limit(10)
        );

        const unsubscribe = onSnapshot(
            logsQuery,
            (snapshot) => {
                const newLogs: AnalysisLog[] = [];
                snapshot.forEach((doc) => {
                    newLogs.push({
                        doc_id: doc.id,
                        ...doc.data(),
                    } as AnalysisLog);
                });
                setLogs(newLogs);
                setIsLoading(false);
                setError(null);
            },
            (err) => {
                console.error("[LiveActivityFeed] Firestore error:", err);
                setError("无法连接到活动流");
                setIsLoading(false);
            }
        );

        return () => unsubscribe();
    }, []);

    const formatTime = (timestamp?: { seconds: number }) => {
        if (!timestamp) return "刚刚";
        const date = new Date(timestamp.seconds * 1000);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return "刚刚";
        if (diffMins < 60) return `${diffMins} 分钟前`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)} 小时前`;
        return date.toLocaleDateString("zh-CN");
    };

    return (
        <Card className="glass-card-strong h-full flex flex-col overflow-hidden">
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-heading font-medium text-slate-300 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-violet-400" />
                    实时活动流
                    {!isLoading && logs.length > 0 && (
                        <Badge
                            variant="outline"
                            className="ml-auto border-emerald-500/30 text-emerald-400 bg-emerald-500/10 flex items-center gap-1.5"
                        >
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                            </span>
                            Live
                        </Badge>
                    )}
                </CardTitle>
            </CardHeader>

            <CardContent className="flex-1 p-0 overflow-hidden">
                <ScrollArea className="h-[400px] px-4 scrollbar-thin">
                    {/* 加载状态 */}
                    {isLoading && (
                        <div className="flex flex-col items-center justify-center py-16">
                            <Loader2 className="w-8 h-8 animate-spin text-violet-500 mb-3" />
                            <p className="text-sm text-slate-500">连接活动流...</p>
                        </div>
                    )}

                    {/* 错误状态 */}
                    {error && (
                        <div className="text-center py-12">
                            <Radio className="w-10 h-10 text-rose-400 mx-auto mb-3 opacity-50" />
                            <p className="text-sm text-rose-400">{error}</p>
                        </div>
                    )}

                    {/* 空状态 */}
                    {!isLoading && !error && logs.length === 0 && (
                        <div className="text-center py-16 text-slate-500">
                            <Activity className="w-12 h-12 mx-auto mb-3 opacity-30" />
                            <p className="text-sm font-medium">暂无活动记录</p>
                            <p className="text-xs mt-1">分析用户后活动将显示在这里</p>
                        </div>
                    )}

                    {/* 活动列表 */}
                    <AnimatePresence mode="popLayout">
                        {logs.map((log, index) => {
                            // 根据状态配置样式
                            const getStatusConfig = () => {
                                if (log.status === "QUEUED") return {
                                    cardClass: "bg-amber-500/5 border-amber-500/20 hover:border-amber-500/40",
                                    avatarClass: "bg-amber-500/20",
                                    textClass: "text-amber-400",
                                    icon: <Clock className="w-3.5 h-3.5 text-amber-400" />,
                                    text: "排队中",
                                };
                                if (log.status === "PROCESSING") return {
                                    cardClass: "bg-sky-500/5 border-sky-500/20 hover:border-sky-500/40",
                                    avatarClass: "bg-sky-500/20",
                                    textClass: "text-sky-400",
                                    icon: <Loader2 className="w-3.5 h-3.5 text-sky-400 animate-spin" />,
                                    text: "处理中",
                                };
                                if (log.status === "FAILED") return {
                                    cardClass: "bg-rose-500/5 border-rose-500/20 hover:border-rose-500/40",
                                    avatarClass: "bg-rose-500/20",
                                    textClass: "text-rose-400",
                                    icon: <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />,
                                    text: "失败",
                                };
                                if (log.risk_level === "High") return {
                                    cardClass: "bg-rose-500/5 border-rose-500/20 hover:border-rose-500/40",
                                    avatarClass: "bg-rose-500/20",
                                    textClass: "text-rose-400",
                                    icon: <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />,
                                    text: `高风险 (${Math.round((log.churn_probability ?? 0) * 100)}%)`,
                                };
                                return {
                                    cardClass: "bg-emerald-500/5 border-emerald-500/20 hover:border-emerald-500/40",
                                    avatarClass: "bg-emerald-500/20",
                                    textClass: "text-emerald-400",
                                    icon: <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />,
                                    text: `低风险 (${Math.round((log.churn_probability ?? 0) * 100)}%)`,
                                };
                            };

                            const config = getStatusConfig();

                            return (
                                <motion.div
                                    key={log.doc_id}
                                    initial={{ opacity: 0, y: -10, scale: 0.98 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.95 }}
                                    transition={{
                                        duration: 0.25,
                                        delay: index * 0.03,
                                        ease: "easeOut"
                                    }}
                                    className="mb-3"
                                >
                                    <div className={`p-3 rounded-xl border transition-all duration-200 cursor-default ${config.cardClass}`}>
                                        <div className="flex items-start gap-3">
                                            <Avatar className={`w-9 h-9 ${config.avatarClass}`}>
                                                <AvatarFallback className={`text-xs font-medium ${config.textClass}`}>
                                                    <User className="w-4 h-4" />
                                                </AvatarFallback>
                                            </Avatar>

                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="text-sm font-medium text-slate-200 truncate">
                                                        User #{log.user_id}
                                                    </span>
                                                    {config.icon}
                                                </div>

                                                <div className="flex items-center justify-between">
                                                    <span className={`text-xs font-medium ${config.textClass}`}>
                                                        {config.text}
                                                    </span>
                                                    <span className="text-xs text-slate-500">
                                                        {formatTime(log.timestamp)}
                                                    </span>
                                                </div>

                                                {log.processing_time_ms && (
                                                    <span className="text-xs text-slate-600 mt-1 block">
                                                        耗时 {log.processing_time_ms.toFixed(0)}ms
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            );
                        })}
                    </AnimatePresence>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}
