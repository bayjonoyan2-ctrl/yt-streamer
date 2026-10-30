import subprocess
import time
import os
import re
import sys

# ================= 配置区 =================
INPUT_FILE = "final_video.mp4"

# Securely grabs the key from GitHub Secrets. Do not put the real key here.
YOUTUBE_STREAM_KEY = os.environ.get("YOUTUBE_STREAM_KEY")

if not YOUTUBE_STREAM_KEY:
    print("❌ ERROR: YOUTUBE_STREAM_KEY is missing. Please add it to GitHub Secrets.")
    sys.exit(1)

RTMP_URL = f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_STREAM_KEY}"
# =========================================

def get_duration(filename):
    """Get the total length of the video in seconds."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0

def stream():
    total_duration = get_duration(INPUT_FILE)
    if total_duration == 0:
        print("❌ Could not read video duration. Check if file exists.")
        return

    seek_offset = 0.0
    first_run = True

    while seek_offset < total_duration:
        print(f"\n🚀 Starting stream from: {seek_offset:.2f} seconds (Remaining: {total_duration - seek_offset:.2f}s)")
        
        # No filters, no cropping. Stream the video exactly as it is.
        cmd = [
            "ffmpeg", "-re",
            "-ss", str(seek_offset), 
            "-i", INPUT_FILE,
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

        # Reconnect parameters if stream drops
        if not first_run:
            print("🔄 Reconnecting...")
            cmd.insert(-1, "-reconnect")
            cmd.insert(-1, "1")
            cmd.insert(-1, "-reconnect_streamed")
            cmd.insert(-1, "1")
            cmd.insert(-1, "-reconnect_delay_max")
            cmd.insert(-1, "5")

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        start_time = time.time()
        stall_count = 0
        last_time = 0.0

        for line in process.stdout:
            if "frame=" in line or "time=" in line:
                sys.stdout.write(line)
                sys.stdout.flush()
            else:
                if "error" in line.lower() or "failed" in line.lower():
                    print(f"\n[FFmpeg] {line.strip()}")
            
            match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if match:
                h, m, s = match.groups()
                current_time = int(h)*3600 + int(m)*60 + float(s)
                
                if current_time > last_time:
                    last_time = current_time
                    stall_count = 0
                else:
                    stall_count += 1

            if stall_count > 10:
                print("\n⚠️ Stream froze (no progress). Restarting...")
                break
                
        if process.poll() is None:
            process.kill()
        
        played_seconds = last_time if last_time > 0 else (time.time() - start_time)
        seek_offset += max(0, played_seconds - 2.0)
        first_run = False

        print(f"⏹️ Stream stopped at {seek_offset:.2f}s. Waiting 5s before resuming...")
        time.sleep(5) 
    
    print("\n✅ Video completely finished!")

if __name__ == "__main__":
    stream()
