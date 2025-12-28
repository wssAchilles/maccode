import { API_URL, API_KEY } from './analysisService';

export interface TrainingResponse {
    status: string;
    job_id: string;
    console_url: string;
    message: string;
}

export const mlopsService = {
    /**
     * Triggers the Vertex AI training pipeline.
     * Endpoint: POST /api/v1/train
     */
    triggerTraining: async (): Promise<TrainingResponse> => {
        // Keeping legacy endpoint for compatibility if needed, but new panel uses /trigger-retraining primarily
        const endpoint = `${API_URL}/api/v1/trigger-retraining`;

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-KEY": API_KEY
                },
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Training trigger failed: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error("Failed to trigger training:", error);
            throw error;
        }
    },

    /**
     * Gets the status of a training job.
     * Endpoint: GET /api/v1/train/{job_id}
     */
    getJobStatus: async (jobId: string): Promise<{ job_id: string; status: string }> => {
        const encodedJobId = encodeURIComponent(jobId);
        const endpoint = `${API_URL}/api/v1/train/${encodedJobId}`;

        try {
            const response = await fetch(endpoint, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-KEY": API_KEY
                },
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Status check failed: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error("Failed to get job status:", error);
            throw error;
        }
    },

    /**
     * Fetch recent AI Judge audit logs.
     * Endpoint: GET /api/v1/audit-logs
     */
    getAuditLogs: async (limit: number = 10): Promise<any[]> => {
        const endpoint = `${API_URL}/api/v1/audit-logs?limit=${limit}`;
        try {
            const response = await fetch(endpoint, {
                headers: { "X-API-KEY": API_KEY }
            });
            if (!response.ok) throw new Error("Failed to fetch logs");
            return await response.json();
        } catch (error) {
            console.error("Error fetching audit logs:", error);
            return [];
        }
    },

    /**
     * Get model health metrics.
     * Endpoint: GET /api/v1/model-health
     */
    getModelHealth: async (): Promise<any> => {
        const endpoint = `${API_URL}/api/v1/model-health`;
        try {
            const response = await fetch(endpoint, {
                headers: { "X-API-KEY": API_KEY }
            });
            if (!response.ok) throw new Error("Failed to fetch health");
            return await response.json();
        } catch (error) {
            console.error("Error fetching model health:", error);
            return null;
        }
    }
};

