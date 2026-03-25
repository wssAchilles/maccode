import pytest

from app.order_client_rpc import resolve_matching_target


def test_resolve_matching_target_https_uses_tls_with_default_443() -> None:
    resolved = resolve_matching_target("https://cerberus-dev-matching-abcde.a.run.app")
    assert resolved.secure is True
    assert resolved.endpoint == "cerberus-dev-matching-abcde.a.run.app:443"


def test_resolve_matching_target_grpcs_keeps_explicit_port() -> None:
    resolved = resolve_matching_target("grpcs://matching.internal:8443")
    assert resolved.secure is True
    assert resolved.endpoint == "matching.internal:8443"


def test_resolve_matching_target_plain_host_is_insecure() -> None:
    resolved = resolve_matching_target("matching:50051")
    assert resolved.secure is False
    assert resolved.endpoint == "matching:50051"


def test_resolve_matching_target_invalid_scheme() -> None:
    with pytest.raises(ValueError):
        resolve_matching_target("ws://matching.service")
