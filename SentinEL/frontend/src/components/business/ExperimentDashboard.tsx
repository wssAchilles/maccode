"use client";

import React, { useEffect, useState } from "react";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    BarChart,
    Bar,
} from "recharts";
import { Activity, Zap, Clock, BarChart3, TrendingUp } from "lucide-react";
import { db } from "@/lib/firebase";
import { collection, query, orderBy, limit, onSnapshot } from "firebase/firestore";

interface ExperimentMetrics {
    group: string;
    avgLatency: number;
    avgQuality: number;
    count: number;
    latencyTrend: { time: string; value: number }[];
}

interface AnalysisLog {
    id: string;
    experiment_group?: string;
    model_used?: string;
    processing_time_ms?: number;
    audit_score?: number;
    timestamp?: any;
}

export function ExperimentDashboard() {
    const [groupA, setGroupA] = useState<ExperimentMetrics>({
        group: "A",
        avgLatency: 0,
        avgQuality: 0,
        count: 0,
        latencyTrend: [],
    });
    const [groupB, setGroupB] = useState<ExperimentMetrics>({
        group: "B",
        avgLatency: 0,
        avgQuality: 0,
        count: 0,
        latencyTrend: [],
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // 监听 Firestore analysis_logs 集合
        const logsRef = collection(db, "analysis_logs");
        const q = query(logsRef, orderBy("timestamp", "desc"), limit(100));

        const unsubscribe = onSnapshot(q, (snapshot) => {
            const logs: AnalysisLog[] = snapshot.docs.map((doc) => ({
                id: doc.id,
                ...doc.data(),
            }));

            // 按实验组分类
            const groupALogs = logs.filter((log) => log.experiment_group === "A");
            const groupBLogs = logs.filter((log) => log.experiment_group === "B");

            // 计算指标
            const calcMetrics = (
                groupLogs: AnalysisLog[],
                groupName: string
            ): ExperimentMetrics => {
                const validLatency = groupLogs.filter(
                    (log) => log.processing_time_ms && log.processing_time_ms > 0
                );
                const validQuality = groupLogs.filter(
                    (log) => log.audit_score && log.audit_score > 0
                );

                const avgLatency =
                    validLatency.length > 0
                        ? validLatency.reduce((sum, log) => sum + (log.processing_time_ms || 0), 0) /
                        validLatency.length
                        : 0;

                const avgQuality =
                    validQuality.length > 0
                        ? validQuality.reduce((sum, log) => sum + (log.audit_score || 0), 0) /
                        validQuality.length
                        : 0;

                // 生成延迟趋势 (最近 10 条)
                const latencyTrend = validLatency.slice(0, 10).reverse().map((log, idx) => ({
                    time: `#${idx + 1}`,
                    value: log.processing_time_ms || 0,
                }));

                return {
                    group: groupName,
                    avgLatency: Math.round(avgLatency),
                    avgQuality: Math.round(avgQuality * 10) / 10,
                    count: groupLogs.length,
                    latencyTrend,
                };
            };

            setGroupA(calcMetrics(groupALogs, "A"));
            setGroupB(calcMetrics(groupBLogs, "B"));
            setLoading(false);
        });

        return () => unsubscribe();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
        );
    }

    const trafficData = [
        { name: "Group A (Pro)", value: groupA.count, fill: "#6366f1" },
        { name: "Group B (Flash)", value: groupB.count, fill: "#22c55e" },
    ];

    const latencyCompare = [
        { name: "Group A", latency: groupA.avgLatency },
        { name: "Group B", latency: groupB.avgLatency },
    ];

    return (
        <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-6 border border-slate-700">
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                    <Activity className="w-6 h-6 text-purple-400" />
                </div>
                <div>
                    <h3 className="text-xl font-bold text-white">A/B 测试实验看板</h3>
                    <p className="text-sm text-slate-400">模型性能对比分析</p>
                </div>
            </div>

            {/* Vs Mode 对比卡片 */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                {/* Group A */}
                <div className="bg-indigo-500/10 rounded-xl p-4 border border-indigo-500/30">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-lg font-bold text-indigo-400">Group A</span>
                        <span className="text-xs text-slate-400 bg-slate-700 px-2 py-1 rounded">
                            gemini-1.5-pro
                        </span>
                    </div>
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <span className="text-slate-400 text-sm flex items-center gap-1">
                                <Clock className="w-4 h-4" /> 平均延迟
                            </span>
                            <span className="text-white font-mono">
                                {groupA.avgLatency.toLocaleString()}ms
                            </span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-slate-400 text-sm flex items-center gap-1">
                                <TrendingUp className="w-4 h-4" /> 审计分
                            </span>
                            <span className="text-white font-mono">{groupA.avgQuality || "N/A"}</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-slate-400 text-sm flex items-center gap-1">
                                <BarChart3 className="w-4 h-4" /> 请求数
                            </span>
                            <span className="text-white font-mono">{groupA.count}</span>
                        </div>
                    </div>
                </div>

                {/* Group B */}
                <div className="bg-emerald-500/10 rounded-xl p-4 border border-emerald-500/30">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-lg font-bold text-emerald-400">Group B</span>
                        <span className="text-xs text-slate-400 bg-slate-700 px-2 py-1 rounded">
                            gemini-1.5-flash
                        </span>
                    </div>
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <span className="text-slate-400 text-sm flex items-center gap-1">
                                <Zap className="w-4 h-4" /> 平均延迟
                            </span>
                            <span className="text-white font-mono">
                                {groupB.avgLatency.toLocaleString()}ms
                            </span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-slate-400 text-sm flex items-center gap-1">
                                <TrendingUp className="w-4 h-4" /> 审计分
                            </span>
                            <span className="text-white font-mono">{groupB.avgQuality || "N/A"}</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-slate-400 text-sm flex items-center gap-1">
                                <BarChart3 className="w-4 h-4" /> 请求数
                            </span>
                            <span className="text-white font-mono">{groupB.count}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* 图表区域 */}
            <div className="grid grid-cols-2 gap-4">
                {/* 延迟对比柱状图 */}
                <div className="bg-slate-800/50 rounded-xl p-4">
                    <h4 className="text-sm font-medium text-slate-400 mb-3">延迟对比 (ms)</h4>
                    <ResponsiveContainer width="100%" height={150}>
                        <BarChart data={latencyCompare}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis dataKey="name" tick={{ fill: "#94a3b8" }} />
                            <YAxis tick={{ fill: "#94a3b8" }} />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: "#1e293b",
                                    border: "1px solid #334155",
                                    borderRadius: "8px",
                                }}
                            />
                            <Bar dataKey="latency" fill="#6366f1" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* 流量分布饼图 */}
                <div className="bg-slate-800/50 rounded-xl p-4">
                    <h4 className="text-sm font-medium text-slate-400 mb-3">流量分布</h4>
                    <ResponsiveContainer width="100%" height={150}>
                        <BarChart data={trafficData} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis type="number" tick={{ fill: "#94a3b8" }} />
                            <YAxis dataKey="name" type="category" tick={{ fill: "#94a3b8" }} width={100} />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: "#1e293b",
                                    border: "1px solid #334155",
                                    borderRadius: "8px",
                                }}
                            />
                            <Bar dataKey="value" radius={[0, 4, 4, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* 延迟趋势曲线 */}
            {(groupA.latencyTrend.length > 0 || groupB.latencyTrend.length > 0) && (
                <div className="mt-4 bg-slate-800/50 rounded-xl p-4">
                    <h4 className="text-sm font-medium text-slate-400 mb-3">延迟趋势 (最近请求)</h4>
                    <ResponsiveContainer width="100%" height={200}>
                        <LineChart>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis dataKey="time" tick={{ fill: "#94a3b8" }} />
                            <YAxis tick={{ fill: "#94a3b8" }} />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: "#1e293b",
                                    border: "1px solid #334155",
                                    borderRadius: "8px",
                                }}
                            />
                            <Legend />
                            <Line
                                data={groupA.latencyTrend}
                                type="monotone"
                                dataKey="value"
                                name="Group A (Pro)"
                                stroke="#6366f1"
                                strokeWidth={2}
                                dot={{ fill: "#6366f1" }}
                            />
                            <Line
                                data={groupB.latencyTrend}
                                type="monotone"
                                dataKey="value"
                                name="Group B (Flash)"
                                stroke="#22c55e"
                                strokeWidth={2}
                                dot={{ fill: "#22c55e" }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
}

export default ExperimentDashboard;
