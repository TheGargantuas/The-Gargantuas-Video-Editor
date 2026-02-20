"""
Video Editor - Main Application
AI-Powered Video Editing Suite - 100% Free!
"""
import gradio as gr
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import modules
from config.config import ensure_directories
from utils.temp_manager import TempManager
from utils.device_manager import DeviceManager
from tabs.upscaler_tab import UpscalerTab
from tabs.support_tab import SupportTab
from theme.custom_theme import CustomTheme, create_custom_css


class VideoEditorApp:
    """Main application class"""
    
    def __init__(self):
        # Initialize managers
        self.temp_manager = TempManager()
        self.device_manager = DeviceManager()
        
        # Initialize tabs
        self.upscaler_tab = UpscalerTab(self.temp_manager, self.device_manager)
        self.support_tab = SupportTab()
        
    def initialize(self):
        """Initialize application"""
        print("=" * 60)
        print("🎬 VIDEO EDITOR - AI-Powered Editing Suite")
        print("=" * 60)
        
        # Setup directories
        ensure_directories()
        self.temp_manager.initialize()
        
        # Display device info
        device_info = self.device_manager.get_device_info()
        print(f"\n📱 Device Information:")
        print(f"   Platform: {device_info['platform']}")
        print(f"   Current Device: {device_info['current']}")
        print(f"   Available Devices: {', '.join(device_info['available'])}")
        
        print("\n" + "=" * 60)
        print("✓ Application initialized successfully")
        print("✓ 100% Free - No authentication required!")
        print("=" * 60 + "\n")
    
    def create_interface(self):
        """Create Gradio interface"""
        self.theme = CustomTheme()
        self.custom_css = create_custom_css()
        
        with gr.Blocks(title="Video Editor - Free AI Upscaler") as app:
            # Header
            gr.Markdown("""
            # 🎬 Video Editor - AI-Powered Suite
            ### Professional video and image enhancement powered by AI
            ### 💯 100% FREE - No Login Required! 🎉
            """)
            
            # Main Tabs
            self.upscaler_tab.create_tab()
            self.support_tab.create_tab()
            
            # Placeholder for future tabs
            with gr.Tab("➕ More Coming Soon"):
                gr.Markdown("""
                ## 🚀 Future Features
                
                This application is designed with a modular architecture. 
                New tabs and features can be easily added:
                
                - 🎞️ Video Trimming & Cutting
                - 🎨 Color Grading
                - 🎵 Audio Enhancement
                - 📝 Subtitle Generation
                - 🔄 Format Conversion
                - And much more!
                
                Stay tuned for updates!
                """)
            
            # Footer
            gr.Markdown("""
            ---
            <div style="text-align: center; color: #B0B0B0; padding: 20px;">
                <p style="margin-bottom: 10px;">💖 <strong>Made with love</strong> | 100% Free & Open Software</p>
                <p style="font-size: 14px; color: #FFA500;">
                    🎉 No ads, no subscriptions, no BS - just great software!
                </p>
                <p style="font-size: 13px; margin-top: 15px;">
                    If you like this app, check out the <strong>❤️ Support Me</strong> tab! 🙏
                </p>
            </div>
            """)
        
        return app
    
    def launch(self):
        """Launch the application"""
        self.initialize()
        
        app = self.create_interface()
        
        # Get absolute paths to directories
        img_dir = Path(__file__).parent / "img"
        example_dir = Path(__file__).parent / "example"
        
        # Launch with specific settings
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True,
            quiet=False,
            theme=self.theme,
            css=self.custom_css,
            allowed_paths=[str(img_dir), str(example_dir)]
        )


def main():
    """Main entry point"""
    try:
        app = VideoEditorApp()
        app.launch()
    except KeyboardInterrupt:
        print("\n\n👋 Application closed by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
