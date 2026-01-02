"use client";

/**
 * AgentReasoningLog - 实时作战室日志组件
 * 
 * 功能:
 * - 使用 Firebase onSnapshot 实时监听分析步骤
 * - Glassmorphism 风格 + 黑客帝国动态效果
 * - 自动滚动到底部 (正在打印日志感)
 * - Judge FAIL 显示红色 REJECTED 徽章
 */

import React, { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import {
    BrainCircuit,
    Play,
    CheckCircle,
    Terminal,
    Cpu,
    AlertTriangle,
    XCircle,
    RefreshCw,
    Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Firebase
import { initializeApp, getApps } from 'firebase/app';
import { getFirestore, doc, onSnapshot, DocumentData } from 'firebase/firestore';

// ============================================================================
// Firebase 配置
// ============================================================================

const firebaseConfig = {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "sentinel-churn",
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID
};

// 初始化 Firebase (防止重复初始化)
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
const db = getFirestore(app);

// ============================================================================
// Types
// ============================================================================

export type StepStatus = 'running' | 'completed' | 'warning' | 'error';

export interface AnalysisStep {
    name: string;
    status: StepStatus;
    timestamp?: string;
    details?: string;
    score?: number;
    verdict?: 'PASS' | 'FAIL';
    feedback?: string;
    has_feedback?: boolean;
}

// 传统日志类型 (保持向后兼容)
export type LogType = 'thought' | 'action' | 'observation';

export interface TraceStep {
    step: number;
    type: LogType;
    content: string;
    tool?: string;
    input?: string;
}

interface AgentReasoningLogProps {
    analysisId?: string;  // 新增: 用于实时监听
    logs?: TraceStep[];   // 保持向后兼容
    isLoading?: boolean;
}

// ============================================================================
// 状态图标映射
// ============================================================================

const StatusIcon: Record<StepStatus, React.ReactNode> = {
    running: <Loader2 className="w-4 h-4 animate-spin text-blue-400" />,
    completed: <CheckCircle className="w-4 h-4 text-green-400" />,
    warning: <AlertTriangle className="w-4 h-4 text-amber-400" />,
    error: <XCircle className="w-4 h-4 text-red-400" />
};

const StatusColor: Record<StepStatus, string> = {
    running: "border-blue-500/50 bg-blue-500/5",
    completed: "border-green-500/50 bg-green-500/5",
    warning: "border-amber-500/50 bg-amber-500/5",
    error: "border-red-500/50 bg-red-500/5"
};

// ============================================================================
// Component
// ============================================================================

const AgentReasoningLog: React.FC<AgentReasoningLogProps> = ({
    analysisId,
    logs = [],
    isLoading = false
}) => {
    const [steps, setSteps] = useState<AnalysisStep[]>([]);
    const [riskScore, setRiskScore] = useState<number | null>(null);
    const [isListening, setIsListening] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    // 自动滚动到底部
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [steps, logs]);

    // Firebase onSnapshot 实时监听
    useEffect(() => {
        if (!analysisId) {
            setSteps([]);
            return;
        }

        setIsListening(true);

        const docRef = doc(db, 'analysis_logs', analysisId);
        const unsubscribe = onSnapshot(docRef, (snapshot) => {
            if (snapshot.exists()) {
                const data = snapshot.data() as DocumentData;

                // 更新步骤
                if (data.steps) {
                    setSteps(data.steps as AnalysisStep[]);
                }

                // 更新风险分数
                if (data.risk_score !== undefined) {
                    setRiskScore(data.risk_score);
                }
            }
        }, (error) => {
            console.error('[AgentLog] Firestore 监听错误:', error);
            setIsListening(false);
        });

        return () => {
            unsubscribe();
            setIsListening(false);
        };
    }, [analysisId]);

    // 判断是否有 Judge FAIL
    const hasJudgeFail = steps.some(s => s.verdict === 'FAIL');

    return (
        <Card className="w-full h-[600px] flex flex-col border-none shadow-2xl relative overflow-hidden
                        bg-gradient-to-br from-slate-900/95 via-slate-950/95 to-slate-900/95
                        backdrop-blur-xl">
            {/* Glassmorphism 背景效果 */}
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none"></div>
            <div className="absolute inset-0 bg-grid-white/[0.02] bg-[length:20px_20px] pointer-events-none"></div>

            {/* 动态光晕 */}
            {isLoading && (
                <div className="absolute -top-20 -right-20 w-40 h-40 bg-blue-500/20 rounded-full blur-3xl animate-pulse"></div>
            )}
            {hasJudgeFail && (
                <div className="absolute -bottom-20 -left-20 w-40 h-40 bg-red-500/20 rounded-full blur-3xl animate-pulse"></div>
            )}

            <CardHeader className="border-b border-slate-700/30 backdrop-blur pb-4 z-10">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-xl bg-gradient-to-br from-emerald-600/20 to-cyan-600/20 border border-emerald-500/20">
                            <Cpu className="w-5 h-5 text-emerald-400" />
                        </div>
                        <div>
                            <CardTitle className="text-lg font-heading font-bold text-white tracking-tight">
                                AI Decision Engine
                            </CardTitle>
                            <p className="text-xs text-slate-500 font-mono">
                                {analysisId ? `ID: ${analysisId.slice(0, 8)}...` : 'STANDBY'}
                            </p>
                        </div>
                    </div>

                    {/* 状态指示器 */}
                    <div className="flex items-center gap-3">
                        {isListening && (
                            <Badge variant="outline" className="border-emerald-500/30 text-emerald-400 bg-emerald-500/10 animate-pulse">
                                <span className="relative flex h-2 w-2 mr-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                </span>
                                LIVE
                            </Badge>
                        )}
                        {(isLoading || steps.some(s => s.status === 'running')) && (
                            <div className="flex items-center gap-2 text-xs text-blue-400 font-mono">
                                <RefreshCw className="w-3 h-3 animate-spin" />
                                PROCESSING...
                            </div>
                        )}
                    </div>
                </div>
            </CardHeader>

            <CardContent className="flex-1 p-0 overflow-hidden relative z-10">
                <ScrollArea className="h-full" ref={scrollRef}>
                    <div className="px-4 py-4 space-y-4">
                        {/* 空状态 */}
                        {steps.length === 0 && logs.length === 0 && !isLoading && (
                            <div className="flex flex-col items-center justify-center h-48 text-slate-600">
                                <Terminal className="w-12 h-12 mb-3 opacity-30" />
                                <p className="font-mono text-sm">READY_FOR_INSTRUCTION</p>
                                <p className="text-xs text-slate-700 mt-1">等待分析任务...</p>
                            </div>
                        )}

                        {/* 实时步骤 (优先显示) */}
                        {steps.map((step, index) => (
                            <div
                                key={`step-${index}`}
                                className={cn(
                                    "relative rounded-xl border p-4 transition-all duration-300",
                                    "animate-in fade-in slide-in-from-left-2",
                                    StatusColor[step.status],
                                    step.status === 'running' && "ring-1 ring-blue-500/30"
                                )}
                            >
                                {/* 步骤头部 */}
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        {StatusIcon[step.status]}
                                        <span className="font-medium text-white text-sm">
                                            {step.name}
                                        </span>
                                    </div>

                                    {/* Judge 判决徽章 */}
                                    {step.verdict && (
                                        <Badge
                                            variant="outline"
                                            className={cn(
                                                "font-mono text-xs",
                                                step.verdict === 'PASS'
                                                    ? "border-green-500/50 text-green-400 bg-green-500/10"
                                                    : "border-red-500/50 text-red-400 bg-red-500/10 animate-pulse"
                                            )}
                                        >
                                            {step.verdict === 'PASS' ? '✓ APPROVED' : '✕ REJECTED'}
                                            {step.score !== undefined && ` (${step.score})`}
                                        </Badge>
                                    )}
                                </div>

                                {/* 详情 */}
                                {step.details && (
                                    <p className="text-xs text-slate-400 font-mono mb-2">
                                        {step.details}
                                    </p>
                                )}

                                {/* Judge 反馈 (FAIL 时显示) */}
                                {step.feedback && step.verdict === 'FAIL' && (
                                    <div className="mt-3 p-3 rounded-lg bg-red-950/30 border border-red-500/20">
                                        <p className="text-xs text-red-400 font-medium mb-1 flex items-center gap-1">
                                            <AlertTriangle className="w-3 h-3" />
                                            Judge Feedback:
                                        </p>
                                        <p className="text-xs text-red-200/80">{step.feedback}</p>
                                    </div>
                                )}

                                {/* 时间戳 */}
                                {step.timestamp && (
                                    <p className="text-[10px] text-slate-600 mt-2 font-mono">
                                        {new Date(step.timestamp).toLocaleTimeString()}
                                    </p>
                                )}
                            </div>
                        ))}

                        {/* 传统日志 (向后兼容) */}
                        {logs.map((log, index) => (
                            <div
                                key={`log-${index}`}
                                className={cn(
                                    "relative pl-6 border-l-2 ml-2 transition-all duration-500 animate-in fade-in slide-in-from-left-2",
                                    log.type === 'thought' ? "border-blue-500/50" :
                                        log.type === 'action' ? "border-yellow-500/50" :
                                            "border-green-500/50"
                                )}
                            >
                                {/* Timeline Dot */}
                                <div className={cn(
                                    "absolute -left-[5px] top-0 w-2 h-2 rounded-full",
                                    log.type === 'thought' ? "bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]" :
                                        log.type === 'action' ? "bg-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)]" :
                                            "bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]"
                                )} />

                                {/* Header */}
                                <div className="flex items-center gap-2 mb-1 text-xs uppercase tracking-widest opacity-70">
                                    {log.type === 'thought' && <BrainCircuit className="w-3 h-3 text-blue-400" />}
                                    {log.type === 'action' && <Play className="w-3 h-3 text-yellow-400" />}
                                    {log.type === 'observation' && <CheckCircle className="w-3 h-3 text-green-400" />}

                                    <span className={cn(
                                        "font-mono",
                                        log.type === 'thought' ? "text-blue-400" :
                                            log.type === 'action' ? "text-yellow-400" :
                                                "text-green-400"
                                    )}>
                                        {log.type.toUpperCase()}
                                        {log.type === 'action' && log.tool && <span className="text-white ml-2">:: {log.tool}</span>}
                                    </span>
                                    <span className="text-slate-700 ml-auto">STEP_{log.step.toString().padStart(3, '0')}</span>
                                </div>

                                {/* Content */}
                                <div className="text-sm text-slate-300 leading-relaxed">
                                    {log.type === 'thought' && (
                                        <p className="italic text-blue-200/80">"{log.content}"</p>
                                    )}

                                    {log.type === 'action' && (
                                        <div className="bg-slate-900/50 rounded-lg p-2 mt-1 border border-yellow-500/20">
                                            <p className="text-xs text-yellow-500/70 mb-1 font-mono">INPUT PAYLOAD:</p>
                                            <code className="text-xs text-yellow-100 break-all">
                                                {log.input}
                                            </code>
                                        </div>
                                    )}

                                    {log.type === 'observation' && (
                                        <div className="bg-green-950/20 rounded-lg p-2 mt-1 border border-green-500/20">
                                            <p className="text-xs text-green-500/70 mb-1 font-mono">DATA RETURNED:</p>
                                            <pre className="text-xs text-green-100 whitespace-pre-wrap font-mono">
                                                {log.content}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {/* 滚动锚点 */}
                        <div className="h-1" />
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
};

export default AgentReasoningLog;
