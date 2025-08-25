import argparse
import os
import sys
from typing import Optional

from .config import get_config
from .state import StateStore
from .utils import setup_logger, sha256_file, write_json, is_video_file
from .aistudio import AIStudioClient
from .watcher import DirectoryWatcher
from .adb_pull import pull_videos_to


def _process_video(path: str, cfg, state: StateStore, ai: AIStudioClient, out_dir: str, logger) -> None:
    try:
        if not os.path.isfile(path) or not is_video_file(path):
            return
        file_hash = sha256_file(path)
        if state.has_processed(file_hash):
            logger.info(f"Skip already processed: {path}")
            return
        logger.info(f"Analyzing: {path}")
        analysis = ai.analyze_video(path)
        out_name = os.path.splitext(os.path.basename(path))[0] + ".analysis.json"
        out_path = os.path.join(out_dir, out_name)
        write_json(out_path, analysis)
        state.record_processed(file_hash, path, out_path, analysis)
        logger.info(f"Saved analysis: {out_path}")
    except Exception as exc:
        logger.error(f"Failed processing {path}: {exc}")


def cmd_watch(args: argparse.Namespace) -> int:
    cfg = get_config()
    logger = setup_logger(cfg.log_level)
    state = StateStore(cfg.state_db_path)
    ai = AIStudioClient(cfg.google_api_key, cfg.model_name)
    out_dir = args.out_dir or cfg.output_dir

    def on_video(path: str) -> None:
        _process_video(path, cfg, state, ai, out_dir, logger)

    watcher = DirectoryWatcher(args.watch_dir, on_video)
    logger.info(f"Watching directory: {args.watch_dir}")
    try:
        watcher.start()
        # Keep running until Ctrl+C
        while True:
            pass
    except KeyboardInterrupt:
        logger.info("Stopping watcher...")
        watcher.stop()
    return 0


def cmd_adb_pull(args: argparse.Namespace) -> int:
    cfg = get_config()
    logger = setup_logger(cfg.log_level)
    state = StateStore(cfg.state_db_path)
    ai = AIStudioClient(cfg.google_api_key, cfg.model_name) if args.analyze else None
    out_dir = args.out_dir or cfg.output_dir

    os.makedirs(out_dir, exist_ok=True)
    logger.info("Pulling videos from Android device via ADB...")
    files = pull_videos_to(out_dir, limit=args.limit)
    logger.info(f"Pulled {len(files)} files")

    if args.analyze and ai is not None:
        for f in files:
            _process_video(f, cfg, state, ai, out_dir, logger)
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    cfg = get_config()
    logger = setup_logger(cfg.log_level)
    state = StateStore(cfg.state_db_path)
    ai = AIStudioClient(cfg.google_api_key, cfg.model_name)
    out_dir = args.out_dir or cfg.output_dir
    _process_video(args.file, cfg, state, ai, out_dir, logger)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wechat_video_automation", description="WeChat video → AI Studio automation")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_watch = sub.add_parser("watch", help="Watch a folder for new videos and analyze")
    p_watch.add_argument("--watch-dir", required=True, help="Directory to watch")
    p_watch.add_argument("--out-dir", help="Output directory for analyses")
    p_watch.set_defaults(func=cmd_watch)

    p_adb = sub.add_parser("adb-pull", help="Pull WeChat videos via ADB and optionally analyze")
    p_adb.add_argument("--out-dir", help="Where to store pulled files and analyses")
    p_adb.add_argument("--limit", type=int, default=20, help="Max files to pull")
    p_adb.add_argument("--analyze", action="store_true", help="Analyze after pulling")
    p_adb.set_defaults(func=cmd_adb_pull)

    p_an = sub.add_parser("analyze", help="Analyze a single local video file")
    p_an.add_argument("--file", required=True, help="Path to a local video")
    p_an.add_argument("--out-dir", help="Output directory for analyses")
    p_an.set_defaults(func=cmd_analyze)

    return p


def main(argv: Optional[list] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)