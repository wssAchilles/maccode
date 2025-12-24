"use client";

/**
 * EmailPreview 组件
 * 模拟邮件客户端 UI，展示 AI 生成的挽留邮件
 * 支持 Markdown 格式渲染
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Mail, Copy, Send, Sparkles, CheckCircle } from "lucide-react";
import { useState } from "react";

interface EmailPreviewProps {
    emailContent: string | null;
    userId: string;
}

export function EmailPreview({ emailContent, userId }: EmailPreviewProps) {
    const [copied, setCopied] = useState(false);

    // 复制到剪贴板
    const handleCopy = async () => {
        if (emailContent) {
            await navigator.clipboard.writeText(emailContent);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
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

                {/* 操作按钮 */}
                <div className="flex gap-2 pt-2">
                    <Button
                        variant="outline"
                        size="sm"
                        className="flex-1 border-slate-700 hover:bg-slate-800"
                        onClick={handleCopy}
                    >
                        {copied ? (
                            <>
                                <CheckCircle className="w-4 h-4 mr-2 text-emerald-500" />
                                已复制
                            </>
                        ) : (
                            <>
                                <Copy className="w-4 h-4 mr-2" />
                                复制内容
                            </>
                        )}
                    </Button>
                    <Button
                        size="sm"
                        className="flex-1 bg-violet-600 hover:bg-violet-700"
                    >
                        <Send className="w-4 h-4 mr-2" />
                        发送邮件
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}
