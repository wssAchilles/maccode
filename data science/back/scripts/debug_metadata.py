import sys
import os
from pathlib import Path
import json

# Add back directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.storage_service import StorageService

def inspect_metadata():
    print("🔍 Inspecting Model Metadata from Firebase...")
    try:
        storage = StorageService()
        metadata_bytes = storage.download_file('models/model_metadata.json')
        metadata = json.loads(metadata_bytes.decode('utf-8'))
        
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        
        metrics = metadata.get('metrics', {})
        print("\n📊 Key Metrics:")
        print(f"   R2 Score: {metrics.get('r2Score')}")
        print(f"   MAE: {metrics.get('mae')}")
        
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    inspect_metadata()
