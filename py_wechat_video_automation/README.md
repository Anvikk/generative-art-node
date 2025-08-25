## WeChat Video → AI Studio (Gemini) Automation (Python)

Automates pulling WeChat videos from a local folder or Android ADB, then sends them to Google AI Studio (Gemini) for analysis. Results are saved locally.

### Prerequisites
- Python 3.10+
- A Google AI Studio API key
- Optional: Android with USB debugging + `adb` installed (for phone pulling)

### Install
```bash
cd /workspace/py_wechat_video_automation
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Configure
```bash
cp .env.example .env
# then edit .env and set GOOGLE_API_KEY
```

### Usage
- Show help
```bash
python -m wechat_video_automation --help
```

- Watch a local folder and analyze new videos
```bash
python -m wechat_video_automation watch \
  --watch-dir /path/to/WeChat/Videos \
  --out-dir /workspace/output \
  --analyze
```

- Pull recent WeChat videos from an Android device via ADB and analyze
```bash
python -m wechat_video_automation adb-pull \
  --out-dir /workspace/output \
  --limit 20 \
  --analyze
```

- Analyze a single local video
```bash
python -m wechat_video_automation analyze --file /path/to/video.mp4
```

### Notes
- A small SQLite database prevents reprocessing the same file twice.
- Android paths vary; this tool tries common `MicroMsg`/`WeiXin` locations under `/sdcard`.
- Ensure you have legal rights to process and upload your content.