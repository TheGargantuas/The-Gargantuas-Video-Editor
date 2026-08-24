#!/usr/bin/env python3
"""Command-line client for upscaling through a public Gradio/Colab URL."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

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
    parser.add_argument("--input", type=Path, help="Local input image")
    parser.add_argument("--output", type=Path, help="Output image path")
    parser.add_argument(
        "--model",
        default="RealESRGAN_x4plus",
        help="RealESRGAN model to use",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List models exposed by the remote server and exit",
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
    client = RemoteUpscaleClient(args.url, timeout=args.timeout)

    if args.list_models:
        try:
            response = client.list_models()
        except RemoteUpscaleError as exc:
            raise SystemExit(f"Could not list models: {exc}") from exc
        for model in response["models"]:
            default = " (default)" if model.get("default") else ""
            print(
                f"{model['name']}{default} | {model['scale']}x | "
                f"{model['description']}"
            )
        return 0

    if args.input is None or args.output is None:
        raise SystemExit("--input and --output are required unless --list-models is used")
    if not args.input.is_file():
        raise SystemExit(f"Input file not found: {args.input}")

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
