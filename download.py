import os
import subprocess
import sys
import re
from datetime import datetime, timedelta, timezone

VOD_URL = os.environ.get("VIDEO_URL")
PROXY_URL = os.environ.get("PROXY_URL")
HORIZONTAL_HOURS = float(os.environ.get("SCHEDULE_HORIZONTAL_HOURS", "0") or "0")
VERTICAL_HOURS = float(os.environ.get("SCHEDULE_VERTICAL_HOURS", "0") or "0")

if not VOD_URL or not PROXY_URL:
    print("❌ Missing VIDEO_URL or PROXY_URL")
    sys.exit(1)

subprocess.run(["pip", "install", "-q", "yt-dlp"])
subprocess.run(["wget", "-q", "-O", "huya_crawler", "https://github.com/hatienl0i2612/huya-crawler/releases/latest/download/huya_crawler-linux-amd64"])
subprocess.run(["chmod", "+x", "huya_crawler"])

result = subprocess.run(['./huya_crawler', '-json', VOD_URL], capture_output=True, text=True)
m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', result.stdout + result.stderr)

if not m3u8_match:
    print("❌ Could not find m3u8 link.")
    sys.exit(1)

m3u8_url = m3u8_match.group(1)
print("✅ Found m3u8 link. Starting download...")

# EXACT WORKING FLAGS + SKIP + FIX
download_process = subprocess.run([
    "yt-dlp", 
    "--add-header", "Referer:https://v.huya.com/",
    "--add-header", "User-Agent:Mozilla/5.0",
    "--extractor-args", f"generic:proxy={PROXY_URL}",
    "-N", "8", "-c", 
    "--fixup", "force", 
    "--skip-unavailable-fragments", # <--- SKIPS THE BROKEN 2-SEC PIECE
    "--retries", "infinite", 
    "--fragment-retries", "infinite",
    "-o", "video.mp4", m3u8_url
])

if download_process.returncode != 0:
    print("❌ Download failed.")
    sys.exit(1)

print("✅ Video downloaded successfully.")

# PRE-RENDER VERTICAL
print("⏳ Pre-rendering vertical video...")
GAME_W, GAME_H, GAME_X, GAME_Y = 1420, 920, 0, 45
CAM_W, CAM_H, CAM_X, CAM_Y = 360, 320, 1550, 650

filter_complex = (
    "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5,eq=brightness=-0.2:saturation=1.2[bg];"
    f"[0:v]crop={GAME_W}:{GAME_H}:{GAME_X}:{GAME_Y},scale=1080:-2[game];"
    f"[0:v]crop={CAM_W}:{CAM_H}:{CAM_X}:{CAM_Y},scale=800:-2[cam];"
    "[bg][cam]overlay=(W-w)/2:150[bg_cam];"
    "[bg_cam][game]overlay=0:950[out]"
)

subprocess.run([
    "ffmpeg", "-y", "-fflags", "+genpts", "-i", "video.mp4",
    "-filter_complex", filter_complex,
    "-map", "[out]", "-map", "0:a",
    "-c:v", "libx264", 
    "-preset", "veryfast",     
    "-b:v", "4M", "-maxrate", "4M", "-bufsize", "8M", 
    "-threads", "4",           
    "-c:a", "aac", "-b:a", "192k",
    "vertical_render.mp4"
], check=True)
print("✅ Vertical video pre-rendered!")

now = datetime.now(timezone.utc)
if HORIZONTAL_HOURS >= 0:
    with open("schedule_horizontal.txt", "w") as f:
        f.write((now + timedelta(hours=HORIZONTAL_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ"))
if VERTICAL_HOURS >= 0:
    with open("schedule_vertical.txt", "w") as f:
        f.write((now + timedelta(hours=VERTICAL_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ"))
