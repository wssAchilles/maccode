import os
import sys
from unittest.mock import patch

import pytest

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import create_app


@pytest.fixture
def app():
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = (
        "/Users/achilles/Documents/code/data science/service-account-key.json"
    )
    app = create_app('testing')
    app.config.update({"TESTING": True})
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


def test_rag_ingest_uses_requested_collection_name(client, mock_auth, auth_headers):
    with patch('api.rag.RAGService') as mock_service_class:
        instance = mock_service_class.return_value
        instance.is_available.return_value = {'available': True}
        instance.load_documents.return_value = ['doc-a']
        instance.create_embeddings.return_value = 1
        instance.get_stats.return_value = {'document_count': 1, 'backend': 'tfidf_fallback'}

        with patch('api.rag.StorageService') as mock_storage_class:
            storage = mock_storage_class.return_value
            storage.download_file.return_value = b'sample text'

            response = client.post(
                '/api/rag/ingest',
                json={
                    'storage_path': 'docs/doc1.txt',
                    'collection_name': 'ops-knowledge',
                },
                headers=auth_headers,
            )

    assert response.status_code == 200
    assert response.get_json()['collection'] == 'ops-knowledge'
    assert mock_service_class.call_args.kwargs['collection_name'] == 'ops-knowledge'


def test_rag_query_uses_requested_collection_name(client, mock_auth, auth_headers):
    with patch('api.rag.RAGService') as mock_service_class:
        instance = mock_service_class.return_value
        instance.is_available.return_value = {'available': True}
        instance.answer_question.return_value = {
            'success': True,
            'answer': '来自 ops-knowledge 的回答',
            'context': [],
        }

        response = client.post(
            '/api/rag/ask',
            json={
                'query': '你是谁',
                'collection_name': 'ops-knowledge',
            },
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['collection'] == 'ops-knowledge'
    assert mock_service_class.call_args.kwargs['collection_name'] == 'ops-knowledge'
    instance.answer_question.assert_called_once_with('你是谁', top_k=3)
