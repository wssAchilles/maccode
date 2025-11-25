
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os
import json
import sys
from datetime import datetime

def serialize_doc(doc_dict):
    """Helper to serialize Firestore document to JSON"""
    if not doc_dict:
        return None
    
    res = {}
    for k, v in doc_dict.items():
        if hasattr(v, 'isoformat'):
            res[k] = v.isoformat()
        elif hasattr(v, 'seconds'): # Timestamp
            res[k] = datetime.fromtimestamp(v.seconds).isoformat()
        elif isinstance(v, dict):
            res[k] = serialize_doc(v)
        else:
            res[k] = v
    return res

def check_history():
    # Load credentials
    cred_path = os.path.join(os.path.dirname(__file__), 'service-account-key.json')
    if not os.path.exists(cred_path):
        # Try looking in parent directory or environment
        cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not cred_path or not os.path.exists(cred_path):
        print("❌ Credentials not found. Please set GOOGLE_APPLICATION_CREDENTIALS or put service-account-key.json in scripts dir.")
        return

    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = cred_path

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        
        # Use config to connect
        try:
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from config import Config
            db_name = Config.FIRESTORE_DATABASE
            print(f"🔌 Connecting to configured database: {db_name}")
            db = firestore.Client(database=db_name)
            print(f"✅ Connected to '{db_name}'")
        except Exception as e:
            print(f"⚠️ Could not connect to configured database: {e}")
            return
        
        print("🔍 Scanning users for history...")
        users = db.collection('users').stream()
        
        found_history = False
        for user in users:
            print(f"👤 User: {user.id}")
            history_ref = db.collection('users').document(user.id).collection('history')
            history_docs = list(history_ref.stream())
            
            if history_docs:
                found_history = True
                print(f"   Found {len(history_docs)} history records:")
                for doc in history_docs:
                    data = doc.to_dict()
                    print(f"   📄 Doc ID: {doc.id}")
                    print(f"      Keys: {list(data.keys())}")
                    # Print first few keys content to see if it's garbage
                    print(f"      Content (serialized): {json.dumps(serialize_doc(data), indent=2, ensure_ascii=False)}")
            else:
                print("   No history records.")
                
        if not found_history:
            print("❌ No history records found for any user.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    check_history()
