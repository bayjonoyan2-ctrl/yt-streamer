import os
import urllib.request
import json
from datetime import datetime, timezone
import sys

GH_TOKEN = os.environ.get("GH_TOKEN")
REPO = "bayjonoyan2-ctrl/yt-streamer" 

if not os.path.exists("schedule.txt"):
    print("No schedule.txt found.")
    sys.exit(0)

with open("schedule.txt", "r") as f:
    start_at_str = f.read().strip()

if not start_at_str:
    print("Schedule is empty. Nothing to trigger.")
    sys.exit(0)

start_at = datetime.strptime(start_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
now = datetime.now(timezone.utc)

if now >= start_at:
    print("🚀 Time reached! Triggering BOTH stream workflows...")
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/main.yml/dispatches"
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {GH_TOKEN}", "X-GitHub-Api-Version": "2022-11-28"}
    
    # Trigger Horizontal
    data_h = json.dumps({"ref": "main", "inputs": {"action": "Stream Horizontal", "start_offset": "0"}}).encode("utf-8")
    req_h = urllib.request.Request(url, data=data_h, headers=headers, method="POST")
    urllib.request.urlopen(req_h)
    
    # Trigger Vertical
    data_v = json.dumps({"ref": "main", "inputs": {"action": "Stream Vertical", "start_offset": "0"}}).encode("utf-8")
    req_v = urllib.request.Request(url, data=data_v, headers=headers, method="POST")
    urllib.request.urlopen(req_v)
    
    print("✅ Both streams triggered.")
    
    # Clear the file so it doesn't trigger again
    open("schedule.txt", "w").write("")
    os.system('git config user.name "GitHub Action"')
    os.system('git config user.email "action@github.com"')
    os.system('git add schedule.txt')
    os.system('git commit -m "Clear schedule after start"')
    os.system('git push')
else:
    mins = (start_at - now).total_seconds() / 60.0
    print(f"⏳ Not yet. {mins:.0f} minutes remaining until streams start.")
