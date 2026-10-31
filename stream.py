import subprocess
import time
import os
import re
import sys
import urllib.request
import json

# ================= 配置区 =================
INPUT_FILE = "final_video.mp4"

YOUTUBE_STREAM_KEY = os.environ.get("YOUTUBE_STREAM_KEY")
GH_TOKEN = os.environ.get("GH_TOKEN") # The new GitHub token

if not YOUTUBE_STREAM_KEY or not GH_TOKEN:
    print("❌ ERROR: Missing YOUTUBE_STREAM_KEY or GH_TOKEN in GitHub Secrets.")
    sys.exit(1)

RTMP_URL = f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_STREAM_KEY}"

# --- Trigger Settings ---
# Change these if you want shorter/longer runs
STREAM_LIMIT_SECONDS = 3 * 3600 + 30 * 60  # 3 hours and 30 minutes
TRIGGER_AT_SECONDS = 3 * 3600 + 10 * 60    # 3 hours and 10 minutes (20 mins before limit)
# =========================================

def get_duration(filename):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0

def trigger_next_workflow():
    print("\n🚀 Triggering NEXT GitHub Action to download and wait...")
    url = "https://api.github.com/repos/bayjonoyan2-ctrl/yt-streamer/actions/workflows/main.yml/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GH_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = json.dumps({"ref": "main", "inputs": {"action": "Stream"}}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"✅ Next workflow triggered! Status: {response.status}")
    except Exception as e:
        print(f"❌ Failed to trigger next workflow: {e}")

def stream():
    total_duration = get_duration(INPUT_FILE)
    if total_duration == 0:
        print("❌ Could not read video duration. Check if file exists.")
        return

    # Check if we are resuming from a previous chunk
    seek_offset = float(os.environ.get("START_OFFSET", "0.0"))
    
    while seek_offset < total_duration:
        print(f"\n🚀 Starting stream from: {seek_offset:.2f} seconds")
        
        # Calculate how long this run is allowed to stream
        remaining_video = total_duration - seek_offset
        max_run_time = min(STREAM_LIMIT_SECONDS, remaining_video)
        
        # We must tell ffmpeg to stop at max_run_time using -t
        cmd = [
            "ffmpeg", "-re",
            "-ss", str(seek_offset), 
            "-i", INPUT_FILE,
            "-t", str(max_run_time), # Stop ffmpeg after this many seconds
            # --- High Quality 1080p 60fps Encoding ---
            "-c:v", "libx264", 
            "-preset", "ultrafast", 
            "-tune", "zerolatency",
            "-b:v", "12M", 
            "-maxrate", "12M", 
            "-bufsize", "24M",
            "-pix_fmt", "yuv420p", 
            # --- Audio Settings ---
            "-c:a", "aac", 
            "-b:a", "192k", 
            "-ar", "48000",
            "-f", "flv", 
            RTMP_URL
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        triggered = False
        last_time = 0.0

        for line in process.stdout:
            if "frame=" in line or "time=" in line:
                sys.stdout.write(line)
                sys.stdout.flush()
            
            match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if match:
                h, m, s = match.groups()
                current_time = int(h)*3600 + int(m)*60 + float(s)
                
                if current_time > last_time:
                    last_time = current_time

                # Check if we need to trigger the next workflow
                if not triggered and current_time >= TRIGGER_AT_SECONDS and remaining_video > max_run_time:
                    triggered = True
                    trigger_next_workflow()

        if process.poll() is None:
            process.kill()
        
        # Move to the next part of the video
        seek_offset += last_time
        
        # If we hit the end of the video, stop
        if seek_offset >= total_duration - 10: # 10 seconds buffer
            print("\n✅ Video completely finished!")
            break
        else:
            print(f"⏹️ Finished chunk. Next workflow is taking over at {seek_offset}s...")
            # We do NOT loop here anymore. The new workflow will take over.
            # We exit this script so the server can shut down.
            break 

if __name__ == "__main__":
    stream()
