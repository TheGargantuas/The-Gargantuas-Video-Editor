#!/usr/bin/env python3
"""Command-line client for upscaling through a public Gradio/Colab URL."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from config.config import MODELS
from utils.remote_upscale import RemoteUpscaleClient, RemoteUpscaleError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a local image to the Video Editor running on Colab."
    )
    parser.add_argument(
        "--url",
        default=os.getenv("GRADIO_URL"),
        help="Public Gradio URL (or set GRADIO_URL)",
    )
    parser.add_argument("--input", required=True, type=Path, help="Local input image")
    parser.add_argument("--output", required=True, type=Path, help="Output image path")
    parser.add_argument(
        "--model",
        default="RealESRGAN_x4plus",
        choices=list(MODELS.keys()),
        help="RealESRGAN model to use",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("UPSCALE_API_TOKEN"),
        help="Optional token configured on Colab (or set UPSCALE_API_TOKEN)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Maximum seconds to wait for the upscaling result",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.url:
        raise SystemExit("Missing --url (or GRADIO_URL)")
    if not args.input.is_file():
        raise SystemExit(f"Input file not found: {args.input}")

    client = RemoteUpscaleClient(args.url, token=args.token, timeout=args.timeout)
    try:
        output_path = client.upscale_to_file(args.input, args.model, args.output)
    except (RemoteUpscaleError, OSError, ValueError) as exc:
        raise SystemExit(f"Upscaling failed: {exc}") from exc

    response = client.last_response or {}
    print(f"Upscaled image saved to: {output_path}")
    print(
        f"Model: {response.get('model', args.model)} | "
        f"Device: {response.get('device', 'remote')} | "
        f"Scale: {response.get('scale', '?')}x"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
