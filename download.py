import subprocess
import re
import os

VOD_URL = "https://www.huya.com/video/play/1130306382.html"
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

    # Correct way to route generic downloads through a proxy rewrite
    subprocess.run([
        "yt-dlp",
        "--add-header", "Referer:https://v.huya.com/",
        "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "--extractor-args", "generic:proxy=https://huya-proxy.bayjonoyan2.workers.dev/?url=",
        "-N", "8",
        "-c",
        "--retries", "infinite",
        "--fragment-retries", "infinite",
        "-o", "final_video.mp4",
        m3u8_url
    ])
    print("\n✅ Download finished!")
else:
    print("❌ Could not find m3u8 link.")
    exit(1)
