import os
import subprocess
from typing import List

COMMON_WECHAT_DIRS = [
    "/sdcard/Tencent/MicroMsg/WeiXin",
    "/sdcard/Android/data/com.tencent.mm/MicroMsg/Download",
    "/sdcard/Android/data/com.tencent.mm/MicroMsg/WeiXin",
]

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm"}


def _adb_ls(path: str) -> List[str]:
    try:
        out = subprocess.check_output(["adb", "shell", "ls", "-1", path], stderr=subprocess.STDOUT, text=True)
        return [line.strip() for line in out.splitlines() if line.strip()]
    except subprocess.CalledProcessError:
        return []


def _adb_pull(remote: str, local: str) -> bool:
    os.makedirs(os.path.dirname(local), exist_ok=True) if os.path.dirname(local) else None
    try:
        subprocess.check_call(["adb", "pull", remote, local], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


def list_wechat_videos(limit: int = 50) -> List[str]:
    results: List[str] = []
    for base in COMMON_WECHAT_DIRS:
        entries = _adb_ls(base)
        for name in entries:
            # Heuristic: videos often end with .mp4 and similar
            _, ext = os.path.splitext(name.lower())
            if ext in VIDEO_EXTS:
                results.append(os.path.join(base, name))
    # Remove duplicates while preserving order
    seen = set()
    deduped = []
    for p in results:
        if p not in seen:
            deduped.append(p)
            seen.add(p)
    return deduped[:limit]


def pull_videos_to(local_dir: str, limit: int = 20) -> List[str]:
    pulled: List[str] = []
    for remote in list_wechat_videos(limit=limit):
        filename = os.path.basename(remote)
        local_path = os.path.join(local_dir, filename)
        if _adb_pull(remote, local_path):
            pulled.append(local_path)
    return pulled