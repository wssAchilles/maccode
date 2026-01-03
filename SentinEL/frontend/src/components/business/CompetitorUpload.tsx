"use client";

import { useState, useRef } from "react";
import { Upload, X, Image as ImageIcon, Loader2, CheckCircle2, AlertCircle, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { analyzeCompetitorImage } from "@/services/analysisService";

// 竞品情报类型定义
interface CompetitorIntelligence {
    competitor_name: string;
    offer_price: string;
    offer_details: string;
    weakness: string;
}

interface CompetitorUploadProps {
    onImageSelect: (base64: string | null) => void;
    analysisId?: string; // 关联到特定分析会话
    onIntelligenceReceived?: (intel: CompetitorIntelligence) => void; // 回调通知父组件
}

export function CompetitorUpload({ onImageSelect, analysisId, onIntelligenceReceived }: CompetitorUploadProps) {
    const [preview, setPreview] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analysisResult, setAnalysisResult] = useState<CompetitorIntelligence | null>(null);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);

    const handleFile = async (file: File) => {
        if (!file.type.startsWith("image/")) {
            setError("仅支持图片文件");
            return;
        }

        // 保存文件引用
        setSelectedFile(file);
        setError(null);
        setAnalysisResult(null);

        // 生成预览
        const reader = new FileReader();
        reader.onloadend = () => {
            const base64 = reader.result as string;
            setPreview(base64);
            onImageSelect(base64);
        };
        reader.readAsDataURL(file);

        // 自动开始分析
        await analyzeImage(file);
    };

    const analyzeImage = async (file: File) => {
        setIsAnalyzing(true);
        setError(null);

        try {
            const result = await analyzeCompetitorImage(file, analysisId);
            setAnalysisResult(result);

            // 通知父组件
            if (onIntelligenceReceived) {
                onIntelligenceReceived(result);
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : "分析失败，请重试";
            setError(errorMessage);
            console.error("Competitor analysis failed:", err);
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files?.[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    const clearImage = () => {
        setPreview(null);
        setSelectedFile(null);
        setAnalysisResult(null);
        setError(null);
        onImageSelect(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    const retryAnalysis = () => {
        if (selectedFile) {
            analyzeImage(selectedFile);
        }
    };

    return (
        <div className="w-full">
            <div className="flex items-center gap-2 mb-2">
                <Target className="w-4 h-4 text-orange-400" />
                <span className="text-sm font-medium text-slate-300">竞品情报分析</span>
                {analysisResult && (
                    <Badge variant="outline" className="ml-auto text-xs border-orange-500/50 text-orange-400 bg-orange-500/10">
                        已检测
                    </Badge>
                )}
            </div>

            {preview ? (
                <div className="space-y-3">
                    {/* 图片预览 */}
                    <div className="relative group rounded-lg overflow-hidden border border-slate-700/50 bg-slate-900/50">
                        <img
                            src={preview}
                            alt="Competitor Offer"
                            className={cn(
                                "w-full h-32 object-cover transition-all duration-300",
                                isAnalyzing ? "opacity-50 blur-sm" : "opacity-80 group-hover:opacity-100"
                            )}
                        />

                        {/* Loading 叠加层 */}
                        {isAnalyzing && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/60 backdrop-blur-sm">
                                <Loader2 className="w-8 h-8 text-orange-400 animate-spin mb-2" />
                                <span className="text-xs text-slate-300">AI 正在分析竞品...</span>
                            </div>
                        )}

                        {/* 关闭按钮 */}
                        {!isAnalyzing && (
                            <Button
                                variant="destructive"
                                size="icon"
                                className="absolute top-2 right-2 h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                                onClick={clearImage}
                            >
                                <X className="w-4 h-4" />
                            </Button>
                        )}

                        {/* 状态栏 */}
                        <div className={cn(
                            "absolute bottom-0 left-0 right-0 p-2 text-center transition-colors",
                            analysisResult ? "bg-orange-500/20" : error ? "bg-red-500/20" : "bg-black/60"
                        )}>
                            {isAnalyzing ? (
                                <span className="text-xs text-white animate-pulse">正在识别竞品优惠...</span>
                            ) : analysisResult ? (
                                <div className="flex items-center justify-center gap-1">
                                    <CheckCircle2 className="w-3 h-3 text-orange-400" />
                                    <span className="text-xs text-orange-300">分析完成</span>
                                </div>
                            ) : error ? (
                                <div className="flex items-center justify-center gap-1">
                                    <AlertCircle className="w-3 h-3 text-red-400" />
                                    <span className="text-xs text-red-300">分析失败</span>
                                </div>
                            ) : (
                                <span className="text-xs text-white">图片已就绪</span>
                            )}
                        </div>
                    </div>

                    {/* 分析结果展示 */}
                    {analysisResult && (
                        <div className="rounded-lg border border-orange-500/30 bg-gradient-to-br from-orange-500/10 to-slate-900/50 p-3 space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-semibold text-orange-400 uppercase tracking-wide">市场情报</span>
                                <Target className="w-4 h-4 text-orange-400" />
                            </div>

                            <div className="grid grid-cols-2 gap-2 text-xs">
                                <div className="space-y-1">
                                    <span className="text-slate-500">竞品</span>
                                    <p className="font-medium text-white truncate">{analysisResult.competitor_name}</p>
                                </div>
                                <div className="space-y-1">
                                    <span className="text-slate-500">价格</span>
                                    <p className="font-bold text-orange-400">{analysisResult.offer_price}</p>
                                </div>
                            </div>

                            {analysisResult.offer_details && (
                                <div className="text-xs space-y-1 pt-1 border-t border-slate-700/50">
                                    <span className="text-slate-500">优惠详情</span>
                                    <p className="text-slate-300 leading-relaxed">{analysisResult.offer_details}</p>
                                </div>
                            )}

                            {analysisResult.weakness && (
                                <div className="text-xs space-y-1 pt-1 border-t border-slate-700/50">
                                    <span className="text-slate-500">🎯 可利用弱点</span>
                                    <p className="text-emerald-400 leading-relaxed text-xs">{analysisResult.weakness}</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* 错误状态 */}
                    {error && (
                        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3">
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-red-400">{error}</span>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-6 text-xs text-red-400 hover:text-red-300 hover:bg-red-500/20"
                                    onClick={retryAnalysis}
                                >
                                    重试
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            ) : (
                <div
                    className={cn(
                        "relative border-2 border-dashed rounded-lg p-6 transition-all duration-200 flex flex-col items-center justify-center text-center gap-2",
                        isDragging
                            ? "border-orange-500 bg-orange-500/10"
                            : "border-slate-700 hover:border-orange-500/50 hover:bg-slate-800/50"
                    )}
                    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={handleDrop}
                >
                    <input
                        type="file"
                        ref={fileInputRef}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                        accept="image/*"
                        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                    />
                    <div className="p-2 rounded-full bg-slate-800 border border-slate-700 pointer-events-none">
                        <Upload className="w-5 h-5 text-slate-400" />
                    </div>
                    <div className="space-y-1 pointer-events-none">
                        <p className="text-xs font-medium text-slate-300">
                            上传竞品优惠截图
                        </p>
                        <p className="text-[10px] text-slate-500">
                            拖拽或点击选择 · AI 自动识别
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
