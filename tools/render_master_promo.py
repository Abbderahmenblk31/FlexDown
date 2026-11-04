import os
import math
import struct
import wave
import subprocess
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1920
FPS = 30
DURATION_SEC = 38.06
TOTAL_FRAMES = int(FPS * DURATION_SEC)

BASE_DIR = r"C:\Users\abdra\.gemini\antigravity\scratch\FlexDown"
OUTPUT_DIR = os.path.join(BASE_DIR, "master_frames")
os.makedirs(OUTPUT_DIR, exist_ok=True)

DESKTOP = r"C:\Users\abdra\OneDrive\Bureau"
FINAL_VIDEO = os.path.join(DESKTOP, "FlexDown_TikTok_Master_Promo.mp4")
FFMPEG = os.path.join(BASE_DIR, "bin", "ffmpeg.exe")

VOICE_FILE = os.path.join(BASE_DIR, "full_voice.wav")
MUSIC_FILE = os.path.join(BASE_DIR, "ambient_tech_beat.wav")
MIXED_AUDIO = os.path.join(BASE_DIR, "mixed_master_audio.wav")

LOGO_PATH = os.path.join(BASE_DIR, "resources", "icons", "app.png")
logo_img = Image.open(LOGO_PATH).convert("RGBA")

APP_RENDER_PATH = os.path.join(BASE_DIR, "asset_main_window.png")
app_window_img = Image.open(APP_RENDER_PATH).convert("RGBA")

# Load fonts safely
def load_font(size, bold=False):
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(font_name, size)
    except Exception:
        try:
            return ImageFont.truetype("segoeui.ttf", size)
        except Exception:
            return ImageFont.load_default()

font_hero = load_font(72, bold=True)
font_title = load_font(52, bold=True)
font_subtitle = load_font(36, bold=False)
font_card_title = load_font(38, bold=True)
font_card_sub = load_font(28, bold=False)
font_badge = load_font(28, bold=True)
font_caption = load_font(42, bold=True)
font_link = load_font(32, bold=True)

def draw_rounded(draw, xy, fill, outline=None, width=1, radius=24):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=width)

def get_bg(f, theme="navy"):
    img = Image.new("RGB", (WIDTH, HEIGHT), (11, 15, 25))
    draw = ImageDraw.Draw(img)
    
    # Gradient base
    for y in range(0, HEIGHT, 8):
        ratio = y / HEIGHT
        if theme == "red":
            r = int(18 + ratio * 20)
            g = int(8 + ratio * 10)
            b = int(14 + ratio * 12)
        elif theme == "magenta":
            r = int(14 + ratio * 18)
            g = int(10 + ratio * 12)
            b = int(24 + ratio * 32)
        else: # navy
            r = int(10 + ratio * 12)
            g = int(14 + ratio * 18)
            b = int(26 + ratio * 38)
        draw.rectangle([(0, y), (WIDTH, y + 8)], fill=(r, g, b))
        
    # Moving cyber light orbs
    glow_x = int(WIDTH * 0.5 + 180 * math.sin(f * 0.025))
    glow_y = int(HEIGHT * 0.45 + 140 * math.cos(f * 0.025))
    glow_col = (30, 20, 45) if theme == "magenta" else ((35, 15, 20) if theme == "red" else (18, 32, 60))
    draw.ellipse([glow_x - 320, glow_y - 320, glow_x + 320, glow_y + 320], fill=glow_col)
    
    return img

print(f"Rendering {TOTAL_FRAMES} frames for Master FlexDown Ad...")

# Scene Boundaries in seconds:
# S1 (Hook): 0.00 -> 5.83
# S2 (Hero Reveal): 5.83 -> 12.26
# S3 (TikTok No Watermark): 12.26 -> 16.65
# S4 (YouTube 4K & MP3): 16.65 -> 25.34
# S5 (Safety & Speed): 25.34 -> 30.76
# S6 & S7 (Offer & CTA): 30.76 -> 38.06

for f in range(TOTAL_FRAMES):
    t = f / FPS
    
    # -------------------------------------------------------------
    # SCENE 1: Hook (0.0s - 5.83s)
    # -------------------------------------------------------------
    if t < 5.83:
        img = get_bg(f, theme="red")
        draw = ImageDraw.Draw(img)
        
        # Brand top pill
        draw_rounded(draw, (WIDTH//2 - 210, 80, WIDTH//2 + 210, 140), fill=(24, 30, 45), outline=(56, 189, 248), width=2, radius=16)
        draw.text((WIDTH//2, 110), "⚡ FLEXDOWN DOWNLOADER", fill=(255, 255, 255), font=font_badge, anchor="mm")
        
        # Red warning badge
        draw_rounded(draw, (WIDTH//2 - 200, 260, WIDTH//2 + 200, 320), fill=(239, 68, 68, 40), outline=(239, 68, 68), width=2, radius=16)
        draw.text((WIDTH//2, 290), "⚠️ WARNING TO PC USERS", fill=(248, 113, 113), font=font_badge, anchor="mm")
        
        draw.text((WIDTH//2, 390), "STOP USING SHADY SITES", fill=(255, 255, 255), font=font_title, anchor="mm")
        draw.text((WIDTH//2, 460), "TO DOWNLOAD VIDEOS!", fill=(239, 68, 68), font=font_hero, anchor="mm")
        
        cards = [
            ("❌  Fake Download Buttons & Popups", 600, (239, 68, 68), 0.0),
            ("❌  Malware & Risky Broken Cracks", 750, (249, 115, 22), 1.6),
            ("❌  Slow Downloads & Watermarks", 900, (234, 179, 8), 3.4),
        ]
        for c_txt, cy, c_col, appear_t in cards:
            if t >= appear_t:
                draw_rounded(draw, (80, cy - 50, WIDTH - 80, cy + 50), fill=(24, 30, 48), outline=c_col, width=2, radius=20)
                draw.text((120, cy), c_txt, fill=(241, 245, 249), font=font_card_title, anchor="lm")
                
        # Caption
        if t < 3.2:
            caption = "Stop risking your PC with sketchy download sites..."
        else:
            caption = "...and broken IDM cracks!"
        draw_rounded(draw, (70, 1420, WIDTH - 70, 1520), fill=(15, 23, 42, 240), outline=(239, 68, 68), width=2, radius=22)
        draw.text((WIDTH//2, 1470), caption, fill=(251, 191, 36), font=font_caption, anchor="mm")

    # -------------------------------------------------------------
    # SCENE 2: The Hero / Real App Reveal (5.83s - 12.26s)
    # -------------------------------------------------------------
    elif t < 12.26:
        img = get_bg(f, theme="navy")
        draw = ImageDraw.Draw(img)
        
        # Brand top pill
        draw_rounded(draw, (WIDTH//2 - 210, 80, WIDTH//2 + 210, 140), fill=(24, 30, 45), outline=(56, 189, 248), width=2, radius=16)
        draw.text((WIDTH//2, 110), "⚡ FLEXDOWN DOWNLOADER", fill=(255, 255, 255), font=font_badge, anchor="mm")
        
        # Header
        draw.text((WIDTH//2, 220), "MEET FLEXDOWN", fill=(255, 255, 255), font=font_hero, anchor="mm")
        draw.text((WIDTH//2, 280), "The Cleanest & Fastest Media Downloader for Windows", fill=(56, 189, 248), font=font_subtitle, anchor="mm")
        
        # COMPOSITE REAL APP WINDOW WITH GLOW AND SMOOTH SCALING
        app_w = 980
        app_h = int(app_w * (app_window_img.height / app_window_img.width))
        app_resized = app_window_img.resize((app_w, app_h), Image.Resampling.LANCZOS)
        
        app_x = WIDTH//2 - app_w//2
        app_y = 330
        
        # Glowing frame around real app
        draw_rounded(draw, (app_x - 8, app_y - 8, app_x + app_w + 8, app_y + app_h + 8), fill=None, outline=(56, 189, 248), width=3, radius=18)
        img.paste(app_resized, (app_x, app_y), app_resized)
        
        # 3 Value Pillars
        pillars = [
            ("⚡ 5X FASTER MULTI-THREAD ENGINE", 1020, (56, 189, 248)),
            ("🛡️ 100% CLEAN • ZERO ADS • NO CRACKS", 1140, (16, 185, 129)),
            ("💻 100% PORTABLE • INSTANT WINDOWS RUN", 1260, (233, 69, 96)),
        ]
        for p_txt, cy, p_col in pillars:
            draw_rounded(draw, (80, cy - 42, WIDTH - 80, cy + 42), fill=(24, 30, 48), outline=p_col, width=2, radius=16)
            draw.text((WIDTH//2, cy), p_txt, fill=(255, 255, 255), font=font_badge, anchor="mm")
            
        # Caption
        if t < 8.8:
            caption = "Meet FlexDown."
        else:
            caption = "The fastest, cleanest media downloader built for Windows."
        draw_rounded(draw, (70, 1420, WIDTH - 70, 1520), fill=(15, 23, 42, 240), outline=(56, 189, 248), width=2, radius=22)
        draw.text((WIDTH//2, 1470), caption, fill=(251, 191, 36), font=font_caption, anchor="mm")

    # -------------------------------------------------------------
    # SCENE 3: TikTok No Watermark (12.26s - 16.65s)
    # -------------------------------------------------------------
    elif t < 16.65:
        img = get_bg(f, theme="magenta")
        draw = ImageDraw.Draw(img)
        
        # Top pill
        draw_rounded(draw, (WIDTH//2 - 210, 80, WIDTH//2 + 210, 140), fill=(24, 30, 45), outline=(236, 72, 153), width=2, radius=16)
        draw.text((WIDTH//2, 110), "🎬 TIKTOK DOWNLOADER", fill=(255, 255, 255), font=font_badge, anchor="mm")
        
        draw.text((WIDTH//2, 230), "TIKTOK IN FULL HD", fill=(236, 72, 153), font=font_title, anchor="mm")
        draw.text((WIDTH//2, 300), "ZERO WATERMARK", fill=(255, 255, 255), font=font_hero, anchor="mm")
        
        # Giant Feature Showcase Card
        draw_rounded(draw, (80, 380, WIDTH - 80, 860), fill=(24, 30, 52), outline=(236, 72, 153), width=3, radius=24)
        
        # TikTok mock download row inside FlexDown
        draw.text((120, 430), "📱 TikTok Video Link Detected", fill=(148, 163, 184), font=font_badge, anchor="lm")
        draw.text((120, 490), "Viral_Creator_Dance_NoWatermark.mp4", fill=(255, 255, 255), font=font_card_title, anchor="lm")
        
        # Progress Bar hitting 100%
        prog_ratio = min(1.0, (t - 12.26) / 2.5)
        bar_w = int((WIDTH - 240) * prog_ratio)
        draw_rounded(draw, (120, 560, WIDTH - 120, 595), fill=(15, 23, 42), radius=10)
        draw_rounded(draw, (120, 560, 120 + bar_w, 595), fill=(236, 72, 153), radius=10)
        
        speed_txt = "COMPLETED • 1080p Full HD" if prog_ratio >= 1.0 else f"Downloading at 14.8 MB/s... ({int(prog_ratio*100)}%)"
        draw.text((120, 640), speed_txt, fill=(16, 185, 129) if prog_ratio >= 1.0 else (56, 189, 248), font=font_badge, anchor="lm")
        
        # 3 Badges
        b1 = "✨ 100% Original Quality"
        b2 = "🚫 Clean: No TikTok Watermark"
        b3 = "⚡ 2-Second Instant Download"
        draw.text((120, 710), b1, fill=(241, 245, 249), font=font_card_sub, anchor="lm")
        draw.text((120, 760), b2, fill=(251, 191, 36), font=font_card_sub, anchor="lm")
        draw.text((120, 810), b3, fill=(16, 185, 129), font=font_card_sub, anchor="lm")
        
        # Real App Mini Preview Card
        draw_rounded(draw, (80, 910, WIDTH - 80, 1240), fill=(20, 26, 42), outline=(56, 189, 248), width=2, radius=20)
        draw.text((WIDTH//2, 955), "💻 REAL FLEXDOWN INTERFACE", fill=(56, 189, 248), font=font_badge, anchor="mm")
        
        # Mini crop of app window
        crop_h = 240
        app_mini = app_window_img.crop((0, 0, app_window_img.width, int(app_window_img.width * 0.28)))
        app_mini_res = app_mini.resize((WIDTH - 200, crop_h), Image.Resampling.LANCZOS)
        img.paste(app_mini_res, (100, 985), app_mini_res)
        
        # Caption
        caption = "Download TikTok videos without watermark in Full HD!"
        draw_rounded(draw, (70, 1420, WIDTH - 70, 1520), fill=(15, 23, 42, 240), outline=(236, 72, 153), width=2, radius=22)
        draw.text((WIDTH//2, 1470), caption, fill=(251, 191, 36), font=font_caption, anchor="mm")

    # -------------------------------------------------------------
    # SCENE 4: YouTube 4K & MP3 320k (16.65s - 25.34s)
    # -------------------------------------------------------------
    elif t < 25.34:
        img = get_bg(f, theme="navy")
        draw = ImageDraw.Draw(img)
        
        # Top pill
        draw_rounded(draw, (WIDTH//2 - 220, 80, WIDTH//2 + 220, 140), fill=(24, 30, 45), outline=(239, 68, 68), width=2, radius=16)
        draw.text((WIDTH//2, 110), "📺 YOUTUBE 4K & STUDIO MP3", fill=(255, 255, 255), font=font_badge, anchor="mm")
        
        draw.text((WIDTH//2, 230), "ULTRA HD & STUDIO AUDIO", fill=(56, 189, 248), font=font_title, anchor="mm")
        draw.text((WIDTH//2, 300), "POWERFUL FEATURES", fill=(255, 255, 255), font=font_hero, anchor="mm")
        
        # Card 1: 4K YouTube Video
        draw_rounded(draw, (80, 380, WIDTH - 80, 680), fill=(24, 30, 52), outline=(239, 68, 68), width=2, radius=22)
        draw.text((120, 430), "📺 YouTube 4K Ultra HD & 60 FPS", fill=(255, 255, 255), font=font_card_title, anchor="lm")
        draw.text((120, 485), "• Select any resolution: 4K, 2K, 1080p, 720p", fill=(203, 213, 225), font=font_card_sub, anchor="lm")
        draw.text((120, 535), "• Batch download complete playlists in 1 click", fill=(203, 213, 225), font=font_card_sub, anchor="lm")
        draw.text((120, 585), "• Auto-embed subtitles & metadata tags", fill=(203, 213, 225), font=font_card_sub, anchor="lm")
        draw_rounded(draw, (120, 620, 240, 660), fill=(239, 68, 68), radius=8)
        draw.text((180, 640), "4K UHD", fill=(255, 255, 255), font=font_badge, anchor="mm")
        draw_rounded(draw, (255, 620, 390, 660), fill=(37, 99, 235), radius=8)
        draw.text((322, 640), "60 FPS", fill=(255, 255, 255), font=font_badge, anchor="mm")
        draw_rounded(draw, (405, 620, 570, 660), fill=(16, 185, 129), radius=8)
        draw.text((487, 640), "PLAYLISTS", fill=(255, 255, 255), font=font_badge, anchor="mm")
        
        # Card 2: 320kbps MP3 Audio
        draw_rounded(draw, (80, 720, WIDTH - 80, 1020), fill=(24, 30, 52), outline=(168, 85, 247), width=2, radius=22)
        draw.text((120, 770), "🎵 320kbps Studio Master MP3", fill=(255, 255, 255), font=font_card_title, anchor="lm")
        draw.text((120, 825), "• Extract crystal-clear music from any video", fill=(203, 213, 225), font=font_card_sub, anchor="lm")
        draw.text((120, 875), "• High-fidelity 320k bit-rate with FFmpeg engine", fill=(203, 213, 225), font=font_card_sub, anchor="lm")
        draw.text((120, 925), "• Audio formats: MP3, WAV, FLAC, AAC, M4A", fill=(203, 213, 225), font=font_card_sub, anchor="lm")
        
        # Animated Audio visualizer bars
        for bar_i in range(16):
            bx = 120 + bar_i * 32
            bh = max(4, int(14 + 16 * math.sin(f * 0.2 + bar_i * 0.5)))
            draw.rectangle([bx, 990 - bh, bx + 18, 990], fill=(168, 85, 247))
            
        # Floating badge card
        draw_rounded(draw, (80, 1060, WIDTH - 80, 1200), fill=(20, 26, 42), outline=(56, 189, 248), width=2, radius=18)
        draw.text((WIDTH//2, 1105), "⚡ 1-CLICK FLOATING DOWNLOAD BADGE", fill=(56, 189, 248), font=font_badge, anchor="mm")
        draw.text((WIDTH//2, 1155), "Hovers over YouTube, TikTok, Facebook & X in your browser", fill=(203, 213, 225), font=font_card_sub, anchor="mm")
        
        # Caption
        if t < 20.8:
            caption = "Grab YouTube 4K videos, playlists..."
        else:
            caption = "...or extract crystal-clear 320k MP3 in 1 click!"
        draw_rounded(draw, (70, 1420, WIDTH - 70, 1520), fill=(15, 23, 42, 240), outline=(56, 189, 248), width=2, radius=22)
        draw.text((WIDTH//2, 1470), caption, fill=(251, 191, 36), font=font_caption, anchor="mm")

    # -------------------------------------------------------------
    # SCENE 5: Safe & Portable & 5X Faster (25.34s - 30.76s)
    # -------------------------------------------------------------
    elif t < 30.76:
        img = get_bg(f, theme="navy")
        draw = ImageDraw.Draw(img)
        
        # Top pill
        draw_rounded(draw, (WIDTH//2 - 210, 80, WIDTH//2 + 210, 140), fill=(24, 30, 45), outline=(16, 185, 129), width=2, radius=16)
        draw.text((WIDTH//2, 110), "🛡️ 100% VERIFIED VIRUS-FREE", fill=(16, 185, 129), font=font_badge, anchor="mm")
        
        draw.text((WIDTH//2, 230), "WHY USERS LOVE IT", fill=(56, 189, 248), font=font_title, anchor="mm")
        draw.text((WIDTH//2, 300), "BUILT FOR WINDOWS", fill=(255, 255, 255), font=font_hero, anchor="mm")
        
        cards = [
            ("🚀  5X Faster Multi-Thread Engine", "Download split-segments concurrently at max speed", 440, (56, 189, 248)),
            ("💾  100% Portable Package", "No complex installation needed • Run from USB or Desktop", 640, (16, 185, 129)),
            ("🔒  Military AES-256 File Privacy", "Password-protect sensitive downloads with one toggle", 840, (236, 72, 153)),
            ("🚫  Zero Popups • Zero Spyware", "100% clean code tested with bandit security and pip-audit", 1040, (251, 191, 36)),
        ]
        for c_title, c_sub, cy, c_col in cards:
            draw_rounded(draw, (80, cy - 65, WIDTH - 80, cy + 65), fill=(24, 30, 52), outline=c_col, width=2, radius=20)
            draw.text((120, cy - 18), c_title, fill=(255, 255, 255), font=font_card_title, anchor="lm")
            draw.text((120, cy + 24), c_sub, fill=(148, 163, 184), font=font_card_sub, anchor="lm")
            
        # Caption
        caption = "It is portable, 100% virus-free, and five times faster!"
        draw_rounded(draw, (70, 1420, WIDTH - 70, 1520), fill=(15, 23, 42, 240), outline=(16, 185, 129), width=2, radius=22)
        draw.text((WIDTH//2, 1470), caption, fill=(251, 191, 36), font=font_caption, anchor="mm")

    # -------------------------------------------------------------
    # SCENE 6 & 7: High Converting Offer & Call to Action (30.76s - 38.06s)
    # -------------------------------------------------------------
    else:
        img = get_bg(f, theme="navy")
        draw = ImageDraw.Draw(img)
        
        # Top pill
        draw_rounded(draw, (WIDTH//2 - 210, 80, WIDTH//2 + 210, 140), fill=(24, 30, 45), outline=(251, 191, 36), width=2, radius=16)
        draw.text((WIDTH//2, 110), "🔥 SPECIAL LAUNCH OFFER 🔥", fill=(251, 191, 36), font=font_badge, anchor="mm")
        
        draw.text((WIDTH//2, 230), "GET YOUR LIFETIME COPY", fill=(56, 189, 248), font=font_title, anchor="mm")
        draw.text((WIDTH//2, 300), "FLEXDOWN PRO", fill=(255, 255, 255), font=font_hero, anchor="mm")
        
        # Huge Golden Offer Box
        draw_rounded(draw, (80, 380, WIDTH - 80, 760), fill=(26, 34, 56), outline=(251, 191, 36), width=3, radius=26)
        draw.text((WIDTH//2, 440), "⭐ LIFETIME LICENSE ⭐", fill=(251, 191, 36), font=font_badge, anchor="mm")
        draw.text((WIDTH//2, 540), "$10 ONLY", fill=(255, 255, 255), font=font_hero, anchor="mm")
        draw.text((WIDTH//2, 630), "One-Time Payment • No Monthly Fees", fill=(16, 185, 129), font=font_card_title, anchor="mm")
        draw.text((WIDTH//2, 690), "All Future Updates Included Free Forever", fill=(148, 163, 184), font=font_card_sub, anchor="mm")
        
        # Pulsing CTA button
        pulse = int(14 * math.sin(f * 0.25))
        btn_y = 900
        draw_rounded(draw, (90 - pulse, btn_y - 65, WIDTH - 90 + pulse, btn_y + 65), fill=(233, 69, 96), radius=38)
        draw.text((WIDTH//2, btn_y), "👉 TAP LINK IN BIO TO DOWNLOAD", fill=(255, 255, 255), font=font_card_title, anchor="mm")
        
        # Store Link Box
        draw_rounded(draw, (80, 1040, WIDTH - 80, 1160), fill=(15, 23, 42), outline=(56, 189, 248), width=2, radius=20)
        draw.text((WIDTH//2, 1080), "OFFICIAL GUMROAD STORE:", fill=(148, 163, 184), font=font_badge, anchor="mm")
        draw.text((WIDTH//2, 1120), "abdoubelkhiria.gumroad.com/l/zgntp", fill=(56, 189, 248), font=font_link, anchor="mm")
        
        # Trust badges
        draw.text((WIDTH//2, 1240), "🔒 Instant Direct Download • Windows 10 & 11 • Virus-Free", fill=(203, 213, 225), font=font_card_sub, anchor="mm")
        
        # Caption
        if t < 34.6:
            caption = "Get your lifetime license today for just $10!"
        else:
            caption = "Tap the link in bio to get FlexDown now!"
        draw_rounded(draw, (70, 1420, WIDTH - 70, 1520), fill=(15, 23, 42, 240), outline=(251, 191, 36), width=2, radius=22)
        draw.text((WIDTH//2, 1470), caption, fill=(251, 191, 36), font=font_caption, anchor="mm")

    # Save frame
    frame_path = os.path.join(OUTPUT_DIR, f"frame_{f:04d}.png")
    img.save(frame_path)
    if (f + 1) % 150 == 0 or f == TOTAL_FRAMES - 1:
        print(f"Rendered {f + 1}/{TOTAL_FRAMES} frames ({(f + 1) / TOTAL_FRAMES * 100:.1f}%)")

print("Synthesizing ambient tech beat...")
sample_rate = 44100
total_samples = int(sample_rate * DURATION_SEC)
with wave.open(MUSIC_FILE, "w") as wav:
    wav.setnchannels(2)
    wav.setsampwidth(2)
    wav.setframerate(sample_rate)
    frames_bytes = bytearray()
    bpm = 120.0
    beat_interval = 60.0 / bpm
    for i in range(total_samples):
        t_sec = i / sample_rate
        b_phase = (t_sec % beat_interval) / beat_interval
        
        # Warm electronic kick on 1 and 3
        kick = math.sin(2 * math.pi * (110 * (1 - b_phase * 0.75)) * b_phase) * math.exp(-b_phase * 7) if b_phase < 0.25 else 0
        
        # Subtle hi-hat
        sixteenth = ((t_sec % (beat_interval / 4)) / (beat_interval / 4))
        hihat = 0.12 * math.sin(2 * math.pi * 9200 * sixteenth) * math.exp(-sixteenth * 28) if sixteenth < 0.08 else 0
        
        # Smooth deep chord progression
        chords = [55.0, 65.4, 73.4, 82.4]
        note = chords[int(t_sec / 2.0) % len(chords)]
        pad = 0.22 * math.sin(2 * math.pi * note * t_sec) + 0.11 * math.sin(2 * math.pi * (note * 1.5) * t_sec)
        
        val = max(-1.0, min(1.0, (kick * 0.45 + hihat * 0.2 + pad * 0.35)))
        sample_int = int(val * 5500) # Quiet background level (-18dB)
        frames_bytes.extend(struct.pack("<hh", sample_int, sample_int))
    wav.writeframes(frames_bytes)

print("Mixing Voice and Music with FFmpeg...")
mix_cmd = [
    FFMPEG,
    "-y",
    "-i", VOICE_FILE,
    "-i", MUSIC_FILE,
    "-filter_complex",
    "[0:a]volume=2.6,aformat=sample_rates=44100:channel_layouts=stereo[v];[1:a]volume=0.22[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2[aout]",
    "-map", "[aout]",
    "-c:a", "pcm_s16le",
    MIXED_AUDIO
]
subprocess.run(mix_cmd, check=True)

print("Encoding Master 1080x1920 MP4 Video...")
ffmpeg_cmd = [
    FFMPEG,
    "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(OUTPUT_DIR, "frame_%04d.png"),
    "-i", MIXED_AUDIO,
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-preset", "fast",
    "-crf", "18",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    FINAL_VIDEO
]
subprocess.run(ffmpeg_cmd, check=True)
print(f"MASTER PROMO VIDEO COMPLETED AT: {FINAL_VIDEO}")

# Clean up temporary frames
for f in os.listdir(OUTPUT_DIR):
    try:
        os.remove(os.path.join(OUTPUT_DIR, f))
    except Exception:
        pass
try:
    os.rmdir(OUTPUT_DIR)
    os.remove(MUSIC_FILE)
    os.remove(MIXED_AUDIO)
except Exception:
    pass
