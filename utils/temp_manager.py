"""
Temporary Files Manager
Handles creation and cleanup of temporary files and directories
"""
import shutil
import atexit
from pathlib import Path
from config.config import TEMP_DIR


class TempManager:
    """Manages temporary files and directories"""
    
    def __init__(self):
        self.temp_dir = TEMP_DIR
        self.frames_dir = self.temp_dir / "frames"
        self.output_dir = self.temp_dir / "output"
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
    
    def initialize(self):
        """Initialize temp directories"""
        # Clean up any existing temp files first
        self.cleanup()
        
        # Create fresh directories
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        self.frames_dir.mkdir(exist_ok=True, parents=True)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        print(f"✓ Temporary directories initialized at {self.temp_dir}")
    
    def cleanup(self):
        """Clean up all temporary files"""
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                print("✓ Temporary files cleaned up")
            except Exception as e:
                print(f"Warning: Could not clean up temp directory: {e}")
    
    def get_frames_dir(self):
        """Get frames directory path"""
        return self.frames_dir
    
    def get_output_dir(self):
        """Get output directory path"""
        return self.output_dir
    
    def create_temp_subdir(self, name):
        """Create a subdirectory in temp"""
        subdir = self.temp_dir / name
        subdir.mkdir(exist_ok=True, parents=True)
        return subdir
    
    def get_temp_file_path(self, filename):
        """Get path for a temp file"""
        return self.temp_dir / filename
