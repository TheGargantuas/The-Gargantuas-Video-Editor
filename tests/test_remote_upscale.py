"""Tests for the remote Colab/Gradio upscaling API."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
import requests
from PIL import Image

from config.config import MODELS
from tabs.upscaler_tab import MAX_VIDEO_CHUNK_FRAMES, UpscalerTab
from utils.remote_upscale import (
    RemoteUpscaleClient,
    RemoteUpscaleError,
    data_url_to_image,
    decode_video_data_url,
    image_to_data_url,
    video_file_to_data_url,
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
    assert len(session.post.call_args.kwargs["json"]["data"]) == 2
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
            'data: [{"ok": false, "error": "Remote processing failed"}]',
            "",
        ]
    )
    client = RemoteUpscaleClient("https://example.gradio.live", session=session)

    try:
        client.upscale_image(Image.new("RGB", (1, 1)), "RealESRGAN_x4plus")
    except RemoteUpscaleError as exc:
        assert "Remote processing failed" in str(exc)
    else:
        raise AssertionError("RemoteUpscaleError was not raised")


def test_client_lists_remote_models():
    models_result = {
        "ok": True,
        "default_model": "RealESRGAN_x4plus",
        "models": [
            {
                "name": "RealESRGAN_x4plus",
                "scale": 4,
                "description": "General purpose",
                "default": True,
            }
        ],
    }
    session = Mock()
    session.post.return_value = FakeResponse(json_data={"data": [models_result]})

    client = RemoteUpscaleClient("https://example.gradio.live", session=session)
    result = client.list_models()

    assert result == models_result
    assert "/gradio_api/api/upscale_models" in session.post.call_args.args[0]
    assert session.post.call_args.kwargs["json"] == {"data": []}
    session.get.assert_not_called()


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


def test_server_api_lists_models():
    tab, _ = make_upscaler()

    result = tab.get_upscale_models_api()

    assert result["ok"] is True
    assert result["default_model"] == "RealESRGAN_x4plus"
    assert [model["name"] for model in result["models"]] == list(MODELS.keys())
    assert result["models"][0]["scale"] == MODELS["RealESRGAN_x4plus"]["scale"]
    assert result["api_version"] == 4
    assert result["capabilities"] == {
        "image_upscale": True,
        "video_chunks": True,
        "chunk_frames": 100,
        "max_chunk_frames": MAX_VIDEO_CHUNK_FRAMES,
        "preserve_source_fps": True,
        "optional_output_fps": True,
        "video_chunk_progress": True,
        "video_chunk_progress_version": 1,
    }


def test_video_data_url_round_trip_and_signature_validation(tmp_path):
    video = tmp_path / "chunk.mp4"
    payload = b"\x00\x00\x00\x18ftypisompayload"
    video.write_bytes(payload)

    encoded = video_file_to_data_url(video, max_bytes=1024)

    assert decode_video_data_url(encoded, max_bytes=1024) == payload
    try:
        decode_video_data_url("data:video/mp4;base64,AAAA", max_bytes=1024)
    except ValueError as exc:
        assert "MP4" in str(exc)
    else:
        raise AssertionError("Malformed MP4 was accepted")


def test_server_video_chunk_api_returns_exact_metadata_and_cleans_workspace(tmp_path):
    tab, _ = make_upscaler()
    chunks_root = tmp_path / "api_video_chunks"
    tab.temp_manager.create_temp_subdir.return_value = chunks_root
    tab.load_model = Mock(return_value="loaded")
    tab.upsampler = Mock()
    source = tmp_path / "source.mp4"
    source.write_bytes(b"\x00\x00\x00\x18ftypisominput")

    def stream(_source, output, _model, **options):
        assert options["expected_frames"] == 100
        assert options["fps_override"] == 0
        assert options["crf"] == 12
        Path(output).write_bytes(b"\x00\x00\x00\x18ftypisomoutput")
        return {"frame_count": 100, "fps": 30.0, "width": 1280, "height": 720, "elapsed_seconds": 2.5}

    tab._stream_upscaled_video = Mock(side_effect=stream)

    events = list(tab.upscale_video_chunk_api(
        video_file_to_data_url(source, max_bytes=1024),
        "RealESRGAN_x2plus",
        100,
    ))
    result = events[-1]

    assert result["ok"] is True
    assert result["frame_count"] == 100
    assert result["video"].startswith("data:video/mp4;base64,")
    assert any(item.get("event") == "progress" and item.get("state") == "finalizing" for item in events)
    assert not chunks_root.exists() or list(chunks_root.iterdir()) == []


def test_server_video_chunk_api_accepts_large_batches_and_explicit_fps(tmp_path):
    tab, _ = make_upscaler()
    tab.temp_manager.create_temp_subdir.return_value = tmp_path / "api_video_chunks"
    tab.load_model = Mock(return_value="loaded")
    tab.upsampler = Mock()
    source = tmp_path / "source.mp4"
    source.write_bytes(b"\x00\x00\x00\x18ftypisominput")

    def stream(_source, output, _model, **options):
        assert options["expected_frames"] == 300
        assert options["fps_override"] == 59.94
        Path(output).write_bytes(b"\x00\x00\x00\x18ftypisomoutput")
        return {"frame_count": 300, "fps": 59.94, "width": 1280, "height": 720, "elapsed_seconds": 2.5}

    tab._stream_upscaled_video = Mock(side_effect=stream)
    result = list(tab.upscale_video_chunk_api(
        video_file_to_data_url(source, max_bytes=1024), "RealESRGAN_x2plus", 300, 59.94
    ))[-1]

    assert result["ok"] is True
    assert result["frame_count"] == 300
    assert result["fps"] == 59.94


def test_server_video_chunk_api_streams_real_frame_progress(tmp_path):
    tab, _ = make_upscaler()
    tab.temp_manager.create_temp_subdir.return_value = tmp_path / "api_video_chunks"
    tab.load_model = Mock(return_value="loaded")
    tab.upsampler = Mock()
    source = tmp_path / "source.mp4"
    source.write_bytes(b"\x00\x00\x00\x18ftypisominput")

    def stream(_source, output, _model, **options):
        options["on_frame"](1, 4, 0.5, 0.5)
        options["on_frame"](2, 4, 0.4, 0.9)
        Path(output).write_bytes(b"\x00\x00\x00\x18ftypisomoutput")
        return {"frame_count": 4, "fps": 24.0, "width": 128, "height": 72, "elapsed_seconds": 1.8}

    tab._stream_upscaled_video = Mock(side_effect=stream)
    events = list(tab.upscale_video_chunk_api(
        video_file_to_data_url(source, max_bytes=1024), "RealESRGAN_x2plus", 4
    ))
    progress = [item for item in events if item.get("event") == "progress"]

    assert progress
    assert any(item["state"] == "upscaling" and item["completed_frames"] == 2 for item in progress)
    update = next(item for item in progress if item["state"] == "upscaling" and item["completed_frames"] == 2)
    assert update["progress"] == pytest.approx(0.5)
    assert update["seconds_per_frame"] == pytest.approx(0.45)
    assert update["estimated_remaining_seconds"] == pytest.approx(0.9)
    assert events[-1]["ok"] is True


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_stream_encoder_writes_frames_during_upscaling_without_png_sequence(tmp_path):
    source = tmp_path / "source.mp4"
    output = tmp_path / "output.mp4"
    subprocess.run([
        shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=32x24:rate=30:duration=1",
        "-frames:v", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
    ], check=True)
    tab, _ = make_upscaler()
    tab.upsampler = Mock()
    tab.upsampler.enhance.side_effect = lambda frame, outscale: (
        np.repeat(np.repeat(frame, int(outscale), axis=0), int(outscale), axis=1),
        None,
    )

    metadata = tab._stream_upscaled_video(
        source, output, "RealESRGAN_x2plus", expected_frames=30
    )

    assert metadata["frame_count"] == 30
    assert metadata["fps"] == pytest.approx(30)
    assert (metadata["width"], metadata["height"]) == (64, 48)
    assert output.exists() and output.stat().st_size > 0
    assert not list(tmp_path.glob("*.png"))


def test_server_api_rejects_unknown_model():
    tab, _ = make_upscaler()

    result = tab.upscale_image_api("unused", "unknown-model")

    assert result["ok"] is False
    assert result["available_models"] == list(MODELS.keys())
