from __future__ import annotations

from pathlib import Path


BACK_ROOT = Path(__file__).resolve().parents[1]


def test_vertex_training_dockerfile_uses_training_specific_requirements():
    dockerfile = (BACK_ROOT / 'Dockerfile.vertex_training').read_text(encoding='utf-8')
    base_dockerfile = (BACK_ROOT / 'Dockerfile.vertex_training.base').read_text(encoding='utf-8')
    requirements = (BACK_ROOT / 'requirements.vertex_training.txt').read_text(encoding='utf-8')

    assert 'ARG BASE_IMAGE=' in dockerfile
    assert 'FROM ${BASE_IMAGE}' in dockerfile
    assert 'COPY --chown=appuser:appuser . .' in dockerfile
    assert 'requirements.vertex_training.txt' not in dockerfile
    assert 'pip install --no-cache-dir -r requirements.vertex_training.txt' not in dockerfile
    assert 'pip install --no-cache-dir -r requirements.txt' not in dockerfile

    assert 'requirements.vertex_training.txt' in base_dockerfile
    assert 'pip install --no-cache-dir -r requirements.vertex_training.txt' in base_dockerfile
    assert 'DEBIAN_FRONTEND=noninteractive apt-get' in base_dockerfile
    assert 'tf-keras' not in requirements


def test_vertex_training_cloudbuild_reuses_cached_image_layers():
    cloudbuild = (BACK_ROOT / 'cloudbuild.vertex_training.yaml').read_text(encoding='utf-8')
    base_cloudbuild = (BACK_ROOT / 'cloudbuild.vertex_training_base.yaml').read_text(encoding='utf-8')
    deploy_script = (BACK_ROOT.parent / 'scripts' / 'deploy_vertex_training.sh').read_text(encoding='utf-8')

    assert 'docker pull "$_IMAGE_URI" || true' in cloudbuild
    assert 'docker pull "$_BASE_IMAGE_URI" || true' in cloudbuild
    assert '--cache-from' in cloudbuild
    assert 'BASE_IMAGE=$_BASE_IMAGE_URI' in cloudbuild
    assert 'Dockerfile.vertex_training.base' in base_cloudbuild
    assert 'REQUIREMENTS_HASH' in deploy_script
    assert 'artifacts docker images describe "$BASE_IMAGE_URI"' in deploy_script
