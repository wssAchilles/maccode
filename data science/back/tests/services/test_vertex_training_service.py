from __future__ import annotations

from google.rpc.status_pb2 import Status

from services.vertex_training_service import VertexTrainingService


class _FakeTimestamp:
    def __init__(self, *, seconds: int = 0, nanos: int = 0):
        self.seconds = seconds
        self.nanos = nanos


class _TruthyErrorWithoutProto:
    def __bool__(self):
        return True

    def __str__(self) -> str:
        return ''


class _WrappedProtoError:
    def __init__(self, proto):
        self._pb = proto

    def __bool__(self):
        return True


class _FakeJob:
    def __init__(self, *, error):
        self.name = 'projects/demo/locations/us-central1/customJobs/123'
        self.display_name = 'demo-job'
        self.state = type('State', (), {'name': 'JOB_STATE_PENDING'})()
        self.start_time = _FakeTimestamp(seconds=0, nanos=0)
        self.end_time = _FakeTimestamp(seconds=0, nanos=0)
        self.create_time = _FakeTimestamp(seconds=1712718000, nanos=0)
        self.update_time = _FakeTimestamp(seconds=1712718060, nanos=0)
        self.web_access_uris = {}
        self.error = error


def test_get_job_snapshot_tolerates_truthy_error_without_proto(monkeypatch):
    monkeypatch.setattr(
        VertexTrainingService,
        'get_custom_job',
        classmethod(lambda cls, _job_name: _FakeJob(error=_TruthyErrorWithoutProto())),
    )

    snapshot = VertexTrainingService.get_job_snapshot('projects/demo/locations/us-central1/customJobs/123')

    assert snapshot['state'] == 'JOB_STATE_PENDING'
    assert snapshot['error'] is None


def test_get_job_snapshot_serializes_wrapped_proto_error(monkeypatch):
    error = _WrappedProtoError(Status(code=7, message='permission denied'))
    monkeypatch.setattr(
        VertexTrainingService,
        'get_custom_job',
        classmethod(lambda cls, _job_name: _FakeJob(error=error)),
    )

    snapshot = VertexTrainingService.get_job_snapshot('projects/demo/locations/us-central1/customJobs/123')

    assert snapshot['error'] == {'code': 7, 'message': 'permission denied'}
