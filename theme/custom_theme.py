"""
Custom Gradio Theme
Amber, Red, Gray, Black, and White color scheme
"""
from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes
import base64
from pathlib import Path


class CustomTheme(Base):
    """Custom theme with amber, red, gray, black, and white colors"""
    
    def __init__(self):
        super().__init__(
            primary_hue=colors.orange,  # Amber
            secondary_hue=colors.red,     # Red
            neutral_hue=colors.gray,      # Gray
            font=fonts.GoogleFont("Inter"),
            font_mono=fonts.GoogleFont("JetBrains Mono"),
        )
        
        # Override specific colors
        self.set(
            # Background colors
            body_background_fill="#1A1A1A",           # Near black
            body_background_fill_dark="#0D0D0D",      # Darker black
            
            # Surface colors
            block_background_fill="#2D2D2D",          # Dark gray
            block_background_fill_dark="#242424",
            
            # Input/Interactive elements
            input_background_fill="#3D3D3D",          # Medium gray
            input_background_fill_dark="#333333",
            input_border_color="#555555",             # Light gray border
            input_border_color_dark="#4D4D4D",
            
            # Primary colors (Amber)
            button_primary_background_fill="#FFA500",        # Amber
            button_primary_background_fill_dark="#FF8C00",   # Dark amber
            button_primary_background_fill_hover="#FFB833",
            button_primary_text_color="#000000",             # Black text on amber
            
            # Secondary colors (Red)
            button_secondary_background_fill="#DC143C",      # Crimson red
            button_secondary_background_fill_dark="#B71C1C",
            button_secondary_background_fill_hover="#E53935",
            button_secondary_text_color="#FFFFFF",           # White text
            
            # Text colors
            body_text_color="#FFFFFF",                # White
            body_text_color_dark="#EEEEEE",
            body_text_color_subdued="#B0B0B0",        # Light gray
            block_label_text_color="#FFA500",         # Amber for labels
            block_title_text_color="#FFA500",         # Amber for titles
            
            # Border colors
            block_border_color="#555555",
            block_border_color_dark="#4D4D4D",
            
            # Shadow
            shadow_drop="0 4px 6px rgba(220, 20, 60, 0.1)",  # Subtle red shadow
            shadow_drop_lg="0 10px 15px rgba(255, 165, 0, 0.1)",  # Amber shadow
            
            # Link colors
            link_text_color="#FFA500",                       # Amber
            link_text_color_hover="#FFB833",
            link_text_color_visited="#FF8C00",
            
            # Error/Warning colors
            error_background_fill="#DC143C",          # Red
            error_text_color="#FFFFFF",
            
            # Panel colors
            panel_background_fill="#242424",
            panel_background_fill_dark="#1A1A1A",
            
            # Slider colors
            slider_color="#FFA500",                   # Amber
        )


def get_background_image_base64():
    """Convert background image to base64 for embedding in CSS"""
    try:
        img_path = Path(__file__).parent.parent / "img" / "background.jpg"
        if img_path.exists():
            with open(img_path, "rb") as img_file:
                encoded = base64.b64encode(img_file.read()).decode()
                return f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        print(f"Warning: Could not load background image: {e}")
    return ""


def create_custom_css():
    """Create custom CSS for additional styling"""
    bg_image = get_background_image_base64()
    
    bg_style = ""
    if bg_image:
        bg_style = f"""
    /* Background image with parallax effect */
    .gradio-container::before {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url('{bg_image}');
        background-size: cover;
        background-position: center center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        opacity: 0.2;
        z-index: -2;
        pointer-events: none;
    }}
    
    /* Dark overlay for better contrast */
    .gradio-container::after {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: radial-gradient(ellipse at center, 
            rgba(26, 26, 26, 0.75) 0%, 
            rgba(13, 13, 13, 0.9) 100%);
        z-index: -1;
        pointer-events: none;
    }}
    """
    
    return f"""
    {bg_style}
    
    /* Global smooth scroll */
    html {{
        scroll-behavior: smooth;
    }}
    
    body {{
        position: relative;
        overflow-x: hidden;
    }}
    
    /* Parallax scrolling simulation */
    @media (prefers-reduced-motion: no-preference) {{
        .gradio-container {{
            animation: subtle-float 20s ease-in-out infinite;
        }}
        
        @keyframes subtle-float {{
            0%, 100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-10px); }}
        }}
    }}
    
    /* Global styles */
    .gradio-container {{
        font-family: 'Inter', sans-serif;
        position: relative;
        z-index: 1;
        backdrop-filter: blur(0px);
        transition: backdrop-filter 0.3s ease;
    }}
    
    /* Headers */
    h1, h2, h3 {{
        color: #FFA500 !important;  /* Amber */
        font-weight: 600;
    }}
    
    /* Tabs */
    .tab-nav button {{
        color: #B0B0B0 !important;
        border-bottom: 2px solid transparent;
    }}
    
    .tab-nav button.selected {{
        color: #FFA500 !important;  /* Amber */
        border-bottom: 2px solid #FFA500;
    }}
    
    .tab-nav button:hover {{
        color: #FFB833 !important;
    }}
    
    /* Buttons */
    button.primary {{
        background: linear-gradient(135deg, #FFA500 0%, #FF8C00 100%) !important;
        border: none;
        font-weight: 600;
        transition: all 0.3s ease;
    }}
    
    button.primary:hover {{
        background: linear-gradient(135deg, #FFB833 0%, #FFA500 100%) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 165, 0, 0.3);
    }}
    
    button.secondary {{
        background: linear-gradient(135deg, #DC143C 0%, #B71C1C 100%) !important;
        transition: all 0.3s ease;
    }}
    
    button.secondary:hover {{
        background: linear-gradient(135deg, #E53935 0%, #DC143C 100%) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(220, 20, 60, 0.3);
    }}
    
    /* File upload areas */
    .file-upload {{
        border: 2px dashed #555555;
        border-radius: 8px;
        transition: all 0.3s ease;
    }}
    
    .file-upload:hover {{
        border-color: #FFA500;
        background-color: rgba(255, 165, 0, 0.05);
    }}
    
    /* Progress bars */
    .progress-bar {{
        background: linear-gradient(90deg, #FFA500 0%, #DC143C 100%);
    }}
    
    /* Markdown content */
    .markdown-text {{
        color: #FFFFFF;
    }}
    
    .markdown-text a {{
        color: #FFA500;
        text-decoration: none;
        transition: color 0.2s ease;
    }}
    
    .markdown-text a:hover {{
        color: #FFB833;
        text-decoration: underline;
    }}
    
    /* Modal overlay */
    .modal-overlay {{
        background-color: rgba(0, 0, 0, 0.85);
    }}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {{
        width: 10px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: #1A1A1A;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: #555555;
        border-radius: 5px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: #FFA500;
    }}
    
    /* Input fields */
    input, textarea, select {{
        background-color: #3D3D3D !important;
        border: 1px solid #555555 !important;
        color: #FFFFFF !important;
    }}
    
    input:focus, textarea:focus, select:focus {{
        border-color: #FFA500 !important;
        box-shadow: 0 0 0 2px rgba(255, 165, 0, 0.2) !important;
    }}
    
    /* Dropdown menus */
    .dropdown {{
        background-color: #3D3D3D;
        border: 1px solid #555555;
    }}
    
    .dropdown-item:hover {{
        background-color: rgba(255, 165, 0, 0.1);
    }}
    """
