"""Tests for the remote Colab/Gradio upscaling API."""

from __future__ import annotations

import json
from unittest.mock import Mock

import numpy as np
import requests
from PIL import Image

from config.config import MODELS
from tabs.upscaler_tab import UpscalerTab
from utils.remote_upscale import (
    RemoteUpscaleClient,
    RemoteUpscaleError,
    data_url_to_image,
    image_to_data_url,
)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, lines=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self._lines = lines or []

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data

    def iter_lines(self, decode_unicode=False):
        return iter(self._lines)


def make_upscaler():
    temp_manager = Mock()
    device_manager = Mock()
    device_manager.current_device = "CPU"
    device_manager.get_available_devices.return_value = ["CPU"]
    return UpscalerTab(temp_manager, device_manager), device_manager


def test_numpy_bgr_frame_round_trip():
    frame = np.zeros((2, 3, 3), dtype=np.uint8)
    frame[0, 0] = [255, 0, 0]

    payload = image_to_data_url(frame, input_is_bgr=True)
    decoded = np.asarray(data_url_to_image(payload))

    assert decoded.shape == frame.shape
    assert decoded[0, 0].tolist() == [0, 0, 255]


def test_client_calls_gradio_api_and_decodes_result():
    output_payload = image_to_data_url(Image.new("RGB", (4, 4), "red"))
    api_result = {
        "ok": True,
        "image": output_payload,
        "model": "RealESRGAN_x2plus",
        "scale": 2,
        "device": "GPU (CUDA)",
    }
    session = Mock()
    session.post.return_value = FakeResponse(json_data={"event_id": "event-123"})
    session.get.return_value = FakeResponse(
        lines=["event: complete", f"data: {json.dumps([api_result])}", ""]
    )

    client = RemoteUpscaleClient("https://example.gradio.live/", session=session)
    result = client.upscale_image(Image.new("RGB", (2, 2)), "RealESRGAN_x2plus")

    assert result.size == (4, 4)
    assert client.last_response["device"] == "GPU (CUDA)"
    assert "/gradio_api/call/upscale_image" in session.post.call_args.args[0]
    assert session.get.call_args.args[0].endswith("/event-123")


def test_client_falls_back_to_legacy_gradio_route():
    output_payload = image_to_data_url(Image.new("RGB", (1, 1), "blue"))
    session = Mock()
    session.post.side_effect = [
        FakeResponse(status_code=404),
        FakeResponse(json_data={"event_id": "legacy-event"}),
    ]
    session.get.return_value = FakeResponse(
        lines=[
            "event: complete",
            f'data: {json.dumps([{"ok": True, "image": output_payload}])}',
            "",
        ]
    )

    client = RemoteUpscaleClient("https://example.gradio.live", session=session)
    client.upscale_image(Image.new("RGB", (1, 1)), "RealESRGAN_x4plus")

    assert session.post.call_count == 2
    assert "/call/upscale_image" in session.post.call_args.args[0]


def test_client_surfaces_api_error():
    session = Mock()
    session.post.return_value = FakeResponse(json_data={"event_id": "failed-event"})
    session.get.return_value = FakeResponse(
        lines=[
            "event: complete",
            'data: [{"ok": false, "error": "Invalid token"}]',
            "",
        ]
    )
    client = RemoteUpscaleClient("https://example.gradio.live", session=session)

    try:
        client.upscale_image(Image.new("RGB", (1, 1)), "RealESRGAN_x4plus")
    except RemoteUpscaleError as exc:
        assert "Invalid token" in str(exc)
    else:
        raise AssertionError("RemoteUpscaleError was not raised")


def test_server_api_prefers_cuda_and_returns_base64(tmp_path):
    tab, device_manager = make_upscaler()
    device_manager.get_available_devices.return_value = ["CPU", "GPU (CUDA)"]
    output_path = tmp_path / "upscaled.png"
    Image.new("RGB", (4, 4), "green").save(output_path)
    tab.upscale_image = Mock(return_value=(output_path, "success"))
    input_payload = image_to_data_url(Image.new("RGB", (2, 2), "green"))

    result = tab.upscale_image_api(input_payload, "RealESRGAN_x2plus")

    assert result["ok"] is True
    assert result["device"] == "GPU (CUDA)"
    assert result["scale"] == MODELS["RealESRGAN_x2plus"]["scale"]
    assert result["image"].startswith("data:image/png;base64,")
    assert tab.upscale_image.call_args.args[2] == "GPU (CUDA)"


def test_server_api_checks_optional_token(monkeypatch):
    monkeypatch.setenv("UPSCALE_API_TOKEN", "secret-token")
    tab, _ = make_upscaler()
    tab.upscale_image = Mock()

    result = tab.upscale_image_api("unused", "RealESRGAN_x4plus", "wrong-token")

    assert result == {"ok": False, "error": "Invalid or missing UPSCALE_API_TOKEN"}
    tab.upscale_image.assert_not_called()


def test_server_api_rejects_unknown_model():
    tab, _ = make_upscaler()

    result = tab.upscale_image_api("unused", "unknown-model")

    assert result["ok"] is False
    assert result["available_models"] == list(MODELS.keys())
