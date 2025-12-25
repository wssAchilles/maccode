import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Mail, Copy, Send, Sparkles, CheckCircle, ThumbsUp, ThumbsDown, Check, ShieldCheck, AlertCircle, Phone, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { submitFeedback } from "@/services/analysisService";
import { toast } from "sonner";
import { doc, onSnapshot } from "firebase/firestore";
import { db } from "@/lib/firebase";

interface EmailPreviewProps {
    emailContent: string | null;
    userId: string;
    analysisId?: string; // Analysis ID needed for feedback
    callScript?: string | null;
    audioBase64?: string | null;
}

export function EmailPreview({ emailContent, userId, analysisId, callScript, audioBase64 }: EmailPreviewProps) {
    const [copied, setCopied] = useState(false);
    const [completed, setCompleted] = useState(false);
    const [feedbackStatus, setFeedbackStatus] = useState<"none" | "thumbs_up" | "thumbs_down">("none");
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Audit State
    const [auditScore, setAuditScore] = useState<number | null>(null);
    const [auditReason, setAuditReason] = useState<string | null>(null);

    useEffect(() => {
        if (!analysisId) return;

        const unsubscribe = onSnapshot(doc(db, "analysis_logs", analysisId), (doc) => {
            if (doc.exists()) {
                const data = doc.data();
                if (data.audit_score !== undefined) {
                    setAuditScore(data.audit_score);
                    setAuditReason(data.audit_reason);
                }
            }
        });

        return () => unsubscribe();
    }, [analysisId]);

    // 复制到剪贴板
    const handleCopy = async () => {
        if (emailContent) {
            await navigator.clipboard.writeText(emailContent);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    // 提交反馈
    const handleFeedback = async (type: "thumbs_up" | "thumbs_down") => {
        if (!analysisId || isSubmitting || feedbackStatus !== "none") return;

        setIsSubmitting(true);
        // Optimistic update
        setFeedbackStatus(type);

        const success = await submitFeedback(analysisId, userId, type);

        if (success) {
            if (type === "thumbs_up") {
                toast.success("感谢反馈！");
            } else {
                toast("反馈已收到，我们将持续改进。");
            }
        } else {
            // Revert on failure
            setFeedbackStatus("none");
            toast.error("提交反馈失败，请稍后重试");
        }
        setIsSubmitting(false);
    };

    // 空状态处理
    if (!emailContent) {
        return (
            <Card className="bg-slate-900/50 border-slate-700/50 backdrop-blur-sm h-full">
                <CardHeader>
                    <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                        <Mail className="w-4 h-4" />
                        AI 生成邮件
                    </CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col items-center justify-center py-8 text-slate-500">
                    <Mail className="w-12 h-12 mb-3 opacity-50" />
                    <p className="text-sm">低风险用户无需发送挽留邮件</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="bg-slate-900/50 border-slate-700/50 backdrop-blur-sm h-full flex flex-col">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                        <Mail className="w-4 h-4" />
                        AI 生成邮件
                    </CardTitle>
                    <Badge variant="outline" className="border-emerald-500/50 text-emerald-400">
                        <Sparkles className="w-3 h-3 mr-1" />
                        Gemini 2.5 Pro
                    </Badge>
                </div>
            </CardHeader>

            <CardContent className="flex-1 flex flex-col space-y-4">
                {/* 邮件头部模拟 */}
                <div className="p-3 rounded-lg bg-slate-800/80 border border-slate-700/50 space-y-2">
                    <div className="flex items-center gap-2 text-xs">
                        <span className="text-slate-500 w-12">收件人:</span>
                        <span className="text-slate-300">user_{userId}@example.com</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                        <span className="text-slate-500 w-12">主题:</span>
                        <span className="text-slate-300">我们想念您 - 专属福利已送达</span>
                    </div>
                </div>

                {/* 邮件正文 */}
                <div className="flex-1 p-4 rounded-lg bg-slate-950/50 border border-slate-800 
                        overflow-y-auto max-h-[300px]">
                    <div className="prose prose-sm prose-invert max-w-none">
                        {/* 简单渲染，保留换行 */}
                        {emailContent.split('\n').map((line, i) => (
                            <p key={i} className="text-slate-300 text-sm leading-relaxed mb-2">
                                {line || '\u00A0'}
                            </p>
                        ))}
                    </div>
                </div>

                {/* 此处开始 Feedback & Actions */}
                <div className="flex items-center justify-between pt-2 gap-2">
                    <div className="flex gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            className={`h-8 w-8 ${feedbackStatus === 'thumbs_up' ? 'text-green-500 bg-green-500/10' : 'text-slate-500 hover:text-green-500 hover:bg-green-500/10'} `}
                            onClick={() => handleFeedback("thumbs_up")}
                            disabled={feedbackStatus !== "none"}
                        >
                            <ThumbsUp className="w-4 h-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className={`h-8 w-8 ${feedbackStatus === 'thumbs_down' ? 'text-red-500 bg-red-500/10' : 'text-slate-500 hover:text-red-500 hover:bg-red-500/10'} `}
                            onClick={() => handleFeedback("thumbs_down")}
                            disabled={feedbackStatus !== "none"}
                        >
                            <ThumbsDown className="w-4 h-4" />
                        </Button>
                    </div>

                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            className="border-slate-700 hover:bg-slate-800"
                            onClick={handleCopy}
                        >
                            {copied ? (
                                <>
                                    <CheckCircle className="w-3 h-3 mr-2 text-emerald-500" />
                                    已复制
                                </>
                            ) : (
                                <>
                                    <Copy className="w-3 h-3 mr-2" />
                                    复制内容
                                </>
                            )}
                        </Button>
                    </div>
                </div>
            </CardContent>
            {/* AI Audit Report Section */}
            {auditScore !== null && (
                <div className="mt-6 border-t pt-4 px-6"> {/* Added px-6 for padding */}
                    <div className="flex items-center gap-2 mb-3">
                        <ShieldCheck className="w-5 h-5 text-indigo-600" />
                        <h3 className="font-semibold text-slate-200">AI 合规审计报告 (AI Judge)</h3> {/* Changed text color */}
                    </div>

                    <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50"> {/* Changed bg and border */}
                        <div className="flex items-start gap-4">
                            {/* Score Ring */}
                            <div className="relative w-16 h-16 flex-shrink-0">
                                <svg className="w-full h-full transform -rotate-90">
                                    <circle
                                        cx="32"
                                        cy="32"
                                        r="28"
                                        fill="none"
                                        stroke="#334155" /* Changed stroke color */
                                        strokeWidth="6"
                                    />
                                    <circle
                                        cx="32"
                                        cy="32"
                                        r="28"
                                        fill="none"
                                        stroke={auditScore >= 80 ? "#16a34a" : auditScore >= 60 ? "#ca8a04" : "#dc2626"}
                                        strokeWidth="6"
                                        strokeDasharray={`${2 * Math.PI * 28} `}
                                        strokeDashoffset={`${2 * Math.PI * 28 * (1 - auditScore / 100)} `}
                                        className="transition-all duration-1000 ease-out"
                                    />
                                </svg>
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <span className={`text - sm font - bold ${auditScore >= 80 ? "text-green-500" : auditScore >= 60 ? "text-yellow-500" : "text-red-500" /* Changed text colors */
                                        } `}>
                                        {auditScore}
                                    </span>
                                </div>
                            </div>

                            {/* Reasoning */}
                            <div className="flex-1">
                                <p className="text-sm text-slate-400 leading-relaxed"> {/* Changed text color */}
                                    {auditReason}
                                </p>
                                {auditScore < 60 && (
                                    <div className="mt-2 flex items-center gap-1 text-xs text-red-400 bg-red-900/20 px-2 py-1 rounded w-fit border border-red-700/50"> {/* Changed bg, text, and added border */}
                                        <AlertCircle className="w-3 h-3" />
                                        <span>存在合规风险，请人工复核</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}


            {/* Voicemail Section */}
            {callScript && (
                <div className="border-t border-slate-800 p-4 bg-slate-900/30">
                    <div className="flex items-center gap-2 mb-3 text-slate-300">
                        <div className="p-1.5 rounded-md bg-indigo-500/20 text-indigo-400">
                            <Phone className="w-4 h-4" />
                        </div>
                        <span className="text-sm font-medium">Generated Voicemail</span>
                    </div>

                    <div className="space-y-3">
                        <div className="p-3 rounded bg-slate-950 border border-slate-800/60">
                            <p className="text-xs text-slate-400 italic font-serif leading-relaxed">
                                "{callScript}"
                            </p>
                        </div>

                        {audioBase64 && (
                            <div className="bg-slate-800/50 rounded-lg p-2 border border-slate-700/50 flex items-center gap-3">
                                <audio controls className="w-full h-8 opacity-80 hover:opacity-100 transition-opacity" style={{ filter: "invert(0.9) hue-rotate(180deg)" }}>
                                    <source src={`data:audio/mp3;base64,${audioBase64}`} type="audio/mp3" />
                                    Your browser does not support the audio element.
                                </audio>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </Card>
    );
}
