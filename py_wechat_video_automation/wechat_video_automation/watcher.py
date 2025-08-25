import os
from typing import Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class _VideoEventHandler(FileSystemEventHandler):
    def __init__(self, on_video: Callable[[str], None]) -> None:
        super().__init__()
        self.on_video = on_video

    def on_created(self, event):
        if event.is_directory:
            return
        path = event.src_path
        _, ext = os.path.splitext(path.lower())
        if ext in {".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm"}:
            self.on_video(path)


class DirectoryWatcher:
    def __init__(self, directory: str, on_video: Callable[[str], None]) -> None:
        self.directory = directory
        self.handler = _VideoEventHandler(on_video)
        self.observer = Observer()

    def start(self) -> None:
        self.observer.schedule(self.handler, path=self.directory, recursive=True)
        self.observer.start()

    def stop(self) -> None:
        self.observer.stop()
        self.observer.join()