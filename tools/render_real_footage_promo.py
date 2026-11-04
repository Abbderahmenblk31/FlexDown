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
OUTPUT_DIR = os.path.join(BASE_DIR, "real_promo_frames")
os.makedirs(OUTPUT_DIR, exist_ok=True)

DESKTOP = r"C:\Users\abdra\OneDrive\Bureau"
FINAL_VIDEO = os.path.join(DESKTOP, "FlexDown_TikTok_Real_Footage_Promo.mp4")
FFMPEG = os.path.join(BASE_DIR, "bin", "ffmpeg.exe")

VOICE_FILE = os.path.join(BASE_DIR, "full_voice.wav")
MUSIC_FILE = os.path.join(BASE_DIR, "ambient_tech_beat.wav")
MIXED_AUDIO = os.path.join(BASE_DIR, "real_mixed_audio.wav")

# User Real Screenshots
IMG_USER_DIR = r"C:\Users\abdra\.gemini\antigravity\brain\b9cddb44-5785-41a5-8138-09e0358ff4be\.user_uploaded"
SHOT_TIKTOK_PLAYER = os.path.join(IMG_USER_DIR, "media_1792425980509_4a7a9fc2.png")
SHOT_TIKTOK_MENU   = os.path.join(IMG_USER_DIR, "media_1792426007901_132deca0.png")
SHOT_APP_DIALOG    = os.path.join(IMG_USER_DIR, "media_1792426076791_4fe1d48a.png")

img_tiktok_player = Image.open(SHOT_TIKTOK_PLAYER).convert("RGBA")
img_tiktok_menu   = Image.open(SHOT_TIKTOK_MENU).convert("RGBA")
img_app_dialog    = Image.open(SHOT_APP_DIALOG).convert("RGBA")

LOGO_PATH = os.path.join(BASE_DIR, "resources", "icons", "app.png")
logo_img = Image.open(LOGO_PATH).convert("RGBA")

# Fonts
def load_font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(name, size)
    except Exception:
        try:
            return ImageFont.truetype("segoeui.ttf", size)
        except Exception:
            return ImageFont.load_default()

font_hero = load_font(72, bold=True)
font_title = load_font(50, bold=True)
font_subtitle = load_font(34, bold=False)
font_card_title = load_font(38, bold=True)
font_card_sub = load_font(28, bold=False)
font_badge = load_font(28, bold=True)
font_caption = load_font(42, bold=True)
font_link = load_font(32, bold=True)

def draw_rounded(draw, xy, fill, outline=None, width=1, radius=24):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=width)

def get_bg(f, theme="navy"):
    img = Image.new("RGB", (WIDTH, HEIGHT), (12, 16, 28))
    draw = ImageDraw.Draw(img)
    
    # Modern smooth gradient
    for y in range(0, HEIGHT, 8):
        ratio = y / HEIGHT
        if theme == "red":
            r = int(22 + ratio * 20)
            g = int(8 + ratio * 10)
            b = int(14 + ratio * 14)
        elif theme == "magenta":
            r = int(16 + ratio * 18)
            g = int(10 + ratio * 12)
            b = int(28 + ratio * 34)
        else: # navy
            r = int(10 + ratio * 14)
            g = int(14 + ratio * 20)
            b = int(28 + ratio * 42)
        draw.rectangle([(0, y), (WIDTH, y + 8)], fill=(r, g, b))
        
    # Subtle ambient light
    glow_x = int(WIDTH * 0.5 + 160 * math.sin(f * 0.025))
    glow_y = int(HEIGHT * 0.42 + 130 * math.cos(f * 0.025))
    glow_col = (35, 20, 50) if theme == "magenta" else ((38, 16, 22) if theme == "red" else (20, 36, 68))
    draw.ellipse([glow_x - 320, glow_y - 320, glow_x + 320, glow_y + 320], fill=glow_col)
    
    return img

print(f"Rendering {TOTAL_FRAMES} frames using USER REAL SCREENSHOTS...")

for f in range(TOTAL_FRAMES):
    t = f / FPS
    
    # -------------------------------------------------------------
    # SCENE 1: Hook / Problem (0.0s - 5.83s)
    # -------------------------------------------------------------
    if t < 5.83:
        img = get_bg(f, theme="red")
        draw = ImageDraw.Draw(img)
        
        # Brand top bar
        draw_rounded(draw, (WIDTH//2 - 210, 80, WIDTH//2 + 210, 140), fill=(24, 30, 48), outline=(56, 189, 248), width=2, radius=16)
        draw.text((WIDTH//2, 110), "⚡ FLEXDOWN DOWNLOADER", fill=(255, 255, 255), font=font_badge, anchor="mm")
        
        # Red warning badge
        draw_rounded(draw, (WIDTH//2 - 200, 260, WIDTH//2 + 200, 320), fill=(239, 68, 68, 40), outline=(239, 68, 68), width=2, radius=16)
        draw.text((WIDTH//2, 290), "⚠️ WARNING TO PC USERS", fill=(248, 113, 113), font=font_badge, anchor="mm")
        
        draw.text((WIDTH//2, 390), "STOP USING SHADY SITES", fill=(255, 255, 255), font=font_title, anchor="mm")
        draw.text((WIDTH//2, 460), "TO DOWNLOAD VIDEOS!", fill=(239, 68, 68), font=font_hero, anchor="mm")
        
        cards = [
            ("❌  Fake Download Buttons & Popups", 600, (239, 68, 68), 0.0),
            ("❌  Dangerous Malware & Broken Cracks", 750, (249, 115, 22), 1.6),
            ("❌  Slow Speeds & Ugly Watermarks", 900, (234, 179, 8), 3.4),
        ]
        for c_txt, cy, c_col, appear_t in cards:
            if t >= appear_t:
                draw_rounded(draw, (80, cy - 50, WIDTH - 80, cy + 50), fill=(24, 30, 48), outline=c_col, width=2, radius=20)
                draw.text((120, cy), c_txt, fill=(241, 245, 249), font=font_card_title, anchor="lm")
                
        # Caption
        if t < 3.2:
            caption = "Stop risking your PC with sketchy download websites..."
        else:
            caption = "...and broken IDM cracks!"
        draw_rounded(draw, (70, 1420, WIDTH - 70, 1520), fill=(15, 23, 42, 240), outline=(239, 68, 68), width=2, radius=22)
        draw.text((WIDTH//2, 1470), caption, fill=(251, 191, 36), font=font_caption, anchor="mm")

    # -------------------------------------------------------------
    # SCENE 2: The Hero / FlexDown Reveal (5.83s - 12.26s)
    # -------------------------------------------------------------
    elif t < 12.26:
        img = get_bg(f, theme="navy")
        draw = ImageDraw.Draw(img)
        
        # Brand top bar
        draw_rounded(draw, (WIDTH//2 - 210, 80, WIDTH//2 + 210, 140), fill=(24, 30, 48), outline=(56, 189, 248), width=2, radius=16)
        draw.text((WIDTH//2, 110), "⚡ FLEXDOWN DOWNLOADER", fill=(255, 255, 255), font=font_badge, anchor="mm")
        
        # Logo with breathing animation
        logo_scale = 1.0 + 0.05 * math.sin(f * 0.15)
        l_sz = int(200 * logo_scale)
        l_img = logo_img.resize((l_sz, l_sz), Image.Resampling.LANCZOS)
        img.paste(l_img, (WIDTH//2 - l_sz//2, 210 - (l_sz - 200)//2), l_img)
        
        draw.text((WIDTH//2, 450), "MEET FLEXDOWN", fill=(255, 255, 255), font=font_hero, anchor="mm")
        draw.text((WIDTH//2, 515), "The Ultimate Media Downloader for Windows", fill=(56, 189, 248), font=font_subtitle, anchor="mm")
        
        # 3 Big Value Pillars (inspired by Neat Download banner)
        pillars = [
            ("⚡ 500% FASTER MULTI-THREAD ENGINE", "Supercharged segmented download acceleration", 640, (56, 189, 248)),
            ("🌐 1-CLICK BROWSER FLOATING BADGE", "Works seamlessly inside TikTok, YouTube & Facebook", 810, (236, 72, 153)),
            ("🛡️ 100% CLEAN • ZERO ADS • ZERO CRACKS", "Verified safe, portable, no installation needed", 980, (16, 185, 129)),
            ("🎵 320kbps STUDIO AUDIO CONVERTER", "Extract crystal-clear music from any video instantly", 1150, (168, 85, 247)),
        ]
        for p_title, p_sub, cy, p_col in pillars:
            draw_rounded(draw, (80, cy - 55, WIDTH - 80, cy + 55), fill=(24, 30, 52), outline=p_col, width=2, radius=20)
            draw.text((120, cy - 16), p_title, fill=(255, 255, 255), font=font_card_title, anchor="lm")
            draw.text((120, cy + 24), p_sub, fill=(148, 163, 184), font=font_card_sub, anchor="lm")
            
        # Caption
        if t < 8.8:
            caption = "Meet FlexDown."
        else:
            caption = "The fastest, cleanest media downloader built for Windows."
        draw_rounded(draw, (70, 1420, WIDTH - 70, 1520), fill=(15, 23, 42, 240), outline=(56, 189, 248), width=2, radius=22)
        draw.text((WIDTH//2, 1470), caption, fill=(251, 191, 36), font=font_caption, anchor="mm")

    # -------------------------------------------------------------
    # SCENE 3: REAL TIKTOK FOOTAGE & 1-CLICK BADGE (12.26s - 18.2s)
    # -------------------------------------------------------------
    elif t < 18.2:
        img = get_bg(f, theme="magenta")
        draw = ImageDraw.Draw(img)
        
        # Top pill
        draw_rounded(draw, (WIDTH//2 - 210, 80, WIDTH//2 + 210, 140), fill=(24, 30, 48), outline=(236, 72, 153), width=2, radius=16)
        draw.text((WIDTH//2, 110), "🎬 REAL TIKTOK EXPERIENCE", fill=(255, 255, 255), font=font_badge, anchor="mm")
        
        draw.text((WIDTH//2, 220), "1-CLICK TIKTOK DOWNLOAD", fill=(236, 72, 153), font=font_title, anchor="mm")
        draw.text((WIDTH//2, 280), "ZERO WATERMARK • FULL HD 1080P", fill=(255, 255, 255), font=font_subtitle, anchor="mm")
        
        # Show real screenshot 1 (player with button) or screenshot 2 (menu open)
        card_w = 980
        card_x = WIDTH//2 - card_w//2
        card_y = 350
        
        if t < 15.2:
            # Shot 1: The video player with the floating badge
            shot = img_tiktok_player
            shot_ratio = card_w / shot.width
            shot_h = int(shot.height * shot_ratio)
            shot_res = shot.resize((card_w, shot_h), Image.Resampling.LANCZOS)
            
            # Glowing border
            draw_rounded(draw, (card_x - 6, card_y - 6, card_x + card_w + 6, card_y + shot_h + 6), fill=None, outline=(56, 189, 248), width=3, radius=22)
            img.paste(shot_res, (card_x, card_y), shot_res)
            
            # Animate mouse pointer moving towards FlexDown button in top right!
            p_prog = min(1.0, (t - 12.26) / 2.5)
            mx = int(card_x + 200 + p_prog * (card_w - 300))
            my = int(card_y + 400 - p_prog * 330)
            
            # Draw cursor
            draw.polygon([(mx, my), (mx + 22, my + 14), (mx + 12, my + 24)], fill=(255, 255, 255), outline=(0, 0, 0))
            if p_prog >= 0.9:
                # Click ripple
                draw.ellipse([mx - 18, my - 18, mx + 18, my + 18], outline=(236, 72, 153), width=3)
                
            badge_txt = "👉 Hovering over TikTok: FlexDown Button Detected!"
            draw_rounded(draw, (card_x, card_y + shot_h + 30, card_x + card_w, card_y + shot_h + 100), fill=(24, 30, 52), outline=(56, 189, 248), width=2, radius=16)
            draw.text((WIDTH//2, card_y + shot_h + 65), badge_txt, fill=(56, 189, 248), font=font_badge, anchor="mm")
        else:
            # Shot 2: The actual menu opened!
            shot = img_tiktok_menu
            shot_ratio = card_w / shot.width
            shot_h = int(shot.height * shot_ratio)
            shot_res = shot.resize((card_w, shot_h), Image.Resampling.LANCZOS)
            
            draw_rounded(draw, (card_x - 6, card_y - 6, card_x + card_w + 6, card_y + shot_h + 6), fill=None, outline=(236, 72, 153), width=3, radius=22)
            img.paste(shot_res, (card_x, card_y), shot_res)
            
            # Highlight 1080p and 320k
            badge_txt = "✨ 1080p Full HD & 320k MP3 saved in 2 seconds!"
            draw_rounded(draw, (card_x, card_y + shot_h + 30, card_x + card_w, card_y + shot_h + 100), fill=(24, 30, 52), outline=(16, 185, 129), width=2, radius=16)
            draw.text((WIDTH//2, card_y + shot_h + 65), badge_txt, fill=(16, 185, 129), font=font_badge, anchor="mm")
            
        # Caption
        caption = "Download TikTok videos without watermark in Full HD!"
        draw_rounded(draw, (70, 1420, WIDTH - 70, 1520), fill=(15, 23, 42, 240), outline=(236, 72, 153), width=2, radius=22)
        draw.text((WIDTH//2, 1470), caption, fill=(251, 191, 36), font=font_caption, anchor="mm")

    # -------------------------------------------------------------
    # SCENE 4: REAL DESKTOP APP FOOTAGE (18.2s - 25.5s)
    # -------------------------------------------------------------
    elif t < 25.5:
        img = get_bg(f, theme="navy")
        draw = ImageDraw.Draw(img)
        
        # Top pill
        draw_rounded(draw, (WIDTH//2 - 220, 80, WIDTH//2 + 220, 140), fill=(24, 30, 48), outline=(239, 68, 68), width=2, radius=16)
        draw.text((WIDTH//2, 110), "📺 YOUTUBE 4K & MP3 CONVERTER", fill=(255, 255, 255), font=font_badge, anchor="mm")
        
        draw.text((WIDTH//2, 220), "REAL DESKTOP APP", fill=(56, 189, 248), font=font_title, anchor="mm")
        draw.text((WIDTH//2, 280), "Ultra HD 4K, 8K & 320k MP3 Studio Audio", fill=(255, 255, 255), font=font_subtitle, anchor="mm")
        
        # Display User's Real App Dialog screenshot
        shot = img_app_dialog
        card_w = 980
        shot_ratio = card_w / shot.width
        shot_h = int(shot.height * shot_ratio)
        shot_res = shot.resize((card_w, shot_h), Image.Resampling.LANCZOS)
        
        card_x = WIDTH//2 - card_w//2
        card_y = 350
        
        # Glowing border around real desktop dialog
        draw_rounded(draw, (card_x - 6, card_y - 6, card_x + card_w + 6, card_y + shot_h + 6), fill=None, outline=(56, 189, 248), width=3, radius=22)
        img.paste(shot_res, (card_x, card_y), shot_res)
        
        # Two value tags under the real app screenshot
        draw_rounded(draw, (card_x, card_y + shot_h + 30, WIDTH//2 - 15, card_y + shot_h + 115), fill=(24, 30, 52), outline=(239, 68, 68), width=2, radius=16)
        draw.text(((card_x + WIDTH//2 - 15)//2, card_y + shot_h + 60), "📺 4K & 8K ULTRA HD", fill=(255, 255, 255), font=font_badge, anchor="mm")
        draw.text(((card_x + WIDTH//2 - 15)//2, card_y + shot_h + 90), "Complete Playlists in 1 Click", fill=(148, 163, 184), font=font_card_sub, anchor="mm")
        
        draw_rounded(draw, (WIDTH//2 + 15, card_y + shot_h + 30, card_x + card_w, card_y + shot_h + 115), fill=(24, 30, 52), outline=(168, 85, 247), width=2, radius=16)
        draw.text(((WIDTH//2 + 15 + card_x + card_w)//2, card_y + shot_h + 60), "🎵 320kbps STUDIO MP3", fill=(255, 255, 255), font=font_badge, anchor="mm")
        draw.text(((WIDTH//2 + 15 + card_x + card_w)//2, card_y + shot_h + 90), "Crystal-Clear Music Extraction", fill=(148, 163, 184), font=font_card_sub, anchor="mm")
        
        # Caption
        if t < 21.0:
            caption = "Grab YouTube 4K videos, playlists..."
        else:
            caption = "...or extract crystal-clear 320k MP3 in 1 click!"
        draw_rounded(draw, (70, 1420, WIDTH - 70, 1520), fill=(15, 23, 42, 240), outline=(56, 189, 248), width=2, radius=22)
        draw.text((WIDTH//2, 1470), caption, fill=(251, 191, 36), font=font_caption, anchor="mm")

    # -------------------------------------------------------------
    # SCENE 5: Safe & Portable & 500% Speed (25.5s - 30.76s)
    # -------------------------------------------------------------
    elif t < 30.76:
        img = get_bg(f, theme="navy")
        draw = ImageDraw.Draw(img)
        
        # Top pill
        draw_rounded(draw, (WIDTH//2 - 210, 80, WIDTH//2 + 210, 140), fill=(24, 30, 48), outline=(16, 185, 129), width=2, radius=16)
        draw.text((WIDTH//2, 110), "🛡️ 100% VERIFIED VIRUS-FREE", fill=(16, 185, 129), font=font_badge, anchor="mm")
        
        draw.text((WIDTH//2, 230), "WHY USERS LOVE IT", fill=(56, 189, 248), font=font_title, anchor="mm")
        draw.text((WIDTH//2, 300), "BUILT FOR WINDOWS 10 & 11", fill=(255, 255, 255), font=font_hero, anchor="mm")
        
        cards = [
            ("🚀  500% Download Acceleration", "Multi-thread split engine maximizes bandwidth speed", 450, (56, 189, 248)),
            ("💾  100% Portable Package", "No complex installation • Run directly from Desktop or USB", 650, (16, 185, 129)),
            ("🔒  Military Grade AES-256 Privacy", "Password-protect and encrypt downloads with one toggle", 850, (236, 72, 153)),
            ("🚫  Zero Popups • Zero Spyware", "100% clean and transparent code for daily workflow", 1050, (251, 191, 36)),
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
    # SCENE 6 & 7: High Converting Offer & CTA (30.76s - 38.06s)
    # -------------------------------------------------------------
    else:
        img = get_bg(f, theme="navy")
        draw = ImageDraw.Draw(img)
        
        # Top pill
        draw_rounded(draw, (WIDTH//2 - 210, 80, WIDTH//2 + 210, 140), fill=(24, 30, 48), outline=(251, 191, 36), width=2, radius=16)
        draw.text((WIDTH//2, 110), "🔥 SPECIAL LAUNCH OFFER 🔥", fill=(251, 191, 36), font=font_badge, anchor="mm")
        
        draw.text((WIDTH//2, 230), "GET YOUR LIFETIME COPY", fill=(56, 189, 248), font=font_title, anchor="mm")
        draw.text((WIDTH//2, 300), "FLEXDOWN PRO", fill=(255, 255, 255), font=font_hero, anchor="mm")
        
        # Giant Golden Offer Box
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
        
        # Warm electronic kick
        kick = math.sin(2 * math.pi * (110 * (1 - b_phase * 0.75)) * b_phase) * math.exp(-b_phase * 7) if b_phase < 0.25 else 0
        
        # Crisp hi-hat
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

print("Encoding Master Real Footage MP4 Video...")
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
print(f"REAL FOOTAGE MASTER VIDEO CREATED AT: {FINAL_VIDEO}")

# Clean up frames
for f in os.listdir(OUTPUT_DIR):
    try:
        os.remove(os.path.join(OUTPUT_DIR, f))
    except Exception:
        pass
try:
    os.rmdir(OUTPUT_DIR)
    os.remove(MIXED_AUDIO)
except Exception:
    pass
