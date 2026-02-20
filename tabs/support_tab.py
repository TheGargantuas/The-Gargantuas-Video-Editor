"""
Support Tab
Shows information about supporting the free app
"""
import gradio as gr
from config.config import (
    YOUTUBE_CHANNEL_URL, 
    YOUTUBE_CHANNEL_HANDLE,
    YOUTUBE_PLAYLIST_ID,
    YOUTUBE_PLAYLIST_URL,
    YOUTUBE_SUBSCRIBE_URL
)


class SupportTab:
    """Displays support information and YouTube channel integration"""
    
    def __init__(self):
        pass
    
    def create_tab(self):
        """Create and return the Support tab interface"""
        with gr.Tab("❤️ Support Me"):
            gr.Markdown("""
            # 💖 Support This Free Project
            """)
            
            # Main support message
            gr.HTML("""
            <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #2D2D2D 0%, #1A1A1A 100%); 
                        border-radius: 15px; margin: 20px 0; border: 2px solid #FFA500;">
                <h1 style="color: #FFA500; margin-bottom: 20px; font-size: 2.5em;">
                    🎉 This App is 100% FREE!
                </h1>
                <p style="color: #FFFFFF; font-size: 1.3em; margin-bottom: 25px; line-height: 1.6;">
                    No subscriptions. No hidden fees. No locked features.<br>
                    Just pure, free AI-powered video editing! 🚀
                </p>
                <div style="background: rgba(255, 165, 0, 0.1); padding: 20px; border-radius: 10px; margin: 20px auto; max-width: 600px;">
                    <p style="color: #FFB833; font-size: 1.1em; margin: 0;">
                        ✨ If you find this useful, the best way to support me is by subscribing to my YouTube channel!
                    </p>
                </div>
            </div>
            """)
            
            # YouTube Subscribe Button (styled like official YouTube button)
            gr.HTML(f"""
            <div style="text-align: center; margin: 40px 0;">
                <a href="{YOUTUBE_SUBSCRIBE_URL}" 
                   target="_blank" 
                   style="display: inline-flex; align-items: center; gap: 10px;
                          background: #DC143C; color: white; 
                          padding: 15px 40px; text-decoration: none; 
                          border-radius: 50px; font-weight: bold; font-size: 20px;
                          box-shadow: 0 4px 15px rgba(220, 20, 60, 0.4);
                          transition: all 0.3s ease;
                          border: none;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="white">
                        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                    </svg>
                    <span>Subscribe to {YOUTUBE_CHANNEL_HANDLE}</span>
                </a>
            </div>
            <style>
                a[href*="youtube"]:hover {{
                    background: #B71C1C !important;
                    transform: translateY(-3px);
                    box-shadow: 0 6px 20px rgba(220, 20, 60, 0.6) !important;
                }}
            </style>
            """)
            
            gr.Markdown("---")
            
            # Embedded Playlist
            gr.Markdown("""
            ## 🎬 Check Out My Content
            Here's a playlist of videos from my channel. Take a look and let me know what you think!
            """)
            
            gr.HTML(f"""
            <div style="margin: 30px auto; max-width: 900px;">
                <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; 
                            border-radius: 12px; box-shadow: 0 8px 20px rgba(0,0,0,0.3);">
                    <iframe 
                        src="https://www.youtube.com/embed/videoseries?list={YOUTUBE_PLAYLIST_ID}" 
                        style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
                        frameborder="0" 
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                        allowfullscreen>
                    </iframe>
                </div>
            </div>
            """)
            
            # Additional support options
            gr.Markdown("---")
            
            gr.HTML(f"""
            <div style="background: #2D2D2D; padding: 30px; border-radius: 12px; margin: 20px 0;">
                <h2 style="color: #FFA500; text-align: center; margin-bottom: 25px;">
                    💝 Other Ways to Support
                </h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0;">
                    <div style="background: #1A1A1A; padding: 25px; border-radius: 10px; text-align: center; border: 1px solid #555;">
                        <div style="font-size: 2em; margin-bottom: 15px;">👍</div>
                        <h3 style="color: #FFA500; margin-bottom: 10px;">Like Videos</h3>
                        <p style="color: #B0B0B0; font-size: 0.95em;">
                            Watch and like my videos to help with the algorithm
                        </p>
                    </div>
                    <div style="background: #1A1A1A; padding: 25px; border-radius: 10px; text-align: center; border: 1px solid #555;">
                        <div style="font-size: 2em; margin-bottom: 15px;">💬</div>
                        <h3 style="color: #FFA500; margin-bottom: 10px;">Comment</h3>
                        <p style="color: #B0B0B0; font-size: 0.95em;">
                            Leave feedback and suggestions on videos
                        </p>
                    </div>
                    <div style="background: #1A1A1A; padding: 25px; border-radius: 10px; text-align: center; border: 1px solid #555;">
                        <div style="font-size: 2em; margin-bottom: 15px;">🔔</div>
                        <h3 style="color: #FFA500; margin-bottom: 10px;">Enable Notifications</h3>
                        <p style="color: #B0B0B0; font-size: 0.95em;">
                            Hit the bell icon to get notified of new content
                        </p>
                    </div>
                    <div style="background: #1A1A1A; padding: 25px; border-radius: 10px; text-align: center; border: 1px solid #555;">
                        <div style="font-size: 2em; margin-bottom: 15px;">🌟</div>
                        <h3 style="color: #FFA500; margin-bottom: 10px;">Share</h3>
                        <p style="color: #B0B0B0; font-size: 0.95em;">
                            Tell your friends about this free app!
                        </p>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 30px; padding: 20px; background: rgba(255, 165, 0, 0.1); border-radius: 8px;">
                    <p style="color: #FFFFFF; font-size: 1.1em; margin: 0;">
                        🙏 <strong>Thank you for using this app!</strong><br>
                        <span style="color: #B0B0B0; font-size: 0.9em;">
                            Your support means everything and helps me create more free tools like this!
                        </span>
                    </p>
                </div>
            </div>
            """)
            
            # Channel link button
            gr.HTML(f"""
            <div style="text-align: center; margin: 30px 0;">
                <a href="{YOUTUBE_CHANNEL_URL}" 
                   target="_blank"
                   style="display: inline-block; background: linear-gradient(135deg, #FFA500 0%, #FF8C00 100%); 
                          color: black; padding: 12px 30px; text-decoration: none; 
                          border-radius: 8px; font-weight: bold; font-size: 16px;
                          box-shadow: 0 4px 10px rgba(255, 165, 0, 0.3);
                          transition: all 0.3s;">
                    🎥 Visit My YouTube Channel
                </a>
            </div>
            <style>
                a[href*="@TheGargantuas"]:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 6px 15px rgba(255, 165, 0, 0.5) !important;
                }}
            </style>
            """)
