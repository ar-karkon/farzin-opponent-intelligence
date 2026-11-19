"""Generate private Kaggle script metadata; no credentials are stored here."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def build_metadata(username: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", username):
        raise ValueError("Kaggle username must contain only letters, numbers, _ or -")
    return {
        "id": f"{username}/foi-v1-gpu-smoke",
        "title": "FOI v1 GPU Smoke",
        "code_file": "foi_kaggle_smoke.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "machine_shape": "NvidiaTeslaT4",
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True, help="Your public Kaggle username/slug, NOT an API key")
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / "kaggle" / "kernel-metadata.json"
    path.write_text(json.dumps(build_metadata(args.username), indent=2) + "\n")
    print(f"Configured private kernel metadata: {path}")
    print(f"Kernel ref: {args.username}/foi-v1-gpu-smoke")


if __name__ == "__main__":
    main()
