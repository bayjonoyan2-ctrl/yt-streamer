import os
import urllib.request
import json
from datetime import datetime, timezone

GH_TOKEN = os.environ.get("GH_TOKEN")
REPO = "bayjonoyan2-ctrl/yt-streamer" 

# If no schedule file is found, exit gracefully
if not os.path.exists("schedule.txt"):
    print("No schedule.txt found. Exiting.")
    exit(0)

with open("schedule.txt", "r") as f:
    start_at_str = f.read().strip()

start_at = datetime.strptime(start_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
now = datetime.now(timezone.utc)

if now >= start_at:
    print("🚀 Time reached! Triggering Stream workflow...")
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/main.yml/dispatches"
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {GH_TOKEN}", "X-GitHub-Api-Version": "2022-11-28"}
    data = json.dumps({"ref": "main", "inputs": {"action": "Stream", "start_offset": "0"}}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    urllib.request.urlopen(req)
    
    # Rename the file so it doesn't trigger again
    os.rename("schedule.txt", "schedule_done.txt")
else:
    mins = (start_at - now).total_seconds() / 60.0
    print(f"⏳ Not yet. {mins:.0f} minutes remaining.")
