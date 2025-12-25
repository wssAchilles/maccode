import { useState, useRef } from "react";
import { Upload, X, Image as ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface CompetitorUploadProps {
    onImageSelect: (base64: string | null) => void;
}

export function CompetitorUpload({ onImageSelect }: CompetitorUploadProps) {
    const [preview, setPreview] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFile = (file: File) => {
        if (!file.type.startsWith("image/")) return;

        const reader = new FileReader();
        reader.onloadend = () => {
            const base64 = reader.result as string;
            setPreview(base64);
            onImageSelect(base64);
        };
        reader.readAsDataURL(file);
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
        onImageSelect(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    return (
        <div className="w-full">
            <div className="flex items-center gap-2 mb-2">
                <ImageIcon className="w-4 h-4 text-violet-400" />
                <span className="text-sm font-medium text-slate-300">Competitor Analysis (Optional)</span>
            </div>

            {preview ? (
                <div className="relative group rounded-lg overflow-hidden border border-slate-700/50 bg-slate-900/50">
                    <img
                        src={preview}
                        alt="Competitor Offer"
                        className="w-full h-32 object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                    />
                    <Button
                        variant="destructive"
                        size="icon"
                        className="absolute top-2 right-2 h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={clearImage}
                    >
                        <X className="w-4 h-4" />
                    </Button>
                    <div className="absolute bottom-0 left-0 right-0 bg-black/60 p-1 text-center">
                        <span className="text-xs text-white">Image Ready for Analysis</span>
                    </div>
                </div>
            ) : (
                <div
                    className={cn(
                        "relative border-2 border-dashed rounded-lg p-6 transition-all duration-200 cursor-pointer flex flex-col items-center justify-center text-center gap-2",
                        isDragging
                            ? "border-violet-500 bg-violet-500/10"
                            : "border-slate-700 hover:border-violet-500/50 hover:bg-slate-800/50"
                    )}
                    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                >
                    <input
                        type="file"
                        ref={fileInputRef}
                        className="hidden"
                        accept="image/*"
                        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                    />
                    <div className="p-2 rounded-full bg-slate-800 border border-slate-700">
                        <Upload className="w-5 h-5 text-slate-400" />
                    </div>
                    <div className="space-y-1">
                        <p className="text-xs font-medium text-slate-300">
                            Upload Offer Screenshot
                        </p>
                        <p className="text-[10px] text-slate-500">
                            Drag & drop or click to browse
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
