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
        const endpoint = `${API_URL}/api/v1/train`;

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
        // The job_id might contain slashes (resource name), so we should encode it
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
    }
};
