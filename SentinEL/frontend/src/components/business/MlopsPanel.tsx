import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ShieldCheck, AlertTriangle, RefreshCw, Activity, CheckCircle, XCircle } from 'lucide-react';
import { mlopsService } from '@/services/mlopsService';

interface AuditLog {
    timestamp: number;
    user_id: string;
    score: number;
    flags: string[];
    reasoning: string;
}

interface ModelHealth {
    model_version: string;
    last_trained: string;
    drift_status: string;
    drift_magnitude: number;
    serving_accuracy: number;
}

const MlopsPanel = () => {
    const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
    const [modelHealth, setModelHealth] = useState<ModelHealth | null>(null);
    const [isRetraining, setIsRetraining] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 30000); // Auto refresh every 30s
        return () => clearInterval(interval);
    }, []);

    const fetchData = async () => {
        try {
            const logs = await mlopsService.getAuditLogs();
            setAuditLogs(logs);

            const health = await mlopsService.getModelHealth();
            setModelHealth(health);
        } catch (error) {
            console.error("Failed to fetch MLOps data", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleRetrain = async () => {
        setIsRetraining(true);
        try {
            await mlopsService.triggerTraining();
            // Refresh logic handled by parent or toast ideally, here just simple done
            alert("Retraining Pipeline Triggered Successfully!");
        } catch (error) {
            alert("Failed to trigger pipeline.");
        } finally {
            setIsRetraining(false);
        }
    };

    return (
        <Card className="w-full bg-slate-900 border-slate-800 text-slate-100 shadow-xl overflow-hidden">
            <CardHeader className="border-b border-slate-800 pb-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <ShieldCheck className="w-5 h-5 text-indigo-400" />
                        <CardTitle className="text-lg font-semibold">Enterprise MLOps & Governance</CardTitle>
                    </div>
                    <Badge variant="outline" className="bg-indigo-950/30 text-indigo-400 border-indigo-500/30">
                        <Activity className="w-3 h-3 mr-1 animate-pulse" />
                        Active Monitoring
                    </Badge>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-800 h-[300px]">

                    {/* Column 1: Model Health */}
                    <div className="p-4 flex flex-col justify-between bg-slate-900/50">
                        <div>
                            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Model Health</h4>
                            {modelHealth ? (
                                <div className="space-y-4">
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-slate-400">Version</span>
                                        <Badge className="bg-slate-800">{modelHealth.model_version}</Badge>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-slate-400">Drift Status</span>
                                        <Badge variant={modelHealth.drift_status === "Normal" ? "default" : "destructive"}
                                            className={modelHealth.drift_status === "Normal" ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30" : ""}>
                                            {modelHealth.drift_status}
                                        </Badge>
                                    </div>
                                    <div className="space-y-1">
                                        <div className="flex justify-between text-xs text-slate-400">
                                            <span>Accuracy</span>
                                            <span>{(modelHealth.serving_accuracy * 100).toFixed(1)}%</span>
                                        </div>
                                        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                                            <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${modelHealth.serving_accuracy * 100}%` }} />
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="text-sm text-slate-500">Loading metrics...</div>
                            )}
                        </div>
                        <Button
                            variant="outline"
                            className="w-full mt-4 bg-indigo-600 hover:bg-indigo-700 text-white border-none"
                            onClick={handleRetrain}
                            disabled={isRetraining}
                        >
                            {isRetraining ? (
                                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                            ) : (
                                <RefreshCw className="w-4 h-4 mr-2" />
                            )}
                            Trigger Retraining
                        </Button>
                    </div>

                    {/* Column 2 & 3: Audit Logs */}
                    <div className="md:col-span-2 p-4 flex flex-col h-full">
                        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">LLM-as-a-Judge Audit Stream</h4>
                        <ScrollArea className="flex-1 -mr-3 pr-3">
                            <div className="space-y-3">
                                {auditLogs.length === 0 ? (
                                    <div className="text-center text-slate-500 py-10 text-sm">No validation issues detected recently.</div>
                                ) : (
                                    auditLogs.map((log, idx) => (
                                        <div key={idx} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50 flex flex-col gap-2">
                                            <div className="flex justify-between items-start">
                                                <div className="flex items-center gap-2">
                                                    {log.score >= 8 ? (
                                                        <CheckCircle className="w-4 h-4 text-emerald-400" />
                                                    ) : (
                                                        <AlertTriangle className="w-4 h-4 text-amber-400" />
                                                    )}
                                                    <span className="text-sm font-medium text-slate-200">User: {log.user_id}</span>
                                                </div>
                                                <span className="text-xs text-slate-500 font-mono">
                                                    {new Date(log.timestamp * 1000).toLocaleTimeString()}
                                                </span>
                                            </div>
                                            <p className="text-xs text-slate-400 line-clamp-2">
                                                {log.reasoning}
                                            </p>
                                            <div className="flex gap-2 mt-1">
                                                <Badge variant="secondary" className="text-[10px] bg-slate-900 border-slate-700">
                                                    Score: {log.score}/10
                                                </Badge>
                                                {log.flags.map(flag => (
                                                    <Badge key={flag} variant="destructive" className="text-[10px]">
                                                        {flag}
                                                    </Badge>
                                                ))}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </ScrollArea>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};

export default MlopsPanel;
