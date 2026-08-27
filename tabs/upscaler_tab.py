"""
Upscaler Tab
AI-powered image and video upscaling using RealESRGAN models
"""
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import gradio as gr
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from config.config import MODELS
import ffmpeg
import os
import subprocess
import time
import shutil
import uuid

from utils.remote_upscale import (
    decode_image_data_url,
    decode_video_data_url,
    image_file_to_data_url,
    video_file_to_data_url,
)

DEFAULT_VIDEO_CHUNK_FRAMES = max(1, int(os.getenv("UPSCALE_API_DEFAULT_CHUNK_FRAMES", "100")))
MAX_VIDEO_CHUNK_FRAMES = max(DEFAULT_VIDEO_CHUNK_FRAMES, int(os.getenv("UPSCALE_API_MAX_CHUNK_FRAMES", "5000")))


class UpscalerTab:
    """Handles image and video upscaling functionality"""
    
    def __init__(self, temp_manager, device_manager):
        self.temp_manager = temp_manager
        self.device_manager = device_manager
        self.current_model = None
        self.current_model_name = None
        self.current_device_name = None
        self.upsampler = None
    
    def load_model(self, model_name, device):
        """Load RealESRGAN model"""
        if (
            self.current_model_name == model_name
            and self.current_device_name == device
            and self.upsampler is not None
        ):
            return f"✓ Model {model_name} already loaded on {device}"
        
        try:
            model_config = MODELS[model_name]
            scale = model_config['scale']
            
            # Select device
            self.device_manager.set_device(device)
            torch_device = self.device_manager.get_torch_device()
            
            # Define model architecture
            if 'anime' in model_name:
                model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, 
                               num_block=6, num_grow_ch=32, scale=scale)
            else:
                model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, 
                               num_block=23, num_grow_ch=32, scale=scale)
            
            # Initialize upsampler
            self.upsampler = RealESRGANer(
                scale=scale,
                model_path=model_config['url'],
                model=model,
                tile=0,
                tile_pad=10,
                pre_pad=0,
                half=True if str(torch_device) != 'cpu' else False,
                device=str(torch_device)
            )
            
            self.current_model_name = model_name
            self.current_device_name = device
            
            return f"✓ Model {model_name} loaded successfully on {device}"
            
        except Exception as e:
            # Reset upsampler on error
            self.upsampler = None
            self.current_model_name = None
            self.current_device_name = None
            return f"✗ Error loading model: {str(e)}"

    def _get_api_device(self):
        """Prefer the fastest device available for remote API calls."""
        available_devices = self.device_manager.get_available_devices()
        for preferred_device in ("GPU (CUDA)", "MPS (Apple Silicon)", "CPU"):
            if preferred_device in available_devices:
                return preferred_device
        return self.device_manager.current_device

    def get_upscale_models_api(self):
        """Return the models exposed by the remote upscaling API."""
        default_model = next(
            (name for name, config in MODELS.items() if config.get("default")),
            next(iter(MODELS)),
        )
        return {
            "ok": True,
            "api_version": 3,
            "capabilities": {
                "image_upscale": True,
                "video_chunks": True,
                "chunk_frames": DEFAULT_VIDEO_CHUNK_FRAMES,
                "max_chunk_frames": MAX_VIDEO_CHUNK_FRAMES,
                "preserve_source_fps": True,
                "optional_output_fps": True,
            },
            "default_model": default_model,
            "models": [
                {
                    "name": name,
                    "scale": config["scale"],
                    "description": config["description"],
                    "default": name == default_model,
                }
                for name, config in MODELS.items()
            ],
        }

    def upscale_image_api(self, image_payload, model_name):
        """Upscale a base64 image/frame through the public Gradio API."""
        if model_name not in MODELS:
            return {
                "ok": False,
                "error": f"Unsupported model: {model_name}",
                "available_models": list(MODELS.keys()),
            }

        try:
            max_input_mb = float(os.getenv("UPSCALE_API_MAX_INPUT_MB", "25"))
            if max_input_mb <= 0:
                raise ValueError
        except ValueError:
            max_input_mb = 25

        try:
            image, input_format = decode_image_data_url(
                image_payload,
                max_bytes=int(max_input_mb * 1024 * 1024),
            )
            device = self._get_api_device()
            output_path, info = self.upscale_image(
                image,
                model_name,
                device,
                input_format=input_format,
            )
            if output_path is None:
                return {"ok": False, "error": info}

            return {
                "ok": True,
                "image": image_file_to_data_url(output_path),
                "model": model_name,
                "scale": MODELS[model_name]["scale"],
                "device": device,
                "info": info,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _start_raw_video_encoder(output_path, width, height, fps, *, crf=18):
        """Start a fast H.264 encoder fed with OpenCV BGR frames on stdin."""
        ffmpeg_executable = shutil.which("ffmpeg")
        if not ffmpeg_executable:
            raise RuntimeError("ffmpeg is required to encode an upscaled video")
        command = [
            ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-f", "rawvideo", "-pix_fmt", "bgr24", "-s:v", f"{width}x{height}",
            "-r", f"{fps:.8f}", "-i", "pipe:0", "-an", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(output_path),
        ]
        return subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    def _stream_upscaled_video(
        self,
        input_path,
        output_path,
        model_name,
        *,
        fps_override=None,
        expected_frames=None,
        crf=18,
        on_frame=None,
    ):
        """Upscale and encode concurrently, without an intermediate PNG sequence."""
        capture = cv2.VideoCapture(str(input_path))
        if not capture.isOpened():
            raise RuntimeError("Could not open video file")
        source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        source_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        source_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        requested_fps = float(fps_override or 0)
        if not np.isfinite(requested_fps) or requested_fps < 0:
            capture.release()
            raise ValueError("Video FPS must be 0 (original) or a positive finite value")
        fps = requested_fps or source_fps or 30
        reported_total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        scale = MODELS[model_name]["scale"]
        process = None
        frame_count = 0
        width = height = 0
        started_at = time.time()
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if expected_frames is not None and frame_count >= expected_frames:
                    raise ValueError(f"The chunk contains more than {expected_frames} frames")
                frame_started_at = time.time()
                output_frame, _ = self.upsampler.enhance(frame, outscale=scale)
                output_frame = np.ascontiguousarray(output_frame, dtype=np.uint8)
                if process is None:
                    height, width = output_frame.shape[:2]
                    process = self._start_raw_video_encoder(output_path, width, height, fps, crf=crf)
                if process.stdin is None:
                    raise RuntimeError("ffmpeg input pipe is unavailable")
                process.stdin.write(output_frame.tobytes())
                frame_count += 1
                if on_frame:
                    on_frame(
                        frame_count,
                        reported_total or expected_frames or frame_count,
                        time.time() - frame_started_at,
                        time.time() - started_at,
                    )
            if frame_count == 0:
                raise ValueError("The input video contains no decodable frames")
            if expected_frames is not None and frame_count != expected_frames:
                raise ValueError(f"Frame count mismatch: expected {expected_frames}, decoded {frame_count}")
            assert process is not None
            assert process.stdin is not None
            process.stdin.close()
            stderr = process.stderr.read().decode("utf-8", "replace") if process.stderr else ""
            return_code = process.wait()
            if return_code:
                raise RuntimeError(f"ffmpeg encoding failed: {stderr.strip() or return_code}")
            return {
                "frame_count": frame_count,
                "fps": fps,
                "width": width,
                "height": height,
                "source_width": source_width,
                "source_height": source_height,
                "elapsed_seconds": time.time() - started_at,
            }
        except Exception:
            if process is not None and process.poll() is None:
                if process.stdin:
                    try:
                        process.stdin.close()
                    except OSError:
                        pass
                process.kill()
                process.wait()
            Path(output_path).unlink(missing_ok=True)
            raise
        finally:
            capture.release()

    def upscale_video_chunk_api(self, video_payload, model_name, expected_frames, output_fps=0):
        """Upscale one bounded MP4 chunk for MLSM Studio's parallel scheduler."""
        if model_name not in MODELS:
            return {"ok": False, "error": f"Unsupported model: {model_name}", "available_models": list(MODELS.keys())}
        try:
            expected = int(expected_frames)
            if expected < 1 or expected > MAX_VIDEO_CHUNK_FRAMES:
                raise ValueError(f"A video chunk must contain from 1 to {MAX_VIDEO_CHUNK_FRAMES} frames")
            requested_fps = float(output_fps or 0)
            if not np.isfinite(requested_fps) or requested_fps < 0:
                raise ValueError("Output FPS must be 0 (original) or a positive finite value")
            max_input_mb = max(1, float(os.getenv("UPSCALE_API_MAX_VIDEO_INPUT_MB", "256")))
            max_output_mb = max(1, float(os.getenv("UPSCALE_API_MAX_VIDEO_OUTPUT_MB", "1024")))
            source_bytes = decode_video_data_url(video_payload, max_bytes=int(max_input_mb * 1024 * 1024))
            job_dir = self.temp_manager.create_temp_subdir("api_video_chunks") / uuid.uuid4().hex
            job_dir.mkdir(parents=True, exist_ok=False)
            source_path = job_dir / "input.mp4"
            output_path = job_dir / "upscaled.mp4"
            source_path.write_bytes(source_bytes)
            device = self._get_api_device()
            load_message = self.load_model(model_name, device)
            if self.upsampler is None:
                raise RuntimeError(load_message)
            metadata = self._stream_upscaled_video(
                source_path,
                output_path,
                model_name,
                fps_override=requested_fps,
                expected_frames=expected,
                crf=12,
            )
            return {
                "ok": True,
                "api_version": 3,
                "video": video_file_to_data_url(output_path, max_bytes=int(max_output_mb * 1024 * 1024)),
                "model": model_name,
                "scale": MODELS[model_name]["scale"],
                "device": device,
                **metadata,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            if "job_dir" in locals():
                shutil.rmtree(job_dir, ignore_errors=True)
    
    def upscale_image(self, input_image, model_name, device, input_format="png"):
        """Upscale a single image"""
        if input_image is None:
            return None, "Please upload an image"
        
        try:
            # Load model if needed
            load_msg = self.load_model(model_name, device)
            
            # Check if model loaded successfully
            if self.upsampler is None:
                return None, f"✗ Failed to load model\n{load_msg}"
            
            # Convert to numpy array if needed
            if isinstance(input_image, Image.Image):
                img = np.array(input_image)
            else:
                img = input_image
            
            # Convert RGB to BGR for OpenCV
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            # Upscale
            output, _ = self.upsampler.enhance(img, outscale=MODELS[model_name]['scale'])
            
            # Convert back to RGB
            output = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            output_image = Image.fromarray(output)
            
            # Normalize format for PIL (JPG -> JPEG)
            save_format = input_format.upper()
            if save_format == 'JPG':
                save_format = 'JPEG'
            
            # Save to temp file with same format as input
            output_path = self.temp_manager.get_temp_file_path(f"upscaled_image.{input_format}")
            output_image.save(output_path, format=save_format)
            
            info = f"✓ Image upscaled successfully\n{load_msg}\n"
            info += f"Original size: {img.shape[1]}x{img.shape[0]}\n"
            info += f"Upscaled size: {output.shape[1]}x{output.shape[0]}"
            
            # Return the file path instead of PIL Image to preserve format
            return output_path, info
            
        except Exception as e:
            return None, f"✗ Error upscaling image: {str(e)}"
    
    def upscale_video(self, input_video, model_name, device, fps=None, progress=gr.Progress()):
        """Upscale a video file"""
        if input_video is None:
            return None, "Please upload a video"
        
        try:
            progress(0, desc="Loading model...")
            load_msg = self.load_model(model_name, device)
            
            # Check if model loaded successfully
            if self.upsampler is None:
                return None, f"✗ Failed to load model\n{load_msg}"
            
            # Check if video has audio
            progress(0.05, desc="Checking audio...")
            audio_path = None
            has_audio = False
            
            try:
                probe = ffmpeg.probe(input_video)
                audio_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'audio']
                has_audio = len(audio_streams) > 0
                
                if has_audio:
                    # Extract audio
                    print("✓ Audio detected, extracting...")
                    audio_path = self.temp_manager.get_temp_file_path("original_audio.aac")
                    
                    # Remove old audio file if exists
                    if audio_path.exists():
                        audio_path.unlink()
                    
                    (
                        ffmpeg
                        .input(input_video)
                        .output(str(audio_path), acodec='copy', vn=None)
                        .overwrite_output()
                        .run(quiet=True, capture_stdout=True, capture_stderr=True)
                    )
                    print(f"✓ Audio extracted to {audio_path}")
                else:
                    print("ℹ️ No audio stream detected in video")
            except Exception as e:
                print(f"Warning: Could not extract audio: {e}")
                has_audio = False
            
            progress(0.1, desc="Upscaling and encoding video...")
            temp_video_path = self.temp_manager.get_temp_file_path("upscaled_video_no_audio.mp4")
            output_video_path = self.temp_manager.get_temp_file_path("upscaled_video.mp4")
            if temp_video_path.exists():
                temp_video_path.unlink()
            if output_video_path.exists():
                output_video_path.unlink()

            def update_progress(done, total, frame_time, elapsed):
                average = elapsed / done
                eta = max(0, total - done) * average
                progress(0.1 + (0.82 * done / max(1, total)), desc=f"Frame {done}/{total} · {frame_time:.2f}s · ETA {eta:.1f}s")

            metadata = self._stream_upscaled_video(
                input_video,
                temp_video_path,
                model_name,
                fps_override=fps,
                on_frame=update_progress,
            )
            frame_count = metadata["frame_count"]
            fps = metadata["fps"]
            output_width = metadata["width"]
            output_height = metadata["height"]
            width = metadata["source_width"]
            height = metadata["source_height"]
            total_time = metadata["elapsed_seconds"]
            progress(0.93, desc="Finalizing audio...")
            
            # Combine with audio if available
            if has_audio and audio_path and audio_path.exists():
                progress(0.95, desc="Adding audio...")
                print("✓ Combining video with original audio...")
                
                video = ffmpeg.input(str(temp_video_path))
                audio = ffmpeg.input(str(audio_path))
                
                (
                    ffmpeg
                    .output(video, audio, str(output_video_path), vcodec='copy', acodec='aac', strict='experimental')
                    .overwrite_output()
                    .run(quiet=True, capture_stdout=True, capture_stderr=True)
                )
                
                # Clean up temp video
                temp_video_path.unlink()
                audio_path.unlink()
                print("✓ Audio successfully added to upscaled video")
            else:
                # No audio, just rename temp video
                temp_video_path.rename(output_video_path)
            
            progress(1.0, desc="Done!")
            avg_time_per_frame = total_time / frame_count
            
            info = f"✓ Video upscaled successfully\n{load_msg}\n"
            info += f"Frames processed: {frame_count}\n"
            info += f"Original size: {width}x{height}\n"
            info += f"Upscaled size: {output_width}x{output_height}\n"
            info += f"FPS: {fps}\n"
            info += f"Audio: {'✓ Preserved' if has_audio else '✗ No audio track'}\n"
            info += "\n⏱️ Performance:\n"
            info += f"  Total time: {total_time:.2f}s\n"
            info += f"  Average: {avg_time_per_frame:.2f}s/frame\n"
            info += f"  Speed: {frame_count/total_time:.2f} fps"
            
            return str(output_video_path), info
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None, f"✗ Error upscaling video: {str(e)}"
    
    def upscale_file(self, input_file, model_name, device, fps=None, progress=gr.Progress()):
        """Unified upscaling function that auto-detects file type"""
        if input_file is None:
            return None, None, "Please upload a file", gr.update(visible=False), gr.update(visible=False)
        
        # Get file extension
        file_path = input_file if isinstance(input_file, str) else input_file.name
        ext = Path(file_path).suffix.lower()
        
        # Image extensions
        image_exts = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif']
        # Video extensions
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v']
        
        if ext in image_exts:
            # Process as image
            from PIL import Image
            img = Image.open(file_path)
            # Use the same format as input (strip the dot from extension)
            input_format = ext[1:]  # Remove the leading dot
            # Normalize format: both jpg and jpeg should use jpg for filename, JPEG for PIL
            if input_format == 'jpeg':
                input_format = 'jpg'
            result, info = self.upscale_image(img, model_name, device, input_format)
            return result, None, info, gr.update(visible=True), gr.update(visible=False)
        
        elif ext in video_exts:
            # Process as video
            result, info = self.upscale_video(file_path, model_name, device, fps, progress)
            return None, result, info, gr.update(visible=False), gr.update(visible=True)
        
        else:
            return None, None, f"✗ Unsupported file format: {ext}", gr.update(visible=False), gr.update(visible=False)
    
    def create_tab(self):
        """Create and return the Gradio tab interface"""
        with gr.Tab("🎨 Upscaler"):
            gr.Markdown("""
            # AI Image & Video Upscaler
            Upload any image or video - the app will automatically detect and process it!
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    # Model and device selection in collapsible accordion
                    with gr.Accordion("🔧 Select Model & Device", open=False):
                        model_dropdown = gr.Radio(
                            choices=list(MODELS.keys()),
                            value="RealESRGAN_x4plus",
                            label="Select Model",
                            info="Choose the upscaling model"
                        )
                        
                        device_dropdown = gr.Radio(
                            choices=self.device_manager.get_available_devices(),
                            value=self.device_manager.current_device,
                            label="Compute Device",
                            info="Select processing device"
                        )
                    
                    # Model info
                    model_info = gr.Textbox(
                        label="Model Information",
                        value=MODELS["RealESRGAN_x4plus"]["description"],
                        interactive=False
                    )
                    
                    def update_model_info(model_name):
                        return MODELS[model_name]["description"]
                    
                    model_dropdown.change(
                        fn=update_model_info,
                        inputs=[model_dropdown],
                        outputs=[model_info]
                    )
            
            # Unified Upscaling Section
            gr.Markdown("## 📁 Upload File")
            with gr.Row():
                with gr.Column():
                    file_input = gr.File(
                        label="Input File (Image or Video)",
                        file_types=["image", "video"]
                    )
                    
                    # Options row
                    with gr.Row():
                        video_fps = gr.Number(
                            label="Video FPS (0 = original)",
                            value=0,
                            minimum=0,
                            info="Only for videos. Leave 0 to preserve the original frame rate and every decoded frame."
                        )
                    
                    upscale_btn = gr.Button("🚀 Upscale", variant="primary", size="lg")
                
                with gr.Column():
                    # Output containers
                    image_output = gr.Image(
                        label="Upscaled Image",
                        type="filepath",
                        visible=False
                    )
                    video_output = gr.Video(
                        label="Upscaled Video",
                        format="mp4",
                        visible=False
                    )
                    info_output = gr.Textbox(
                        label="Processing Info",
                        lines=6
                    )
            
            upscale_btn.click(
                fn=self.upscale_file,
                inputs=[file_input, model_dropdown, device_dropdown, video_fps],
                outputs=[image_output, video_output, info_output, image_output, video_output],
                concurrency_limit=1,
                concurrency_id="realesrgan_upscaler",
            )

            # Public API endpoint. Base64 keeps the REST payload self-contained,
            # so callers do not need to expose their local input file via a URL.
            with gr.Group(visible=False):
                api_image_payload = gr.Textbox(label="Base64 image or data URL")
                api_model_name = gr.Dropdown(
                    choices=list(MODELS.keys()),
                    value="RealESRGAN_x4plus",
                    label="Model",
                )
                api_result = gr.JSON(label="Upscaling API response")
                api_button = gr.Button("API Upscale")
                api_models_result = gr.JSON(label="Available upscaling models")
                api_models_button = gr.Button("API Models")
                api_video_payload = gr.Textbox(label="Base64 MP4 chunk")
                api_video_model = gr.Dropdown(choices=list(MODELS.keys()), value="RealESRGAN_x4plus", label="Chunk model")
                api_video_frames = gr.Number(value=DEFAULT_VIDEO_CHUNK_FRAMES, minimum=1, maximum=MAX_VIDEO_CHUNK_FRAMES, precision=0, label="Expected frames")
                api_video_fps = gr.Number(value=0, minimum=0, label="Output FPS (0 = chunk original)")
                api_video_result = gr.JSON(label="Video chunk API response")
                api_video_button = gr.Button("API Upscale Video Chunk")

            api_button.click(
                fn=self.upscale_image_api,
                inputs=[api_image_payload, api_model_name],
                outputs=[api_result],
                api_name="upscale_image",
                show_progress="hidden",
                concurrency_limit=1,
                concurrency_id="realesrgan_upscaler",
            )

            api_models_button.click(
                fn=self.get_upscale_models_api,
                inputs=[],
                outputs=[api_models_result],
                api_name="upscale_models",
                show_progress="hidden",
                queue=False,
            )

            api_video_button.click(
                fn=self.upscale_video_chunk_api,
                inputs=[api_video_payload, api_video_model, api_video_frames, api_video_fps],
                outputs=[api_video_result],
                api_name="upscale_video_chunk",
                show_progress="hidden",
                concurrency_limit=1,
                concurrency_id="realesrgan_upscaler",
            )
            
            # Examples Section - Expandable
            gr.Markdown("---")
            
            with gr.Accordion("📊 Compare Models - Example Videos", open=False):
                gr.Markdown("""
                ### Side-by-Side Video Comparison
                Compare the original video with different upscaling models. Videos are synchronized and maintain their original aspect ratio.
                """)
                
                # Model selector with radio buttons
                example_model_radio = gr.Radio(
                    choices=[
                        "RealESRGAN_x2plus",
                        "RealESRGAN_x4plus", 
                        "RealESRNet_x4plus",
                        "RealESRGAN_x4plus_anime_6B"
                    ],
                    value="RealESRGAN_x4plus",
                    label="Select Model to Compare",
                    info="Choose which upscaled version to compare with the original"
                )
                
                gr.Markdown("""
                **ℹ️ Note:** Use the native video player controls below to play/pause the videos. 
                They will automatically synchronize when you interact with either video.
                """)
                
                # JavaScript for automatic video synchronization
                gr.HTML("""
                <script>
                (function() {
                    function setupVideoSync() {
                        // Find video elements
                        const allVideos = document.querySelectorAll('video');
                        const videos = Array.from(allVideos).filter(v => {
                            const src = v.src || v.querySelector('source')?.src || '';
                            return src.includes('example/example_video/');
                        });
                        
                        if (videos.length < 2) {
                            console.log('Videos not ready yet, found:', videos.length);
                            return false;
                        }
                        
                        const [video1, video2] = videos;
                        
                        if (video1._syncSetup) {
                            return true; // Already set up
                        }
                        
                        // Mark as set up
                        video1._syncSetup = true;
                        video2._syncSetup = true;
                        
                        console.log('Setting up video synchronization...');
                        
                        // Mute both videos
                        video1.muted = true;
                        video2.muted = true;
                        
                        // Sync play events
                        video1.addEventListener('play', () => {
                            if (video2.paused) {
                                video2.play().catch(e => console.log('Sync play error:', e));
                            }
                        });
                        
                        video2.addEventListener('play', () => {
                            if (video1.paused) {
                                video1.play().catch(e => console.log('Sync play error:', e));
                            }
                        });
                        
                        // Sync pause events
                        video1.addEventListener('pause', () => {
                            if (!video2.paused) {
                                video2.pause();
                            }
                        });
                        
                        video2.addEventListener('pause', () => {
                            if (!video1.paused) {
                                video1.pause();
                            }
                        });
                        
                        // Sync seek events
                        video1.addEventListener('seeked', () => {
                            if (Math.abs(video1.currentTime - video2.currentTime) > 0.1) {
                                video2.currentTime = video1.currentTime;
                            }
                        });
                        
                        video2.addEventListener('seeked', () => {
                            if (Math.abs(video1.currentTime - video2.currentTime) > 0.1) {
                                video1.currentTime = video2.currentTime;
                            }
                        });
                        
                        console.log('✓ Video synchronization active');
                        return true;
                    }
                    
                    // Try to setup multiple times
                    let attempts = 0;
                    const maxAttempts = 30;
                    const interval = setInterval(() => {
                        if (setupVideoSync() || attempts >= maxAttempts) {
                            clearInterval(interval);
                            if (attempts >= maxAttempts) {
                                console.log('Video sync setup timeout');
                            }
                        }
                        attempts++;
                    }, 500);
                })();
                </script>
                """)
                
                # Videos side by side
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 🎬 Original (Base)")
                        gr.Video(
                            value="example/example_video/base.mp4",
                            label="",
                            autoplay=False,
                            show_label=False,
                            format="mp4",
                            height=500
                        )
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### ✨ Upscaled")
                        example_video = gr.Video(
                            value="example/example_video/example RealESRGAN_x4plus.mp4",
                            label="",
                            autoplay=False,
                            show_label=False,
                            format="mp4",
                            height=500
                        )
                
                # Info text
                gr.Markdown("""
                **💡 How to use:**
                1. Select a model with the radio buttons above to change the upscaled video
                2. Click the **play button** on either video - both will start automatically
                3. Use the **seek bar** to jump to any point - both videos will sync
                4. Videos are muted and maintain their original aspect ratio
                
                **Note:** The videos are automatically synchronized. When you play, pause, or seek one video, the other will follow.
                """)
                
                def update_example_video(model_name):
                    """Update example video based on selected model"""
                    video_path = f"example/example_video/example {model_name}.mp4"
                    return video_path
                
                example_model_radio.change(
                    fn=update_example_video,
                    inputs=[example_model_radio],
                    outputs=[example_video]
                )
            
            gr.Markdown("""
            ### 📝 Tips:
            - **RealESRGAN_x4plus**: Best for general photos and images
            - **RealESRGAN_x2plus**: Use for subtle enhancement or when 4x is too much
            - **RealESRNet_x4plus**: Produces cleaner results with less enhancement
            - **RealESRGAN_x4plus_anime_6B**: Specifically trained for anime and cartoon content
            - Supported image formats: JPG, PNG, WebP, BMP, TIFF
            - Supported video formats: MP4, AVI, MOV, MKV, WebM
            - Video processing may take several minutes depending on length and resolution
            - Use GPU/MPS acceleration for substantially faster processing
            """)
