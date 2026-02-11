from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger("adapters.openvino.loader")


def verify_model_checksum(model_dir: Path, expected_sha256: str | None = None) -> bool:
    """Verify model integrity via SHA-256 checksum."""
    bin_path = model_dir / "openvino_model.bin"
    if not bin_path.exists():
        logger.error("Model file not found: %s", bin_path)
        return False

    if expected_sha256 is None:
        return True

    sha = hashlib.sha256()
    with open(bin_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)

    actual = sha.hexdigest()
    if actual != expected_sha256:
        logger.error(
            "Checksum mismatch: expected %s, got %s",
            expected_sha256,
            actual,
        )
        return False

    return True


def list_available_models(models_dir: Path) -> list[dict[str, str]]:
    """List all available quantized models."""
    models: list[dict[str, str]] = []
    if not models_dir.exists():
        return models

    for model_dir in sorted(models_dir.iterdir()):
        if model_dir.is_dir() and (model_dir / "openvino_model.xml").exists():
            models.append(
                {
                    "name": model_dir.name,
                    "path": str(model_dir),
                    "has_tokenizer": (model_dir / "tokenizer.json").exists().__str__(),
                }
            )

    return models
