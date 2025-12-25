"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { mlopsService } from '@/services/mlopsService';

export const ModelTrainingCard = () => {
    const [isLoading, setIsLoading] = useState(false);
    const [trainingInfo, setTrainingInfo] = useState<{ jobId: string, url: string } | null>(null);
    const [pipelineStatus, setPipelineStatus] = useState<string>("Pending");
    const [error, setError] = useState<string | null>(null);

    // Polling effect
    React.useEffect(() => {
        let intervalId: NodeJS.Timeout;

        if (trainingInfo?.jobId) {
            const pollStatus = async () => {
                try {
                    const data = await mlopsService.getJobStatus(trainingInfo.jobId);
                    setPipelineStatus(data.status);

                    // Stop polling if finished
                    if (['PIPELINE_STATE_SUCCEEDED', 'PIPELINE_STATE_FAILED', 'PIPELINE_STATE_CANCELLED'].includes(data.status)) {
                        clearInterval(intervalId);
                    }
                } catch (err) {
                    console.error("Polling error:", err);
                }
            };

            // Initial check
            pollStatus();
            // Poll every 10 seconds
            intervalId = setInterval(pollStatus, 10000);
        }

        return () => {
            if (intervalId) clearInterval(intervalId);
        };
    }, [trainingInfo?.jobId]);

    const handleStartTraining = async () => {
        setIsLoading(true);
        setError(null);
        setPipelineStatus("Initializing");
        try {
            const response = await mlopsService.triggerTraining();
            setTrainingInfo({
                jobId: response.job_id,
                url: response.console_url
            });
        } catch (err: any) {
            setError(err.message || "Failed to start training");
            setPipelineStatus("Failed");
        } finally {
            setIsLoading(false);
        }
    };

    const getStatusColor = (status: string) => {
        if (status === 'PIPELINE_STATE_SUCCEEDED' || status === 'PIPELINE_STATE_RUNNING') return 'text-green-400 border-green-500/50 bg-green-500';
        if (status === 'PIPELINE_STATE_FAILED' || status === 'PIPELINE_STATE_CANCELLED') return 'text-red-400 border-red-500/50 bg-red-500';
        return 'text-indigo-400 border-indigo-500/50 bg-indigo-500';
    };

    const getStatusText = (status: string) => {
        switch (status) {
            case 'PIPELINE_STATE_RUNNING': return 'Running (Data Export/Training)';
            case 'PIPELINE_STATE_SUCCEEDED': return 'Training Complete Successfully';
            case 'PIPELINE_STATE_FAILED': return 'Training Failed (See Console)';
            case 'PIPELINE_STATE_CANCELLED': return 'Training Cancelled';
            case 'PIPELINE_STATE_PENDING': return 'Pending Resources...';
            case 'Initializing': return 'Initializing Pipeline...';
            default: return status.replace('PIPELINE_STATE_', '');
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 relative overflow-hidden group"
        >
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-indigo-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

            <div className="relative z-10">
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <h3 className="text-lg font-semibold text-white mb-1">Continuous Learning Pipeline</h3>
                        <p className="text-sm text-gray-400">Automated model retraining & evaluation</p>
                    </div>
                    <div className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-xs font-medium border border-green-500/20">
                        Active
                    </div>
                </div>

                <div className="bg-white/5 rounded-xl p-4 mb-6 border border-white/5">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-400">Current Model</span>
                        <span className="text-xs text-indigo-400 font-mono">v2.4.0</span>
                    </div>
                    <div className="flex items-center gap-2 text-white font-medium">
                        <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                        Gemini 1.5 Pro (v002)
                    </div>
                </div>

                <AnimatePresence mode="wait">
                    {trainingInfo ? (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="bg-green-500/10 border border-green-500/20 rounded-xl p-4 mb-4"
                        >
                            <p className={`text-sm mb-3 flex items-center gap-2 ${getStatusColor(pipelineStatus).split(' ')[0]}`}>
                                <span className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${getStatusColor(pipelineStatus).split(' ')[1]}`}>
                                    <span className={`w-2 h-2 rounded-full ${getStatusColor(pipelineStatus).split(' ')[2]} ${pipelineStatus === 'PIPELINE_STATE_RUNNING' ? 'animate-pulse' : ''}`} />
                                </span>
                                {getStatusText(pipelineStatus)}
                            </p>
                            <a
                                href={trainingInfo.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block w-full py-2 px-4 bg-green-500/20 hover:bg-green-500/30 text-green-300 text-center rounded-lg text-sm transition-colors border border-green-500/20"
                            >
                                View in Vertex AI Console →
                            </a>
                        </motion.div>
                    ) : (
                        <button
                            onClick={handleStartTraining}
                            disabled={isLoading}
                            className="w-full py-3 px-4 bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white rounded-xl font-medium shadow-lg shadow-indigo-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 group/btn"
                        >
                            {isLoading ? (
                                <>
                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    <span>Initiating Pipeline...</span>
                                </>
                            ) : (
                                <>
                                    <span className="text-lg">🧬</span>
                                    <span>Evolve Model (Start Tuning)</span>
                                </>
                            )}
                        </button>
                    )}
                </AnimatePresence>

                {error && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="mt-3 text-red-400 text-sm bg-red-500/10 p-3 rounded-lg border border-red-500/20"
                    >
                        {error}
                    </motion.div>
                )}
            </div>
        </motion.div>
    );
};
