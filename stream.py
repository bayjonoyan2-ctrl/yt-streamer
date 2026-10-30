import urllib.request
import zipfile
import os

# --- NEW CODE: Download video from GitHub Artifact ---
if not os.path.exists("final_video.mp4"):
    print("Downloading video from GitHub Artifact...")
    # The download link will be provided by the workflow script
    download_url = os.environ.get("VIDEO_ARTIFACT_URL")
    if download_url:
        urllib.request.urlretrieve(download_url, "video_artifact.zip")
        with zipfile.ZipFile("video_artifact.zip", 'r') as zip_ref:
            zip_ref.extractall(".")
        print("✅ Video extracted successfully!")
# -----------------------------------------------------

# (Keep the rest of your stream.py code exactly the same)
