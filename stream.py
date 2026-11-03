import subprocess
import time
import os
import re
import sys
import urllib.request
import json

INPUT_FILE = "final_video.mp4"
YOUTUBE_STREAM_KEY = os.environ.get("YOUTUBE_STREAM_KEY")
GH_TOKEN = os.environ.get("GH_TOKEN")
START_OFFSET = os.environ.get("START_OFFSET", "0")

if not YOUTUBE_STREAM_KEY:
    print("Missing stream key.")
    sys.exit(1)

RTMP_URL = f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_STREAM_KEY}"
STREAM_LIMIT_SECONDS = 3 * 3600 + 30 * 60
TRIGGER_AT_SECONDS = 3 * 3600

# Automatically detect if this is the vertical stream
IS_VERTICAL = "VERTICAL" in sys.argv or os.environ.get("YOUTUBE_STREAM_KEY_VERTICAL") == YOUTUBE_STREAM_KEY

def get_duration(filename):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try: return float(result.stdout.strip())
    except ValueError: return 0.0

def trigger_next_workflow(start_offset):
    print(f"\n🚀 Triggering NEXT {'Vertical' if IS_VERTICAL else 'Horizontal'} workflow...")
    url = "https://api.github.com/repos/bayjonoyan2-ctrl/yt-streamer/actions/workflows/main.yml/dispatches"
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {GH_TOKEN}", "X-GitHub-Api-Version": "2022-11-28"}
    next_offset = str(int(start_offset + STREAM_LIMIT_SECONDS))
    action_name = "Stream Vertical" if IS_VERTICAL else "Stream Horizontal"
    
    data = json.dumps({"ref": "main", "inputs": {"action": action_name, "start_offset": next_offset}}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            print(f"✅ Next workflow triggered! Status: {response.status}")
    except Exception as e:
        print(f"❌ Failed to trigger: {e}")

def stream():
    total_duration = get_duration(INPUT_FILE)
    if total_duration == 0: return

    seek_offset = float(START_OFFSET)
    
    while seek_offset < total_duration:
        print(f"\n🚀 Starting {'VERTICAL' if IS_VERTICAL else 'HORIZONTAL'} stream from: {seek_offset:.2f}s")
        remaining_video = total_duration - seek_offset
        max_run_time = min(STREAM_LIMIT_SECONDS, remaining_video)

        cmd = [
            "ffmpeg", "-re",
            "-ss", str(seek_offset), 
            "-i", INPUT_FILE,
            "-t", str(max_run_time), 
            "-c:v", "libx264", 
            "-preset", "ultrafast", 
            "-tune", "zerolatency",
            "-b:v", "12M", "-maxrate", "12M", "-bufsize", "24M",
            "-pix_fmt", "yuv420p", 
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-f", "flv", 
            RTMP_URL
        ]

        if IS_VERTICAL:
            filter_complex = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5,eq=brightness=-0.2:saturation=1.2[bg];"
                "[0:v]crop=1420:920:0:45,scale=1080:-2[game];"
                "[0:v]crop=360:320:1550:650,scale=800:-2[cam];"
                "[bg][cam]overlay=(W-w)/2:150[bg_cam];"
                "[bg_cam][game]overlay=0:950[out]"
            )
            cmd.insert(cmd.index("-c:v"), "-filter_complex")
            cmd.insert(cmd.index("-c:v"), filter_complex)
            cmd.insert(cmd.index("-c:v"), "-map")
            cmd.insert(cmd.index("-c:v"), "[out]")

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        start_time = time.time()
        triggered = False
        last_time = 0.0
        stall_count = 0

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
                    stall_count = 0
                else:
                    stall_count += 1

                if not triggered and current_time >= TRIGGER_AT_SECONDS and remaining_video > max_run_time:
                    triggered = True
                    trigger_next_workflow(seek_offset)

            if stall_count > 300:
                print("\n⚠️ Stream froze. Restarting...")
                break

        if process.poll() is None: process.kill()
        played_seconds = last_time if last_time > 0 else (time.time() - start_time)
        
        if triggered:
            print(f"⏹️ Reached trigger point. Handing over.")
            break
        else:
            seek_offset += max(1.0, played_seconds - 2.0) 
            print(f"🔄 Stream stopped early. Restarting from {seek_offset:.2f}s...")
            time.sleep(5)
            if seek_offset >= total_duration - 10:
                print("\n✅ Video completely finished!")
                break

if __name__ == "__main__":
    stream()
