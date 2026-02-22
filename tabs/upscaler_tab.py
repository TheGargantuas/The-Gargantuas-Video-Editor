"""
Upscaler Tab
AI-powered image and video upscaling using RealESRGAN models
"""
import cv2
import numpy as np
from PIL import Image
import torch
from pathlib import Path
import gradio as gr
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from config.config import MODELS
import ffmpeg
import os
import time
import shutil


class UpscalerTab:
    """Handles image and video upscaling functionality"""
    
    def __init__(self, temp_manager, device_manager):
        self.temp_manager = temp_manager
        self.device_manager = device_manager
        self.current_model = None
        self.current_model_name = None
        self.upsampler = None
    
    def load_model(self, model_name, device):
        """Load RealESRGAN model"""
        if self.current_model_name == model_name and self.upsampler is not None:
            return f"✓ Model {model_name} already loaded"
        
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
            
            return f"✓ Model {model_name} loaded successfully on {device}"
            
        except Exception as e:
            # Reset upsampler on error
            self.upsampler = None
            self.current_model_name = None
            return f"✗ Error loading model: {str(e)}"
    
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
            
            # Save to temp file with same format as input
            output_path = self.temp_manager.get_temp_file_path(f"upscaled_image.{input_format}")
            output_image.save(output_path, format=input_format.upper())
            
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
            
            # Open video
            progress(0.1, desc="Opening video...")
            cap = cv2.VideoCapture(input_video)
            
            if not cap.isOpened():
                return None, "✗ Could not open video file"
            
            # Get video properties
            original_fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Use original fps if None or 0
            if fps is None or fps == 0:
                fps = original_fps
            
            # Calculate output dimensions
            scale = MODELS[model_name]['scale']
            output_width = width * scale
            output_height = height * scale
            
            progress(0.15, desc=f"Processing {total_frames} frames...")
            
            # Create frames directory
            frames_dir = self.temp_manager.get_frames_dir()
            output_frames_dir = self.temp_manager.create_temp_subdir("output_frames")
            
            # Extract and upscale frames with timing
            frame_count = 0
            total_processing_time = 0
            start_time = time.time()
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_start = time.time()
                
                # Upscale frame
                output_frame, _ = self.upsampler.enhance(frame, outscale=scale)
                
                frame_end = time.time()
                frame_time = frame_end - frame_start
                total_processing_time += frame_time
                
                # Save frame
                output_frame_path = output_frames_dir / f"frame_{frame_count:06d}.png"
                cv2.imwrite(str(output_frame_path), output_frame)
                
                frame_count += 1
                avg_time_per_frame = total_processing_time / frame_count
                remaining_frames = total_frames - frame_count
                eta_seconds = remaining_frames * avg_time_per_frame
                
                progress(0.15 + (0.7 * frame_count / total_frames), 
                        desc=f"Frame {frame_count}/{total_frames} | {avg_time_per_frame:.2f}s/frame | ETA: {eta_seconds:.1f}s")
                
                # Print to terminal
                print(f"Frame {frame_count}/{total_frames} processed in {frame_time:.2f}s (avg: {avg_time_per_frame:.2f}s/frame)")
            
            cap.release()
            
            total_time = time.time() - start_time
            print(f"\n✓ All frames processed in {total_time:.2f}s")
            print(f"  Average: {total_processing_time/frame_count:.2f}s/frame")
            
            progress(0.85, desc="Encoding video...")
            
            # Reconstruct video (always same filename to avoid duplicates)
            temp_video_path = self.temp_manager.get_temp_file_path("upscaled_video_no_audio.mp4")
            output_video_path = self.temp_manager.get_temp_file_path("upscaled_video.mp4")
            
            # Remove old files if exist
            if temp_video_path.exists():
                temp_video_path.unlink()
            if output_video_path.exists():
                output_video_path.unlink()
            
            # Encode video without audio first
            (
                ffmpeg
                .input(str(output_frames_dir / "frame_%06d.png"), framerate=fps)
                .output(str(temp_video_path), vcodec='libx264', pix_fmt='yuv420p', crf=18)
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            
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
            
            # Clean up output frames after encoding
            try:
                shutil.rmtree(output_frames_dir)
                print(f"✓ Cleaned up output frames directory")
            except Exception as e:
                print(f"Warning: Could not clean up output frames: {e}")
            
            progress(1.0, desc="Done!")
            
            avg_time_per_frame = total_processing_time / frame_count
            
            info = f"✓ Video upscaled successfully\n{load_msg}\n"
            info += f"Frames processed: {frame_count}\n"
            info += f"Original size: {width}x{height}\n"
            info += f"Upscaled size: {output_width}x{output_height}\n"
            info += f"FPS: {fps}\n"
            info += f"Audio: {'✓ Preserved' if has_audio else '✗ No audio track'}\n"
            info += f"\n⏱️ Performance:\n"
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
            # Handle jpeg -> jpg conversion
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
                    # Model selection
                    model_dropdown = gr.Dropdown(
                        choices=list(MODELS.keys()),
                        value="RealESRGAN_x4plus",
                        label="Select Model",
                        info="Choose the upscaling model"
                    )
                    
                    # Device selection
                    device_dropdown = gr.Dropdown(
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
                            maximum=120,
                            info="Only for videos. Output images keep original format."
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
                        visible=False
                    )
                    info_output = gr.Textbox(
                        label="Processing Info",
                        lines=6
                    )
            
            upscale_btn.click(
                fn=self.upscale_file,
                inputs=[file_input, model_dropdown, device_dropdown, video_fps],
                outputs=[image_output, video_output, info_output, image_output, video_output]
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
                        base_video = gr.Video(
                            value="example/example_video/base.mp4",
                            label="",
                            autoplay=False,
                            show_label=False,
                            height=500
                        )
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### ✨ Upscaled")
                        example_video = gr.Video(
                            value="example/example_video/example RealESRGAN_x4plus.mp4",
                            label="",
                            autoplay=False,
                            show_label=False,
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
