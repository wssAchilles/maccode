import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { BrainCircuit, Play, CheckCircle, Terminal, Cpu } from 'lucide-react';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export type LogType = 'thought' | 'action' | 'observation';

export interface TraceStep {
    step: number;
    type: LogType;
    content: string;
    tool?: string;
    input?: string;
}

interface AgentReasoningLogProps {
    logs: TraceStep[];
    isLoading?: boolean;
}

// ============================================================================
// Component
// ============================================================================

const AgentReasoningLog: React.FC<AgentReasoningLogProps> = ({ logs, isLoading }) => {
    return (
        <Card className="w-full h-[600px] flex flex-col border-none shadow-2xl bg-black/95 text-green-400 font-mono relative overflow-hidden">
            {/* Background Matrix/Grid Effect */}
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none"></div>
            <div className="absolute inset-0 bg-grid-white/[0.02] bg-[length:20px_20px] pointer-events-none"></div>

            <CardHeader className="border-b border-green-900/30 backdrop-blur pb-4 z-10">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Cpu className="w-5 h-5 text-green-500 animate-pulse" />
                        <CardTitle className="text-lg font-bold tracking-wider text-green-100">
                            SENTINEL_CORE // REASONING_ENGINE
                        </CardTitle>
                    </div>
                    {isLoading && (
                        <div className="flex items-center gap-2 text-xs text-green-400">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                            </span>
                            PROCESSING_DATA_STREAMS...
                        </div>
                    )}
                </div>
            </CardHeader>

            <CardContent className="flex-1 p-0 overflow-hidden relative z-10">
                <ScrollArea className="h-full px-4 py-4 w-full">
                    <div className="space-y-6 pb-4">
                        {logs.length === 0 && !isLoading && (
                            <div className="flex flex-col items-center justify-center h-48 text-green-900/50">
                                <Terminal className="w-12 h-12 mb-2 opacity-20" />
                                <p>READY_FOR_INSTRUCTION</p>
                                <p className="text-xs">Waiting for initialization sequence...</p>
                            </div>
                        )}

                        {logs.map((log, index) => (
                            <div
                                key={index}
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
                                        log.type === 'thought' ? "text-blue-400" :
                                            log.type === 'action' ? "text-yellow-400" :
                                                "text-green-400"
                                    )}>
                                        {log.type.toUpperCase()}
                                        {log.type === 'action' && log.tool && <span className="text-white ml-2">:: {log.tool}</span>}
                                    </span>
                                    <span className="text-green-900 ml-auto">STEP_{log.step.toString().padStart(3, '0')}</span>
                                </div>

                                {/* Content */}
                                <div className="text-sm text-green-100/90 leading-relaxed font-sans">
                                    {log.type === 'thought' && (
                                        <p className="italic text-blue-100/80">"{log.content}"</p>
                                    )}

                                    {log.type === 'action' && (
                                        <div className="bg-black/40 rounded p-2 mt-1 border border-yellow-500/20">
                                            <p className="text-xs text-yellow-500/70 mb-1">INPUT PAYLOAD:</p>
                                            <code className="text-xs text-yellow-100 break-all">
                                                {log.input}
                                            </code>
                                        </div>
                                    )}

                                    {log.type === 'observation' && (
                                        <div className="bg-green-950/30 rounded p-2 mt-1 border border-green-500/20">
                                            <p className="text-xs text-green-500/70 mb-1">DATA RETURNED:</p>
                                            <pre className="text-xs text-green-100 whitespace-pre-wrap font-mono">
                                                {log.content}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {/* Scroll Anchor */}
                        <div className="h-1" />
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
};

export default AgentReasoningLog;
