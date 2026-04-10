from __future__ import annotations

from unittest.mock import Mock

import pytest

from services.storage_service import StorageService


class _FakeBucket:
    pass


class _FakeClient:
    def __init__(self, *, project=None, credentials=None):
        self.project = project
        self.credentials = credentials

    def bucket(self, _name):
        return _FakeBucket()


def test_storage_service_uses_adc_when_local_credentials_absent(monkeypatch):
    fake_credentials = object()
    client_spy = Mock(side_effect=lambda **kwargs: _FakeClient(**kwargs))

    monkeypatch.delenv('GCP_SERVICE_ACCOUNT_JSON', raising=False)
    monkeypatch.delenv('GOOGLE_APPLICATION_CREDENTIALS', raising=False)
    monkeypatch.setattr('services.storage_service.google.auth.default', lambda scopes=None: (fake_credentials, 'adc-project'))
    monkeypatch.setattr('services.storage_service.storage.Client', client_spy)

    service = StorageService(bucket_name='demo-bucket')

    assert service.credentials is fake_credentials
    client_spy.assert_called_once_with(project=service.project_id, credentials=fake_credentials)


def test_storage_service_raises_when_no_credentials_are_available(monkeypatch):
    monkeypatch.delenv('GCP_SERVICE_ACCOUNT_JSON', raising=False)
    monkeypatch.delenv('GOOGLE_APPLICATION_CREDENTIALS', raising=False)
    monkeypatch.setattr(
        'services.storage_service.google.auth.default',
        lambda scopes=None: (_ for _ in ()).throw(RuntimeError('adc unavailable')),
    )

    with pytest.raises(EnvironmentError) as exc:
        StorageService(bucket_name='demo-bucket')

    assert 'ADC' in str(exc.value)
