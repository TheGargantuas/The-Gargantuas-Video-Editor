"""Utilities and HTTP client for the public Gradio upscaling API."""

from __future__ import annotations

import base64
import io
import json
import mimetypes
from pathlib import Path
from typing import Any

import numpy as np
import requests
from PIL import Image


UPSCALE_API_NAME = "upscale_image"
MODELS_API_NAME = "upscale_models"
VIDEO_CHUNK_API_NAME = "upscale_video_chunk"
DEFAULT_TIMEOUT_SECONDS = 900


class RemoteUpscaleError(RuntimeError):
    """Raised when a remote upscaling request cannot be completed."""


def _normalized_image_format(image_format: str | None) -> str:
    normalized = (image_format or "PNG").upper()
    return "JPEG" if normalized == "JPG" else normalized


def image_to_data_url(
    image: str | Path | bytes | Image.Image | np.ndarray,
    *,
    input_is_bgr: bool = False,
    image_format: str = "PNG",
) -> str:
    """Encode a path, image, bytes, or NumPy frame as an image data URL."""
    if isinstance(image, (str, Path)):
        image_path = Path(image)
        image_bytes = image_path.read_bytes()
        mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    elif isinstance(image, bytes):
        image_bytes = image
        try:
            with Image.open(io.BytesIO(image_bytes)) as opened:
                detected_format = _normalized_image_format(opened.format)
            mime_type = Image.MIME.get(detected_format, "application/octet-stream")
        except Exception as exc:
            raise ValueError("The supplied bytes are not a valid image") from exc
    else:
        if isinstance(image, np.ndarray):
            array = image
            if array.ndim not in (2, 3):
                raise ValueError("A frame must have 2 or 3 dimensions")
            if array.dtype != np.uint8:
                array = np.clip(array, 0, 255).astype(np.uint8)
            if input_is_bgr and array.ndim == 3 and array.shape[2] >= 3:
                array = array[..., :3][..., ::-1]
            pil_image = Image.fromarray(array)
        elif isinstance(image, Image.Image):
            pil_image = image
        else:
            raise TypeError(f"Unsupported image type: {type(image).__name__}")

        normalized_format = _normalized_image_format(image_format)
        if normalized_format == "JPEG" and pil_image.mode not in ("RGB", "L"):
            pil_image = pil_image.convert("RGB")
        buffer = io.BytesIO()
        pil_image.save(buffer, format=normalized_format)
        image_bytes = buffer.getvalue()
        mime_type = Image.MIME.get(normalized_format, f"image/{normalized_format.lower()}")

    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def decode_image_data_url(payload: str, *, max_bytes: int) -> tuple[Image.Image, str]:
    """Decode a raw base64 string or image data URL into an RGB PIL image."""
    if not isinstance(payload, str) or not payload.strip():
        raise ValueError("The image payload is empty")

    encoded = payload.strip()
    if encoded.startswith("data:"):
        try:
            header, encoded = encoded.split(",", 1)
        except ValueError as exc:
            raise ValueError("Invalid image data URL") from exc
        if ";base64" not in header.lower():
            raise ValueError("The image data URL must use base64 encoding")

    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("The image payload is not valid base64") from exc

    if len(image_bytes) > max_bytes:
        max_megabytes = max_bytes / (1024 * 1024)
        raise ValueError(f"The input image exceeds the {max_megabytes:g} MB limit")

    try:
        with Image.open(io.BytesIO(image_bytes)) as opened:
            input_format = (opened.format or "PNG").lower()
            opened.load()
            image = opened.convert("RGB")
    except Exception as exc:
        raise ValueError("The decoded payload is not a supported image") from exc

    return image, "jpg" if input_format == "jpeg" else input_format


def image_file_to_data_url(image_path: str | Path) -> str:
    """Encode a generated image file as a data URL."""
    return image_to_data_url(Path(image_path))


def data_url_to_image(payload: str) -> Image.Image:
    """Decode a response data URL without applying the server upload limit."""
    image, _ = decode_image_data_url(payload, max_bytes=1024 * 1024 * 1024)
    return image


def decode_video_data_url(payload: str, *, max_bytes: int) -> bytes:
    """Decode a base64 MP4 payload and reject malformed or oversized input."""
    if not isinstance(payload, str) or not payload.strip():
        raise ValueError("The video payload is empty")
    encoded = payload.strip()
    if encoded.startswith("data:"):
        try:
            header, encoded = encoded.split(",", 1)
        except ValueError as exc:
            raise ValueError("Invalid video data URL") from exc
        if ";base64" not in header.lower() or not header.lower().startswith("data:video/"):
            raise ValueError("The video data URL must contain a base64 video")
    try:
        video_bytes = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("The video payload is not valid base64") from exc
    if not video_bytes or len(video_bytes) > max_bytes:
        limit = max_bytes / (1024 * 1024)
        raise ValueError(f"The input video is empty or exceeds the {limit:g} MB limit")
    if len(video_bytes) < 12 or video_bytes[4:8] != b"ftyp":
        raise ValueError("The decoded payload is not an MP4 video")
    return video_bytes


def video_file_to_data_url(video_path: str | Path, *, max_bytes: int) -> str:
    """Encode a generated MP4 as a bounded video data URL."""
    path = Path(video_path)
    video_bytes = path.read_bytes()
    if not video_bytes or len(video_bytes) > max_bytes:
        limit = max_bytes / (1024 * 1024)
        raise ValueError(f"The output video is empty or exceeds the {limit:g} MB limit")
    if len(video_bytes) < 12 or video_bytes[4:8] != b"ftyp":
        raise ValueError("The generated output is not an MP4 video")
    return "data:video/mp4;base64," + base64.b64encode(video_bytes).decode("ascii")


class RemoteUpscaleClient:
    """Small REST client for a remote Gradio ``upscale_image`` endpoint."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        session: requests.Session | None = None,
    ) -> None:
        if not base_url or not base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.last_response: dict[str, Any] | None = None

    def request(
        self,
        image: str | Path | bytes | Image.Image | np.ndarray,
        model: str,
        *,
        input_is_bgr: bool = False,
    ) -> dict[str, Any]:
        """Send an image or frame and return the complete API response."""
        image_payload = image_to_data_url(image, input_is_bgr=input_is_bgr)
        result = self._call_endpoint(UPSCALE_API_NAME, [image_payload, model])
        if not result.get("ok"):
            raise RemoteUpscaleError(result.get("error", "Remote upscaling failed"))
        if not isinstance(result.get("image"), str):
            raise RemoteUpscaleError("The server response does not contain an image")
        self.last_response = result
        return result

    def list_models(self) -> dict[str, Any]:
        """Return model names, scales, descriptions, and the default model."""
        result = self._call_direct_endpoint(MODELS_API_NAME, [])
        if result is None:
            result = self._call_endpoint(MODELS_API_NAME, [])
        if not result.get("ok"):
            raise RemoteUpscaleError(result.get("error", "Could not list remote models"))
        if not isinstance(result.get("models"), list):
            raise RemoteUpscaleError("The server response does not contain a model list")
        return result

    def upscale_image(
        self,
        image: str | Path | bytes | Image.Image | np.ndarray,
        model: str,
    ) -> Image.Image:
        """Upscale an image and return it as a PIL image."""
        result = self.request(image, model)
        return data_url_to_image(result["image"])

    def upscale_frame(self, frame: np.ndarray, model: str) -> np.ndarray:
        """Upscale an OpenCV BGR frame and return an OpenCV BGR frame."""
        result = self.request(frame, model, input_is_bgr=True)
        rgb = np.asarray(data_url_to_image(result["image"]))
        return rgb[..., ::-1].copy()

    def upscale_to_file(
        self,
        image: str | Path | bytes | Image.Image | np.ndarray,
        model: str,
        output_path: str | Path,
    ) -> Path:
        """Upscale an image and save the result to ``output_path``."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        result_image = self.upscale_image(image, model)
        save_format = _normalized_image_format(output.suffix.lstrip(".") or "PNG")
        if save_format == "JPEG" and result_image.mode not in ("RGB", "L"):
            result_image = result_image.convert("RGB")
        result_image.save(output, format=save_format)
        return output

    def _call_direct_endpoint(
        self,
        api_name: str,
        inputs: list[Any],
    ) -> dict[str, Any] | None:
        """Call a synchronous Gradio endpoint, returning None when unavailable."""
        for route_prefix in ("/gradio_api/api", "/api"):
            try:
                response = self.session.post(
                    f"{self.base_url}{route_prefix}/{api_name}",
                    json={"data": inputs},
                    timeout=30,
                )
            except requests.RequestException as exc:
                raise RemoteUpscaleError(
                    f"Could not call the Gradio API: {exc}"
                ) from exc
            if response.status_code in (404, 405):
                continue
            try:
                response.raise_for_status()
            except requests.RequestException as exc:
                raise RemoteUpscaleError(
                    f"Could not call the Gradio API: {exc}"
                ) from exc
            outputs = response.json().get("data")
            if not isinstance(outputs, list) or not outputs:
                raise RemoteUpscaleError("Gradio returned an empty result")
            result = outputs[0]
            if not isinstance(result, dict):
                raise RemoteUpscaleError("Unexpected response format from Gradio")
            return result
        return None

    def _call_endpoint(self, api_name: str, inputs: list[Any]) -> dict[str, Any]:
        route_prefixes = ("/gradio_api/call", "/call")
        last_error: Exception | None = None

        for route_prefix in route_prefixes:
            endpoint_url = f"{self.base_url}{route_prefix}/{api_name}"
            try:
                response = self.session.post(
                    endpoint_url,
                    json={"data": inputs},
                    timeout=30,
                )
                if response.status_code in (404, 405):
                    continue
                response.raise_for_status()
                event_id = response.json().get("event_id")
                if not event_id:
                    raise RemoteUpscaleError("Gradio did not return an event_id")
                return self._wait_for_result(endpoint_url, event_id)
            except RemoteUpscaleError:
                raise
            except requests.RequestException as exc:
                last_error = exc

        if last_error:
            raise RemoteUpscaleError(f"Could not call the Gradio API: {last_error}") from last_error
        raise RemoteUpscaleError(
            f"Endpoint '{api_name}' not found. Make sure Colab is running the updated app."
        )

    def _wait_for_result(self, endpoint_url: str, event_id: str) -> dict[str, Any]:
        response = self.session.get(
            f"{endpoint_url}/{event_id}",
            stream=True,
            timeout=(10, self.timeout),
        )
        response.raise_for_status()

        current_event = ""
        data_lines: list[str] = []

        def consume_event() -> dict[str, Any] | None:
            nonlocal current_event, data_lines
            event = current_event
            data = "\n".join(data_lines)
            current_event = ""
            data_lines = []
            if event == "error":
                raise RemoteUpscaleError(self._format_remote_error(data))
            if event != "complete":
                return None
            try:
                outputs = json.loads(data)
            except json.JSONDecodeError as exc:
                raise RemoteUpscaleError("Gradio returned invalid JSON") from exc
            if not isinstance(outputs, list) or not outputs:
                raise RemoteUpscaleError("Gradio returned an empty result")
            result = outputs[0]
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    pass
            if not isinstance(result, dict):
                raise RemoteUpscaleError("Unexpected response format from Gradio")
            return result

        for raw_line in response.iter_lines(decode_unicode=True):
            line = raw_line if isinstance(raw_line, str) else raw_line.decode("utf-8")
            if not line:
                completed = consume_event()
                if completed is not None:
                    return completed
            elif line.startswith("event:"):
                current_event = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())

        completed = consume_event()
        if completed is not None:
            return completed
        raise RemoteUpscaleError("The Gradio event stream ended before completion")

    @staticmethod
    def _format_remote_error(data: str) -> str:
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            return data or "Remote Gradio processing failed"
        if isinstance(parsed, dict):
            return str(parsed.get("error") or parsed.get("detail") or parsed)
        return str(parsed)
