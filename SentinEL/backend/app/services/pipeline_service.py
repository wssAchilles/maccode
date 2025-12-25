import os
from google.cloud import aiplatform
from app.core.telemetry import get_tracer
from app.core.config import settings

tracer = get_tracer()

class PipelineService:
    def __init__(self):
        self.project_id = settings.PROJECT_ID
        self.location = settings.LOCATION
        self.pipeline_root = f"gs://{settings.PIPELINE_ROOT_BUCKET}"
        
        # Initialize Vertex AI SDK
        aiplatform.init(
            project=self.project_id,
            location=self.location,
            staging_bucket=self.pipeline_root
        )

    def submit_training_job(self) -> tuple[str, str]:
        """
        Submits a Vertex AI Pipeline job for training.
        Returns:
            tuple[str, str]: (job_id, dashboard_url)
        """
        with tracer.start_as_current_span("Pipeline: Submit Training Job") as span:
            try:
                # Path to the compiled pipeline JSON
                # Assuming the JSON is packaged in the specific location or we look for it relative to app
                # For Docker deployment, it's safer to use an absolute path or relative to known root
                template_path = "sentinel_pipeline.json" 
                
                # Verify if file exists (Optional but good for debugging)
                if not os.path.exists(template_path):
                    # Fallback check - maybe it's in mlops folder if running locally
                    alt_path = "backend/mlops/sentinel_pipeline.json"
                    if os.path.exists(alt_path):
                         template_path = alt_path
                    else:
                        print(f"Warning: Pipeline template not found at {template_path}")

                span.set_attribute("pipeline.template_path", template_path)
                
                # Define parameter values (passed to pipeline input arguments)
                parameter_values = {
                    "project_id": self.project_id,
                    "location": self.location,
                    # Add other parameters if your pipeline definition requires them
                }

                job = aiplatform.PipelineJob(
                    display_name="sentinel-retraining-pipeline",
                    template_path=template_path,
                    pipeline_root=self.pipeline_root,
                    parameter_values=parameter_values,
                    enable_caching=False # Force execution for now
                )

                job.submit()
                
                dashboard_url = job._dashboard_uri()
                span.set_attribute("pipeline.dashboard_url", dashboard_url)
                span.set_attribute("pipeline.job_id", job.name)
                
                print(f"Pipeline submitted. Dashboard: {dashboard_url}")
                return job.name, dashboard_url


            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                print(f"Error submitting pipeline: {e}")
                raise e

    def get_job_status(self, job_id: str) -> str:
        """
        Retrieves the status of a pipeline job.
        Args:
            job_id (str): The resource name of the pipeline job.
        Returns:
            str: The state of the job (e.g., PIPELINE_STATE_RUNNING, PIPELINE_STATE_SUCCEEDED, PIPELINE_STATE_FAILED).
        """
        try:
            # Retrieve the job using the resource name (job_id from submit response)
            job = aiplatform.PipelineJob.get(resource_name=job_id)
            return job.state.name
        except Exception as e:
            print(f"Error getting job status for {job_id}: {e}")
            return "UNKNOWN"
