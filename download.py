import subprocess
import re
import os
import sys

# Grab the URL and Proxy from GitHub Actions environment variables
VOD_URL = os.environ.get("VOD_URL")
PROXY_URL = os.environ.get("PROXY_URL")

if not VOD_URL:
    print("❌ ERROR: VOD_URL is missing.")
    sys.exit(1)
    
if not PROXY_URL:
    print("❌ ERROR: PROXY_URL is missing from GitHub Secrets.")
    sys.exit(1)

print(f"Starting download for: {VOD_URL}")
print("Installing yt-dlp and downloading crawler...")

subprocess.run(["pip", "install", "-q", "yt-dlp"])

subprocess.run(["wget", "-q", "-O", "huya_crawler", "https://github.com/hatienl0i2612/huya-crawler/releases/latest/download/huya_crawler-linux-amd64"])
subprocess.run(["chmod", "+x", "huya_crawler"])

print("Extracting m3u8 link...")
result = subprocess.run(['./huya_crawler', '-json', VOD_URL], capture_output=True, text=True)
output_text = result.stdout + result.stderr
m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', output_text)

if m3u8_match:
    m3u8_url = m3u8_match.group(1)
    print(f"✅ Found m3u8 link. Starting download via Cloudflare Proxy...")

    download_process = subprocess.run([
        "yt-dlp",
        "--add-header", "Referer:https://v.huya.com/",
        "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "--extractor-args", f"generic:proxy={PROXY_URL}",
        "-N", "8",
        "-c",
        "--fixup", "force", # Fixes the broken timestamps
        "--retries", "infinite",
        "--fragment-retries", "infinite",
        "-o", "final_video.mp4",
        m3u8_url
    ])
    
    if download_process.returncode != 0:
        print("\n❌ Download failed with errors.")
        sys.exit(1)
        
    print("\n✅ Download finished!")
else:
    print("❌ Could not find m3u8 link.")
    sys.exit(1)
