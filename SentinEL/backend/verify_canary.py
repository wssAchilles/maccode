
import sys
import os
import random
from collections import Counter

# Add module path
sys.path.append(os.getcwd())

# Mock aiplatform to avoid actual cloud calls and credentials issues
from unittest.mock import MagicMock
import google.cloud.aiplatform
google.cloud.aiplatform.init = MagicMock()
google.cloud.aiplatform.Endpoint = MagicMock()

# Mock Endpoint.list to return fake endpoints
def mock_endpoint_list(filter=None):
    mock_ep = MagicMock()
    if "sentinel-churn-transformer" in filter:
        mock_ep.resource_name = "projects/.../endpoints/SHADOW_ID"
        mock_ep.display_name = "sentinel-churn-transformer"
    else:
        mock_ep.resource_name = "projects/.../endpoints/PRIMARY_ID"
        mock_ep.display_name = "sentinel-churn-endpoint"
    return [mock_ep]

google.cloud.aiplatform.Endpoint.list = mock_endpoint_list

# Import service (it will load env vars from .env due to pydantic)
from app.services.prediction_service import PredictionService
from app.core.config import settings

def test_distribution():
    print("=== Configuration ===")
    print(f"Shadow Endpoint: {settings.CHURN_ENDPOINT_SHADOW}")
    print(f"Shadow Weight: {settings.CHURN_ENDPOINT_SHADOW_WEIGHT}")
    
    # Initialize service with settings (mirroring get_prediction_service logic)
    service = PredictionService(
        endpoint_name=settings.CHURN_ENDPOINT_PRIMARY,
        shadow_endpoint_name=settings.CHURN_ENDPOINT_SHADOW,
        shadow_weight=settings.CHURN_ENDPOINT_SHADOW_WEIGHT,
        seq_length=settings.CHURN_SEQ_LENGTH
    )
    
    # Pre-fetch properties to trigger lazy loading
    _ = service.endpoint
    _ = service.shadow_endpoint
    
    print("\n=== Endpoints Loaded ===")
    print(f"Primary: {service.endpoint.display_name} ({service.endpoint.resource_name})")
    if service.shadow_endpoint:
        print(f"Shadow:  {service.shadow_endpoint.display_name} ({service.shadow_endpoint.resource_name})")
    else:
        print("Shadow:  None (Not loaded or weight is 0)")

    print("\n=== Running Simulation (1000 requests) ===")
    results = []
    for _ in range(1000):
        ep = service._choose_endpoint()
        results.append(ep.display_name)
    
    counts = Counter(results)
    total = sum(counts.values())
    
    print("Distribution results:")
    for name, count in counts.items():
        print(f"  {name}: {count} ({count/total:.1%})")

    shadow_count = counts.get(settings.CHURN_ENDPOINT_SHADOW, 0)
    shadow_rate = shadow_count / total
    
    print(f"\nObserved Shadow Rate: {shadow_rate:.1%}")
    print(f"Expected Shadow Rate: {settings.CHURN_ENDPOINT_SHADOW_WEIGHT:.1%}")
    
    # Tolerance check (+/- 5%)
    if abs(shadow_rate - settings.CHURN_ENDPOINT_SHADOW_WEIGHT) < 0.05:
        print("\n✅ VERIFICATION PASSED: Traffic distribution is within expected range.")
    else:
        print("\n❌ VERIFICATION FAILED: Traffic distribution deviates significantly.")

if __name__ == "__main__":
    test_distribution()
