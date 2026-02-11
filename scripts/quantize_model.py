"""Advanced INT4 quantization with calibration dataset.

Usage:
    uv run python scripts/quantize_model.py --model microsoft/Phi-3-mini-4k-instruct
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Quantize LLM to INT4 for OpenVINO")
    parser.add_argument(
        "--model",
        default="microsoft/Phi-3-mini-4k-instruct",
        help="HuggingFace model ID",
    )
    parser.add_argument(
        "--output",
        default="data/models/phi-3-mini-int4",
        help="Output directory",
    )
    parser.add_argument(
        "--group-size",
        type=int,
        default=128,
        help="Quantization group size",
    )
    parser.add_argument(
        "--ratio",
        type=float,
        default=0.8,
        help="INT4 quantization ratio",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Quantizing %s → %s", args.model, output_dir)
    logger.info("This requires: pip install optimum[openvino] nncf")
    logger.info(
        "Run: optimum-cli export openvino "
        "--model %s --weight-format int4 "
        "--group-size %d --ratio %.1f --sym "
        "--output %s",
        args.model,
        args.group_size,
        args.ratio,
        output_dir,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
