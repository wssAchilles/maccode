import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("python version:", sys.version)

try:
    import google.cloud.aiplatform
    print(f"google.cloud.aiplatform version: {google.cloud.aiplatform.__version__}")
except ImportError as e:
    print(f"FAILED to import google.cloud.aiplatform: {e}")

try:
    from google.cloud import aiplatform_v1
    print("Successfully imported google.cloud.aiplatform_v1")
    print("aiplatform_v1 dir snippet:", dir(aiplatform_v1)[:20])
    
    if hasattr(aiplatform_v1, "FeatureOnlineStoreServingServiceClient"):
        print("FeatureOnlineStoreServingServiceClient FOUND in aiplatform_v1")
    else:
        print("FeatureOnlineStoreServingServiceClient NOT FOUND in aiplatform_v1")

except ImportError as e:
    print(f"FAILED to import google.cloud.aiplatform_v1: {e}")

try:
    from google.cloud.aiplatform_v1.services.feature_online_store_serving_service import FeatureOnlineStoreServingServiceClient
    print("Successfully imported FeatureOnlineStoreServingServiceClient from services path")
except ImportError as e:
    print(f"FAILED to import FeatureOnlineStoreServingServiceClient from services path: {e}")

print("Debug checks complete.")
