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

print(f"Downloading from Huya: {VOD_URL}")

# Install tools
subprocess.run(["pip", "install", "-q", "yt-dlp"])
subprocess.run(["wget", "-q", "-O", "huya_crawler", "https://github.com/hatienl0i2612/huya-crawler/releases/latest/download/huya_crawler-linux-amd64"])
subprocess.run(["chmod", "+x", "huya_crawler"])

# Extract m3u8
result = subprocess.run(['./huya_crawler', '-json', VOD_URL], capture_output=True, text=True)
m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', result.stdout + result.stderr)

if not m3u8_match:
    print("❌ Could not find m3u8 link.")
    sys.exit(1)

m3u8_url = m3u8_match.group(1)
print("✅ Found m3u8 link. Starting download...")

download_process = subprocess.run([
    "yt-dlp", 
    "--add-header", "Referer:https://v.huya.com/",
    "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "--extractor-args", f"generic:proxy={PROXY_URL}",
    "-N", "8", "-c", "--fixup", "force",
    "--retries", "infinite", "--fragment-retries", "infinite",
    "-o", "video.mp4", m3u8_url
])

if download_process.returncode != 0:
    print("❌ Download failed.")
    sys.exit(1)

print("✅ Video downloaded successfully.")

# Write schedules
now = datetime.now(timezone.utc)

if HORIZONTAL_HOURS > 0:
    h_at = now + timedelta(hours=HORIZONTAL_HOURS)
    with open("schedule_horizontal.txt", "w") as f:
        f.write(h_at.strftime("%Y-%m-%dT%H:%M:%SZ"))
    print(f"⏰ Horizontal stream scheduled for: {h_at.isoformat()}")

if VERTICAL_HOURS > 0:
    v_at = now + timedelta(hours=VERTICAL_HOURS)
    with open("schedule_vertical.txt", "w") as f:
        f.write(v_at.strftime("%Y-%m-%dT%H:%M:%SZ"))
    print(f"⏰ Vertical stream scheduled for: {v_at.isoformat()}")
