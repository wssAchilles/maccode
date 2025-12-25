import firebase_admin
from firebase_admin import credentials, firestore
import os

# Use default credentials (assumes running in environment with credentials or .config/gcloud)
# Or set GOOGLE_APPLICATION_CREDENTIALS if needed.
# Since we are on a dev machine with gcloud auth, it should work if we initialize with project.

if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        'projectId': 'sentinel-ai-project-482208',
    })

db = firestore.client()

analysis_id = "GTztzUkZ3EY2E5pPEflu"
doc_ref = db.collection("analysis_logs").document(analysis_id)
doc = doc_ref.get()

if doc.exists:
    print(f"Document data: {doc.to_dict()}")
else:
    print("No such document!")
