"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Activity,
    RefreshCw,
    ShieldCheck,
    Terminal,
    CheckCircle2,
    AlertTriangle,
    Clock,
    Server
} from "lucide-react";
import { toast } from "sonner";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from "@/components/ui/table";

// Type definitions
interface AuditLog {
    id?: string;
    timestamp: string; // ISO string
    user_id: string;
    audit_score?: number; // Updated to match Firestore schema
    audit_reason?: string;
    score?: number; // Compatibility
    reason?: string;
    is_compliant?: boolean;
}

export function MlopsPanel() {
    const [isTraining, setIsTraining] = useState(false);
    const [lastRetrained, setLastRetrained] = useState<string>("2 days ago");
    const [modelVersion, setModelVersion] = useState<string>("v2.1.0");
    const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
    const [loadingLogs, setLoadingLogs] = useState(true);

    // Mock fetching logs (replace with API call)
    useEffect(() => {
        fetchAuditLogs();
    }, []);

    const fetchAuditLogs = async () => {
        try {
            // For now, let's use the API we just created
            // const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
            // const res = await fetch(`${apiUrl}/api/v1/audit-logs`);
            // const data = await res.json();

            // Or use Firestore snapshot if we want real-time here too, 
            // but let's stick to the request requirement of using the API or Mock.

            // Mock data for display
            const mockLogs: AuditLog[] = [
                {
                    timestamp: new Date().toISOString(),
                    user_id: "user_007",
                    audit_score: 98,
                    audit_reason: "完全合规，语气专业。",
                    is_compliant: true
                },
                {
                    timestamp: new Date(Date.now() - 3600000).toISOString(),
                    user_id: "user_892",
                    audit_score: 55,
                    audit_reason: "检测到虚假承诺风险：'免费送iPhone'。",
                    is_compliant: false
                },
                {
                    timestamp: new Date(Date.now() - 7200000).toISOString(),
                    user_id: "user_101",
                    audit_score: 88,
                    audit_reason: "符合标准流程。",
                    is_compliant: true
                }
            ];
            setAuditLogs(mockLogs);
        } catch (error) {
            console.error("Failed to fetch logs", error);
        } finally {
            setLoadingLogs(false);
        }
    };

    const handleTriggerRetraining = async () => {
        setIsTraining(true);
        toast.info("Initializing Vertex AI Pipeline...");

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
            const response = await fetch(`${apiUrl}/api/v1/retrain`, {
                method: 'POST',
            });

            if (!response.ok) throw new Error("Pipeline trigger failed");

            const data = await response.json();

            toast.success("Vertex AI Pipeline Job Submitted", {
                description: `Job ID: ${data.job_id || 'unknown'}`,
                duration: 5000,
            });

            // Simulate updating state
            setTimeout(() => {
                setLastRetrained("Just now");
                setIsTraining(false);
            }, 2000);

        } catch (error) {
            console.error(error);
            toast.error("Failed to start retraining pipeline");
            setIsTraining(false);
        }
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
            {/* Section 1: Pipeline Health */}
            <Card className="bg-slate-900/50 border-slate-700/50 backdrop-blur-sm lg:col-span-1">
                <CardHeader>
                    <CardTitle className="text-lg font-medium text-white flex items-center gap-2">
                        <Activity className="w-5 h-5 text-blue-400" />
                        CT Pipeline Health
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="space-y-4">
                        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                            <div className="flex items-center gap-3">
                                <Server className="w-4 h-4 text-slate-400" />
                                <span className="text-sm text-slate-300">Model Version</span>
                            </div>
                            <Badge variant="outline" className="text-emerald-400 border-emerald-500/20 bg-emerald-500/10">
                                {modelVersion}
                            </Badge>
                        </div>

                        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                            <div className="flex items-center gap-3">
                                <Clock className="w-4 h-4 text-slate-400" />
                                <span className="text-sm text-slate-300">Last Retrained</span>
                            </div>
                            <span className="text-sm text-slate-400">{lastRetrained}</span>
                        </div>
                    </div>

                    <Button
                        onClick={handleTriggerRetraining}
                        disabled={isTraining}
                        className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
                    >
                        {isTraining ? (
                            <>
                                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                                Submitting Job...
                            </>
                        ) : (
                            <>
                                <RefreshCw className="w-4 h-4 mr-2" />
                                Trigger Retraining System
                            </>
                        )}
                    </Button>

                    {isTraining && (
                        <div className="text-xs text-center text-slate-500 animate-pulse">
                            Communicating with Vertex AI...
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Section 2: AI Audit Log */}
            <Card className="bg-slate-900/50 border-slate-700/50 backdrop-blur-sm lg:col-span-2">
                <CardHeader>
                    <CardTitle className="text-lg font-medium text-white flex items-center gap-2">
                        <ShieldCheck className="w-5 h-5 text-purple-400" />
                        AI Governance Audit Log
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border border-slate-700/50 overflow-hidden">
                        <Table>
                            <TableHeader className="bg-slate-800/50">
                                <TableRow className="border-slate-700 hover:bg-transparent">
                                    <TableHead className="text-slate-400 w-[180px]">Timestamp</TableHead>
                                    <TableHead className="text-slate-400">User ID</TableHead>
                                    <TableHead className="text-slate-400 w-[100px]">Score</TableHead>
                                    <TableHead className="text-slate-400">Audit Comment</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loadingLogs ? (
                                    <TableRow>
                                        <TableCell colSpan={4} className="text-center py-8 text-slate-500">
                                            Loading audit logs...
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    auditLogs.map((log, idx) => (
                                        <TableRow key={idx} className="border-slate-700/50 hover:bg-slate-800/30">
                                            <TableCell className="font-mono text-xs text-slate-500">
                                                {new Date(log.timestamp).toLocaleString()}
                                            </TableCell>
                                            <TableCell className="text-slate-300 font-medium">
                                                {log.user_id}
                                            </TableCell>
                                            <TableCell>
                                                <Badge
                                                    className={`
                                                        ${(log.score ?? log.audit_score ?? 0) >= 90 ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                                            (log.score ?? log.audit_score ?? 0) < 60 ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                                                                'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'}
                                                    `}
                                                    variant="outline"
                                                >
                                                    {(log.score ?? log.audit_score ?? 0)}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-sm text-slate-400 max-w-[300px] truncate" title={log.reason ?? log.audit_reason}>
                                                {log.reason ?? log.audit_reason}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
