"use client";

/**
 * LiveActivityFeed 组件
 * 
 * 实时监听 Firestore 中的 analysis_logs 集合
 * 展示最近的分析活动流，支持动画效果
 */

import { useEffect, useState } from "react";
import { collection, query, orderBy, limit, onSnapshot } from "firebase/firestore";
import { db } from "@/lib/firebase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Activity, User, AlertTriangle, CheckCircle, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

// 分析日志记录类型
interface AnalysisLog {
    doc_id: string;
    user_id: string;
    churn_probability: number;
    risk_level: "High" | "Low";
    email_subject?: string;
    processing_time_ms: number;
    timestamp?: { seconds: number; nanoseconds: number };
}

export function LiveActivityFeed() {
    const [logs, setLogs] = useState<AnalysisLog[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        // 构建 Firestore 查询
        const logsQuery = query(
            collection(db, "analysis_logs"),
            orderBy("timestamp", "desc"),
            limit(10)
        );

        // 设置实时监听器
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

        // 清理：组件卸载时取消监听
        return () => unsubscribe();
    }, []);

    // 格式化时间戳
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
        <Card className="bg-slate-900/50 border-slate-700/50 backdrop-blur-sm h-full flex flex-col">
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-violet-400" />
                    实时活动流
                    {!isLoading && logs.length > 0 && (
                        <Badge variant="outline" className="ml-auto border-emerald-500/50 text-emerald-400">
                            Live
                        </Badge>
                    )}
                </CardTitle>
            </CardHeader>

            <CardContent className="flex-1 p-0">
                <ScrollArea className="h-[500px] px-4">
                    {/* 加载状态 */}
                    {isLoading && (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="w-6 h-6 animate-spin text-violet-500" />
                        </div>
                    )}

                    {/* 错误状态 */}
                    {error && (
                        <div className="text-center py-8 text-rose-400 text-sm">
                            {error}
                        </div>
                    )}

                    {/* 空状态 */}
                    {!isLoading && !error && logs.length === 0 && (
                        <div className="text-center py-12 text-slate-500">
                            <Activity className="w-10 h-10 mx-auto mb-3 opacity-50" />
                            <p className="text-sm">暂无活动记录</p>
                            <p className="text-xs mt-1">分析用户后活动将显示在这里</p>
                        </div>
                    )}

                    {/* 活动列表 */}
                    <AnimatePresence mode="popLayout">
                        {logs.map((log, index) => (
                            <motion.div
                                key={log.doc_id}
                                initial={{ opacity: 0, y: -20, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                transition={{
                                    duration: 0.3,
                                    delay: index * 0.05,
                                    ease: "easeOut"
                                }}
                                className="mb-3"
                            >
                                <div className={`
                  p-3 rounded-lg border transition-colors duration-200
                  ${log.risk_level === "High"
                                        ? "bg-rose-500/5 border-rose-500/20 hover:border-rose-500/40"
                                        : "bg-emerald-500/5 border-emerald-500/20 hover:border-emerald-500/40"
                                    }
                `}>
                                    <div className="flex items-start gap-3">
                                        {/* 头像 */}
                                        <Avatar className={`
                      w-8 h-8 
                      ${log.risk_level === "High"
                                                ? "bg-rose-500/20"
                                                : "bg-emerald-500/20"
                                            }
                    `}>
                                            <AvatarFallback className={`text-xs font-medium
                        ${log.risk_level === "High"
                                                    ? "text-rose-400"
                                                    : "text-emerald-400"
                                                }
                      `}>
                                                <User className="w-4 h-4" />
                                            </AvatarFallback>
                                        </Avatar>

                                        {/* 内容 */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="text-sm font-medium text-slate-200 truncate">
                                                    User #{log.user_id}
                                                </span>
                                                {log.risk_level === "High" ? (
                                                    <AlertTriangle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
                                                ) : (
                                                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                                                )}
                                            </div>

                                            <div className="flex items-center justify-between">
                                                <span className={`text-xs font-medium
                          ${log.risk_level === "High"
                                                        ? "text-rose-400"
                                                        : "text-emerald-400"
                                                    }
                        `}>
                                                    {log.risk_level === "High" ? "高风险" : "低风险"}
                                                    ({Math.round(log.churn_probability * 100)}%)
                                                </span>
                                                <span className="text-xs text-slate-500">
                                                    {formatTime(log.timestamp)}
                                                </span>
                                            </div>

                                            {/* 处理耗时 */}
                                            <span className="text-xs text-slate-600 mt-1 block">
                                                耗时 {log.processing_time_ms?.toFixed(0) || "N/A"}ms
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}
