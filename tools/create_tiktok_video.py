import os
import math
import struct
import wave
import subprocess
from PIL import Image, ImageDraw, ImageFont

# Video Settings
WIDTH, HEIGHT = 1080, 1920
FPS = 30
DURATION_SEC = 27.0
TOTAL_FRAMES = int(FPS * DURATION_SEC)

# Paths
BASE_DIR = r"C:\Users\abdra\.gemini\antigravity\scratch\FlexDown"
OUTPUT_DIR = os.path.join(BASE_DIR, "video_frames")
os.makedirs(OUTPUT_DIR, exist_ok=True)
DESKTOP = r"C:\Users\abdra\OneDrive\Bureau"
FINAL_VIDEO = os.path.join(DESKTOP, "FlexDown_TikTok_Promo.mp4")
FFMPEG = os.path.join(BASE_DIR, "bin", "ffmpeg.exe")

VOICE_FILE = os.path.join(BASE_DIR, "tight_voice.wav")
MUSIC_FILE = os.path.join(BASE_DIR, "bg_music.wav")
MIXED_AUDIO = os.path.join(BASE_DIR, "final_ad_audio.wav")

LOGO_PATH = os.path.join(BASE_DIR, "resources", "icons", "app.png")
logo_img = Image.open(LOGO_PATH).convert("RGBA")

# Fonts
try:
    font_hero = ImageFont.truetype("arialbd.ttf", 74)
    font_title = ImageFont.truetype("arialbd.ttf", 52)
    font_caption = ImageFont.truetype("arialbd.ttf", 46)
    font_bold = ImageFont.truetype("arialbd.ttf", 40)
    font_medium = ImageFont.truetype("arial.ttf", 32)
    font_badge = ImageFont.truetype("arialbd.ttf", 28)
    font_small = ImageFont.truetype("arial.ttf", 24)
except Exception:
    font_hero = ImageFont.load_default()
    font_title = font_hero
    font_caption = font_hero
    font_bold = font_hero
    font_medium = font_hero
    font_badge = font_hero
    font_small = font_hero


def get_background(frame_idx):
    """Deep modern dark mode tech background with moving ambient light glow."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (10, 15, 29))
    draw = ImageDraw.Draw(img)
    # Gradient base
    for y in range(0, HEIGHT, 6):
        ratio = y / HEIGHT
        r = int(10 + ratio * 15)
        g = int(15 + ratio * 22)
        b = int(29 + ratio * 45)
        draw.rectangle([(0, y), (WIDTH, y + 6)], fill=(r, g, b))

    # Ambient neon glows
    glow_x = int(WIDTH * 0.5 + 200 * math.sin(frame_idx * 0.03))
    glow_y = int(HEIGHT * 0.4 + 150 * math.cos(frame_idx * 0.03))
    # Radial glow representation
    draw.ellipse([glow_x - 300, glow_y - 300, glow_x + 300, glow_y + 300], fill=(20, 30, 60))
    return img


def draw_rounded_card(draw, xy, fill, outline=None, width=1, radius=22):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=width)


print(f"Rendering {TOTAL_FRAMES} frames for ultra-high conversion ad...")

# Subtitle / Voice timing script:
# 0.0 - 3.8s: "Stop using sketchy websites full of fake download buttons and malware."
# 3.8 - 6.8s: "And stop risking your PC with broken IDM cracks."
# 6.8 - 11.2s: "Meet FlexDown. The fastest, cleanest media downloader built for Windows."
# 11.2 - 15.5s: "Download TikTok videos without watermark in full HD."
# 15.5 - 20.0s: "Grab YouTube videos, playlists, or extract crystal-clear 320k MP3 audio."
# 20.0 - 23.5s: "It is portable, zero ads, and five times faster."
# 23.5 - 27.0s: "Get your lifetime license today. Tap the link in bio to get FlexDown now."

for f in range(TOTAL_FRAMES):
    t = f / FPS
    img = get_background(f)
    draw = ImageDraw.Draw(img)

    # Top Brand Bar
    draw_rounded_card(draw, (WIDTH // 2 - 200, 90, WIDTH // 2 + 200, 150), fill=(22, 33, 62, 200), outline=(56, 189, 248), width=2, radius=18)
    draw.text((WIDTH // 2, 120), "⚡ FLEXDOWN DOWNLOADER", fill=(255, 255, 255), font=font_badge, anchor="mm")

    # -------------------------------------------------------------------------
    # SCENE 1 (0.0s - 6.8s): The Problem / Hook (High Curiosity)
    # -------------------------------------------------------------------------
    if t < 6.8:
        # Warning badge
        draw_rounded_card(draw, (WIDTH // 2 - 180, 260, WIDTH // 2 + 180, 320), fill=(239, 68, 68, 40), outline=(239, 68, 68), width=2, radius=14)
        draw.text((WIDTH // 2, 290), "⚠️ WARNING TO PC USERS", fill=(248, 113, 113), font=font_badge, anchor="mm")

        draw.text((WIDTH // 2, 390), "STOP USING SHADY WEBSITES", fill=(255, 255, 255), font=font_title, anchor="mm")
        draw.text((WIDTH // 2, 460), "TO DOWNLOAD VIDEOS!", fill=(239, 68, 68), font=font_hero, anchor="mm")

        # Visual Pain Cards
        cards = [
            ("❌  Fake Download Buttons & Pop-up Ads", 600, (239, 68, 68), 0.0),
            ("❌  Dangerous Malware & Spyware", 750, (249, 115, 22), 1.5),
            ("❌  Broken IDM Cracks That Stop Working", 900, (234, 179, 8), 3.5),
            ("❌  Low Quality Videos With Watermarks", 1050, (239, 68, 68), 5.0),
        ]
        for text, cy, color, appear_t in cards:
            if t >= appear_t:
                draw_rounded_card(draw, (70, cy - 50, WIDTH - 70, cy + 50), fill=(26, 34, 52), outline=color, width=2, radius=18)
                draw.text((110, cy), text, fill=(241, 245, 249), font=font_bold, anchor="lm")

        # Subtitle caption box (Hormozi style)
        if t < 3.8:
            caption = "Stop using sketchy websites full of fake buttons!"
        else:
            caption = "Stop risking your PC with broken IDM cracks!"
        draw_rounded_card(draw, (60, 1380, WIDTH - 60, 1480), fill=(15, 23, 42, 230), outline=(56, 189, 248), width=2, radius=20)
        draw.text((WIDTH // 2, 1430), caption, fill=(251, 191, 36), font=font_bold, anchor="mm")

    # -------------------------------------------------------------------------
    # SCENE 2 (6.8s - 11.2s): The Hero / FlexDown Reveal
    # -------------------------------------------------------------------------
    elif t < 11.2:
        # Animated pulsing logo
        logo_scale = 1.0 + 0.06 * math.sin(f * 0.15)
        l_size = int(320 * logo_scale)
        l_img = logo_img.resize((l_size, l_size), Image.Resampling.LANCZOS)
        img.paste(l_img, (WIDTH // 2 - l_size // 2, 340 - (l_size - 320) // 2), l_img)

        draw.text((WIDTH // 2, 730), "MEET FLEXDOWN", fill=(255, 255, 255), font=font_hero, anchor="mm")
        draw.text((WIDTH // 2, 810), "The Fastest, Cleanest Windows Downloader", fill=(56, 189, 248), font=font_title, anchor="mm")

        # 3 Big Value Pillars
        pillars = [
            ("⚡ 5X FASTER MULTI-THREAD ENGINE", 960, (56, 189, 248)),
            ("🛡️ 100% CLEAN • ZERO ADS • NO CRACKS", 1100, (16, 185, 129)),
            ("💻 PORTABLE • RUNS INSTANTLY ON WINDOWS", 1240, (233, 69, 96)),
        ]
        for p_text, cy, border in pillars:
            draw_rounded_card(draw, (70, cy - 45, WIDTH - 70, cy + 45), fill=(26, 34, 52), outline=border, width=3, radius=18)
            draw.text((WIDTH // 2, cy), p_text, fill=(255, 255, 255), font=font_bold, anchor="mm")

        # Subtitle caption
        draw_rounded_card(draw, (60, 1420, WIDTH - 60, 1510), fill=(15, 23, 42, 230), outline=(56, 189, 248), width=2, radius=20)
        draw.text((WIDTH // 2, 1465), "The fastest, cleanest media downloader for PC", fill=(251, 191, 36), font=font_bold, anchor="mm")

    # -------------------------------------------------------------------------
    # SCENE 3 (11.2s - 20.0s): Features (TikTok, MP3, 1-Click)
    # -------------------------------------------------------------------------
    elif t < 20.0:
        draw.text((WIDTH // 2, 260), "POWERFUL FEATURES", fill=(56, 189, 248), font=font_title, anchor="mm")
        draw.text((WIDTH // 2, 330), "BUILT FOR CREATORS & USERS", fill=(255, 255, 255), font=font_hero, anchor="mm")

        feats = [
            ("🎬 TikTok WITHOUT Watermark", "Full HD video saved in 2 seconds to PC", 480, (236, 72, 153), 11.2),
            ("🌐 1-Click Floating Download Badge", "Hovers on YouTube, TikTok, Facebook & X", 680, (59, 130, 246), 13.0),
            ("🎵 320kbps Studio MP3 Audio", "Extract highest quality music & podcasts", 880, (168, 85, 247), 15.5),
            ("🔒 AES-256 Military Encryption", "Keep your downloaded files 100% private", 1080, (16, 185, 129), 17.5),
        ]
        for title, sub, cy, accent, app_t in feats:
            active = t >= app_t
            fill_col = (30, 41, 59) if active else (20, 26, 38)
            out_col = accent if active else (50, 60, 80)
            draw_rounded_card(draw, (70, cy - 65, WIDTH - 70, cy + 65), fill=fill_col, outline=out_col, width=2 if active else 1, radius=18)
            draw.text((110, cy - 18), title, fill=(255, 255, 255) if active else (148, 163, 184), font=font_bold, anchor="lm")
            draw.text((110, cy + 26), sub, fill=(148, 163, 184) if active else (100, 116, 139), font=font_medium, anchor="lm")

        # Dynamic Hormozi captions
        if t < 15.5:
            caption = "Download any TikTok video without watermark in Full HD!"
        elif t < 18.0:
            caption = "Extract crystal-clear 320k MP3 audio in seconds!"
        else:
            caption = "It is portable, zero ads, and five times faster!"
        draw_rounded_card(draw, (60, 1360, WIDTH - 60, 1460), fill=(15, 23, 42, 230), outline=(56, 189, 248), width=2, radius=20)
        draw.text((WIDTH // 2, 1410), caption, fill=(251, 191, 36), font=font_bold, anchor="mm")

    # -------------------------------------------------------------------------
    # SCENE 4 (20.0s - 27.0s): High-Converting Offer & CTA
    # -------------------------------------------------------------------------
    else:
        draw.text((WIDTH // 2, 270), "SPECIAL LAUNCH OFFER", fill=(56, 189, 248), font=font_title, anchor="mm")
        draw.text((WIDTH // 2, 350), "GET YOUR LIFETIME COPY", fill=(255, 255, 255), font=font_hero, anchor="mm")

        # Huge Offer Box
        draw_rounded_card(draw, (90, 460, WIDTH - 90, 780), fill=(30, 41, 59), outline=(233, 69, 96), width=4, radius=28)
        draw.text((WIDTH // 2, 530), "⭐ LIFETIME ACCESS ⭐", fill=(251, 191, 36), font=font_bold, anchor="mm")
        draw.text((WIDTH // 2, 630), "$10 ONLY", fill=(255, 255, 255), font=font_hero, anchor="mm")
        draw.text((WIDTH // 2, 715), "No monthly subscriptions • All updates free forever", fill=(148, 163, 184), font=font_medium, anchor="mm")

        # Animated Glowing CTA Button
        btn_y = 960
        pulse = 14 * math.sin(f * 0.28)
        draw_rounded_card(draw, (100 - int(pulse), btn_y - 65, WIDTH - 100 + int(pulse), btn_y + 65), fill=(233, 69, 96), radius=36)
        draw.text((WIDTH // 2, btn_y), "👉 TAP LINK IN BIO TO DOWNLOAD", fill=(255, 255, 255), font=font_bold, anchor="mm")

        # Store URL Box
        draw_rounded_card(draw, (110, 1140, WIDTH - 110, 1260), fill=(15, 23, 42), outline=(56, 189, 248), width=2, radius=18)
        draw.text((WIDTH // 2, 1200), "abdoubelkhiria.gumroad.com/l/zgntp", fill=(56, 189, 248), font=font_bold, anchor="mm")

        draw.text((WIDTH // 2, 1380), "Instant Download • Windows 10 & 11 • 100% Virus-Free", fill=(203, 213, 225), font=font_medium, anchor="mm")

    frame_path = os.path.join(OUTPUT_DIR, f"frame_{f:04d}.png")
    img.save(frame_path)
    if (f + 1) % 120 == 0 or f == TOTAL_FRAMES - 1:
        print(f"Rendered {f + 1}/{TOTAL_FRAMES} frames ({(f + 1) / TOTAL_FRAMES * 100:.1f}%)")

print("Synthesizing energetic tech background music...")
sample_rate = 44100
total_samples = int(sample_rate * DURATION_SEC)
with wave.open(MUSIC_FILE, "w") as wav:
    wav.setnchannels(2)
    wav.setsampwidth(2)
    wav.setframerate(sample_rate)
    frames_bytes = bytearray()
    for i in range(total_samples):
        t_sec = i / sample_rate
        # Modern 124 BPM tech beat
        bpm = 124.0
        beat_interval = 60.0 / bpm
        b_phase = (t_sec % beat_interval) / beat_interval

        # Deep sub-kick
        kick = math.sin(2 * math.pi * (130 * (1 - b_phase * 0.8)) * b_phase) * math.exp(-b_phase * 8) if b_phase < 0.3 else 0
        # Crisp hi-hat on 16th notes
        sixteenth = ((t_sec % (beat_interval / 4)) / (beat_interval / 4))
        hihat = 0.15 * math.sin(2 * math.pi * 9500 * sixteenth) * math.exp(-sixteenth * 30) if sixteenth < 0.1 else 0
        # Ambient bassline chord progression
        chords = [55, 65.4, 73.4, 82.4]  # A1, C2, D2, E2
        chord_note = chords[int(t_sec / 2) % len(chords)]
        sub_bass = 0.3 * math.sin(2 * math.pi * chord_note * t_sec)

        val = max(-1.0, min(1.0, (kick * 0.5 + hihat * 0.25 + sub_bass * 0.35)))
        sample_int = int(val * 9000)  # Gentle background level (-14dB)
        frames_bytes.extend(struct.pack("<hh", sample_int, sample_int))
    wav.writeframes(frames_bytes)

print("Mixing Neural Voiceover with Background Music...")
mix_cmd = [
    FFMPEG,
    "-y",
    "-i", VOICE_FILE,
    "-i", MUSIC_FILE,
    "-filter_complex",
    "[0:a]volume=2.4,aformat=sample_rates=44100:channel_layouts=stereo[v];[1:a]volume=0.28[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2[aout]",
    "-map", "[aout]",
    "-c:a", "pcm_s16le",
    MIXED_AUDIO
]
subprocess.run(mix_cmd, check=True)

print("Encoding master MP4 video...")
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
print(f"MASTER PROMO VIDEO READY AT: {FINAL_VIDEO}")

# Clean up
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
