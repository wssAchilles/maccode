
import pytest
import sys
import os
import io
import json
from unittest.mock import MagicMock, patch

# Add back directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import create_app
from services.firebase_service import FirebaseService

@pytest.fixture
def app():
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/Users/achilles/Documents/code/data science/service-account-key.json"
    app = create_app('testing')
    app.config.update({
        "TESTING": True,
    })
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def mock_auth():
    with patch('services.firebase_service.FirebaseService.verify_token') as mock:
        mock.return_value = {'uid': 'test_user', 'email': 'test@example.com'}
        yield mock

@pytest.fixture
def auth_headers():
    return {'Authorization': 'Bearer test_token'}

# Test RAG Endpoint
def test_rag_status(client, mock_auth, auth_headers):
    # Mock RAGService
    with patch('api.rag.RAGService') as MockService:
        instance = MockService.return_value
        instance.is_available.return_value = True
        instance.get_stats.return_value = {'count': 10}
        
        response = client.get('/api/rag/status', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['stats']['count'] == 10

def test_rag_ingest(client, mock_auth, auth_headers):
    with patch('api.rag.RAGService') as MockService:
        instance = MockService.return_value
        instance.is_available.return_value = True
        instance.load_documents.return_value = 5
        
        with patch('api.rag.StorageService') as MockStorage: # Correct path
            storage = MockStorage.return_value
            storage.download_file.return_value = b"sample text"
            storage.list_files.return_value = ['doc1.txt']
            
            response = client.post('/api/rag/ingest', json={
                'storage_path': 'docs/doc1.txt'
            }, headers=auth_headers)
            assert response.status_code == 200
            assert response.get_json()['count'] == 5

# Test ML Explain Endpoint
def test_ml_explain(client, mock_auth, auth_headers):
    with patch('api.ml.MLService') as MockMLService, \
         patch('api.ml.StorageService') as MockStorage, \
         patch('api.ml.ExplainabilityService') as MockExplainService:
         
        pipeline = MagicMock()
        pipeline.named_steps = {'model': MagicMock()}
        MockMLService.load_model.return_value = pipeline
        
        MockStorage.return_value.download_file.return_value = b"col1,col2\n1,2\n3,4"
        MockStorage.return_value.bucket.blob.return_value.upload_from_string.return_value = None
        
        MockExplainService.return_value.calculate_shap_values.return_value = ([], 0, [])
        MockExplainService.return_value.plot_summary.return_value = b"iVBORw0KGgo=" # base64 image data
        
        response = client.post('/api/ml/explain', json={
            'model_path': 'models/model.joblib',
            'storage_path': 'data.csv'
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()['success'] is True

# Test DL Endpoint
def test_dl_train(client, mock_auth, auth_headers):
    with patch('api.ml.DeepLearningService') as MockDL, \
         patch('api.ml.StorageService') as MockStorage:
         
        MockDL.return_value.is_available.return_value = True
        mock_model = MagicMock()
        mock_history = MagicMock()
        mock_history.history = {'loss': [0.1]}
        # Ensure model.save works
        mock_model.save = MagicMock()
        
        MockDL.return_value.train_model.return_value = {
            'model': mock_model,
            'history': mock_history,
            'metrics': {'mae': 0.1}
        }
        
        MockStorage.return_value.download_file.return_value = b"Date,y\n2023-01-01,100"
        
        response = client.post('/api/ml/deep/train', json={
            'storage_path': 'data.csv',
            'target_column': 'y'
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()['metrics']['mae'] == 0.1

# Test Drift Endpoint
def test_drift_detect(client, mock_auth, auth_headers):
    with patch('api.analysis.DriftService') as MockDrift, \
         patch('api.analysis.StorageService') as MockStorage:
         
        MockStorage.return_value.download_file.return_value = b"col1\n1"
        MockDrift.return_value.detect_drift.return_value = {'col1': {'drift_detected': False}}
        MockDrift.return_value.generate_drift_report.return_value = "# Report"
        
        response = client.post('/api/analysis/drift/detect', json={
            'reference_path': 'ref.csv',
            'current_path': 'cur.csv',
            'features': ['col1']
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()['success'] is True

# Test Optimization Sensitivity
def test_optimization_sensitivity(client, mock_auth, auth_headers):
    with patch('api.optimization.EnergyPredictor') as MockPredictor, \
         patch('api.optimization.EnergyOptimizer') as MockOptimizer: # Wait, EnergyOptimizer is imported in the file
        
        # NOTE: Since EnergyOptimizer is imported at the top level of api/optimization.py, 
        # patching it might be tricky if it's already bound.
        # But `_load_service_class` is used.
        # Let's mock the class methods directly if possible or the return of `_load_service_class` 
        # But `optimization.py` uses `EnergyOptimizer = ...`
        
        # We can patch `api.optimization.EnergyOptimizer`
        
        MockPredictor.return_value.predict_next_24h.return_value = [{'predicted_load': 100, 'price': 0.5}] * 24
        
        # Mock instance of EnergyOptimizer
        mock_opt_instance = MagicMock()
        mock_opt_instance.simulate_scenarios.return_value = [{'params': {}, 'savings': 10}]
        
        # When api.optimization.EnergyOptimizer() is called, return our mock instance
        with patch('api.optimization.EnergyOptimizer', return_value=mock_opt_instance):
             response = client.post('/api/optimization/sensitivity', json={
                'target_date': '2024-01-01'
             }, headers=auth_headers)
             assert response.status_code == 200
             assert len(response.get_json()['results']) == 1

