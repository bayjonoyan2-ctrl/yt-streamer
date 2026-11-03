import subprocess
import time
import os
import re
import sys
import urllib.request
import json

INPUT_FILE = "video.mp4"
YOUTUBE_STREAM_KEY = os.environ.get("YOUTUBE_STREAM_KEY")
GH_TOKEN = os.environ.get("GH_TOKEN")
REPO = os.environ.get("REPO", "")
START_OFFSET = os.environ.get("START_OFFSET", "0")

if not YOUTUBE_STREAM_KEY or not GH_TOKEN:
    print("❌ ERROR: Missing YOUTUBE_STREAM_KEY or GH_TOKEN.")
    sys.exit(1)

RTMP_URL = f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_STREAM_KEY}"

TRIGGER_AT_SECONDS = 3 * 3600
HANDOVER_AT_SECONDS = 3 * 3600 + 30 * 60

def get_duration(filename):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try: return float(result.stdout.strip())
    except ValueError: return 0.0

def trigger_next(start_offset):
    print(f"\n🚀 Triggering next Horizontal stream from {start_offset:.0f}s...")
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/stream_horizontal.yml/dispatches"
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {GH_TOKEN}", "X-GitHub-Api-Version": "2022-11-28"}
    data = json.dumps({"ref": "main", "inputs": {"start_offset": str(int(start_offset))}}).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            print(f"✅ Next workflow triggered ({r.status})")
    except Exception as e:
        print(f"❌ Trigger failed: {e}")

def stream():
    total_duration = get_duration(INPUT_FILE)
    if total_duration == 0: return

    seek_offset = float(START_OFFSET)
    if seek_offset > 0:
        print("⏳ Handover detected. Waiting 15 minutes for old stream to finish...")
        time.sleep(15 * 60)

    while seek_offset < total_duration:
        print(f"\n🚀 Starting HORIZONTAL stream from: {seek_offset:.2f}s")
        remaining_video = total_duration - seek_offset
        max_run_time = min(HANDOVER_AT_SECONDS, remaining_video)

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
            "-f", "flv", RTMP_URL
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        start_time = time.time()
        triggered = False
        last_time = 0.0
        stall_count = 0

        for line in process.stdout:
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

                if not triggered and current_time >= TRIGGER_AT_SECONDS and remaining_video > max_run_time and current_time > 600:
                    triggered = True
                    trigger_next(seek_offset + TRIGGER_AT_SECONDS)

            if stall_count > 300:
                print("\n⚠️ Stream froze. Restarting...")
                break

        if process.poll() is None: process.kill()
        played_seconds = last_time if last_time > 0 else (time.time() - start_time)
        
        if triggered:
            print(f"⏹️ Handover at {seek_offset + played_seconds:.2f}s")
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
