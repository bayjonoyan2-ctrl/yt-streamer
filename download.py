import subprocess
import re
import os
import sys

VOD_URL = "https://www.huya.com/video/play/1131138386.html"
PROXY_URL = os.environ.get("PROXY_URL")

if not PROXY_URL:
    print("❌ ERROR: PROXY_URL is missing from GitHub Secrets.")
    sys.exit(1)

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

    # Run download and check the return code
    download_process = subprocess.run([
        "yt-dlp",
        "--add-header", "Referer:https://v.huya.com/",
        "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "--extractor-args", f"generic:proxy={PROXY_URL}",
        "-N", "8",
        "-c",
        "--retries", "infinite",
        "--fragment-retries", "infinite",
        "-o", "final_video.mp4",
        m3u8_url
    ])
    
    # If yt-dlp fails, exit with an error so GitHub knows it failed
    if download_process.returncode != 0:
        print("\n❌ Download failed with errors.")
        sys.exit(1)
        
    print("\n✅ Download finished!")
else:
    print("❌ Could not find m3u8 link.")
    sys.exit(1)
