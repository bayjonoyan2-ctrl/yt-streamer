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

# --- 你的完美裁剪坐标 ---
GAME_W = 1420
GAME_H = 920
GAME_X = 0
GAME_Y = 45

CAM_W = 360
CAM_H = 320
CAM_X = 1550
CAM_Y = 650

def get_duration(filename):
    """Get the total length of the video in seconds."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0

def stream():
    # Get video duration (file is already downloaded by GitHub Actions)
    total_duration = get_duration(INPUT_FILE)
    if total_duration == 0:
        print("❌ Could not read video duration. Check if file exists.")
        return

    seek_offset = 0.0
    first_run = True

    while seek_offset < total_duration:
        print(f"\n🚀 Starting PROFESSIONAL portrait stream from: {seek_offset:.2f} seconds")
        
        # 专业布局滤镜 (Portrait Mode)
        filter_complex = (
            # 1. 背景层：将原始视频放大填满 1080x1920，并施加重度模糊
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5,eq=brightness=-0.2:saturation=1.2[bg];"
            
            # 2. 游戏层：裁剪 -> 缩放到1080宽
            f"[0:v]crop={GAME_W}:{GAME_H}:{GAME_X}:{GAME_Y},scale=1080:-2[game];"
            
            # 3. 人脸层：裁剪 -> 缩放到800宽
            f"[0:v]crop={CAM_W}:{CAM_H}:{CAM_X}:{CAM_Y},scale=800:-2[cam];"
            
            # 4. 给人脸加阴影并放置在 Y=150 的位置
            f"color=c=black@0.5:s=800x1000:d=1[shadow_cam];"
            f"[bg][shadow_cam]overlay=(W-w)/2+15:165[bg_shadow1];"
            f"[bg_shadow1][cam]overlay=(W-w)/2:150[bg_cam];"
            
            # 5. 给游戏加阴影并放置在 Y=950 的位置
            f"color=c=black@0.5:s=1080x1000:d=1[shadow_game];"
            f"[bg_cam][shadow_game]overlay=15:965[bg_shadow2];"
            f"[bg_shadow2][game]overlay=0:950[out]"
        )

        cmd = [
            "ffmpeg", "-re",
            "-ss", str(seek_offset), 
            "-i", INPUT_FILE,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a",
            # --- 视频编码设置 (YouTube 1080p60 推荐码率 12Mbps) ---
            "-c:v", "libx264", 
            "-preset", "ultrafast", 
            "-tune", "zerolatency",
            "-b:v", "12M", 
            "-maxrate", "12M", 
            "-bufsize", "24M",
            "-g", "120",
            "-pix_fmt", "yuv420p", 
            # --- 音频设置 ---
            "-c:a", "aac", 
            "-b:a", "192k", 
            "-ar", "48000",
            "-f", "flv", 
            RTMP_URL
        ]

        # 断线重连参数
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
            
            # 提取时间进度
            match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if match:
                h, m, s = match.groups()
                current_time = int(h)*3600 + int(m)*60 + float(s)
                
                if current_time > last_time:
                    last_time = current_time
                    stall_count = 0
                else:
                    stall_count += 1

            # 防卡死机制
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
