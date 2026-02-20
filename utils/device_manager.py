"""
Device Manager
Handles device selection and management for AI models (CPU, CUDA GPU, MPS)
"""
import torch
import platform


class DeviceManager:
    """Manages compute device selection"""
    
    def __init__(self):
        self.available_devices = self._detect_devices()
        self.current_device = self._get_default_device()
    
    def _detect_devices(self):
        """Detect available compute devices"""
        devices = ["CPU"]
        
        # Check for CUDA (NVIDIA GPU)
        if torch.cuda.is_available():
            devices.append("GPU (CUDA)")
        
        # Check for MPS (Apple Silicon)
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            devices.append("MPS (Apple Silicon)")
        
        return devices
    
    def _get_default_device(self):
        """Get default device based on what's available"""
        if "MPS (Apple Silicon)" in self.available_devices:
            return "MPS (Apple Silicon)"
        elif "GPU (CUDA)" in self.available_devices:
            return "GPU (CUDA)"
        else:
            return "CPU"
    
    def get_available_devices(self):
        """Get list of available devices"""
        return self.available_devices
    
    def set_device(self, device_name):
        """Set current device"""
        if device_name in self.available_devices:
            self.current_device = device_name
            print(f"✓ Device set to: {device_name}")
            return True
        else:
            print(f"Warning: Device {device_name} not available")
            return False
    
    def get_torch_device(self):
        """Get PyTorch device object"""
        if self.current_device == "GPU (CUDA)":
            return torch.device("cuda")
        elif self.current_device == "MPS (Apple Silicon)":
            return torch.device("mps")
        else:
            return torch.device("cpu")
    
    def get_device_info(self):
        """Get information about current device"""
        info = {
            "current": self.current_device,
            "available": self.available_devices,
            "platform": platform.system()
        }
        
        if self.current_device == "GPU (CUDA)":
            info["cuda_version"] = torch.version.cuda
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["gpu_memory"] = f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB"
        elif self.current_device == "MPS (Apple Silicon)":
            info["mps_available"] = True
        
        return info
