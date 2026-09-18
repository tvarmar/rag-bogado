"""Deterministic tests verifying Docker and Compose configuration files."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_dockerfile_structure():
    dockerfile_path = REPO_ROOT / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile must exist at repository root"
    content = dockerfile_path.read_text(encoding="utf-8")

    # Multi-stage validation
    assert "FROM python:3.12" in content
    assert "AS builder" in content
    assert "AS runner" in content

    # uv installation and lockfile usage
    assert "ghcr.io/astral-sh/uv" in content
    assert "uv sync --frozen" in content
    assert "pyproject.toml" in content
    assert "uv.lock" in content

    # Security and runtime configurations
    assert "useradd" in content
    assert "USER appuser" in content
    assert "EXPOSE 8000" in content
    assert "uvicorn" in content
    assert "rag_bogado.api.app:app" in content
    assert "HEALTHCHECK" in content


def test_dockerignore_coverage():
    dockerignore_path = REPO_ROOT / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore must exist at repository root"
    ignored_patterns = {
        line.strip()
        for line in dockerignore_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }

    essential_patterns = {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
    }
    missing = essential_patterns - ignored_patterns
    assert not missing, f"Missing essential patterns in .dockerignore: {missing}"


def test_docker_compose_specification():
    compose_path = REPO_ROOT / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist at repository root"

    with compose_path.open("r", encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    assert "services" in compose_data
    services = compose_data["services"]

    # Validate API service
    assert "rag-bogado-api" in services
    api_service = services["rag-bogado-api"]
    assert "8000:8000" in api_service.get("ports", [])
    assert api_service.get("build", {}).get("dockerfile") == "Dockerfile"
    assert "qdrant" in api_service.get("depends_on", {})

    # Validate environment variables for inter-service communication
    env_vars = api_service.get("environment", [])
    env_dict = dict(item.split("=", 1) for item in env_vars if "=" in item)
    assert env_dict.get("QDRANT_URL") == "http://qdrant:6333"
    assert env_dict.get("CATALOG_PATH") == "/app/data/catalog/catalog.sqlite3"
    assert "OLLAMA_BASE_URL" in env_dict

    # Validate Qdrant service
    assert "qdrant" in services
    qdrant_service = services["qdrant"]
    assert "qdrant/qdrant" in qdrant_service.get("image", "")
    assert "6333:6333" in qdrant_service.get("ports", [])
    assert "healthcheck" in qdrant_service

    # Validate persistent volumes
    api_vols = api_service.get("volumes", [])
    qdrant_vols = qdrant_service.get("volumes", [])
    assert any("/app/data/catalog" in vol for vol in api_vols)
    assert any("/qdrant/storage" in vol for vol in qdrant_vols)
