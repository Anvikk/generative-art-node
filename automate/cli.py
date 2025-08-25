import argparse
import csv
import os
import re
import shutil
import sys
from glob import glob
from pathlib import Path
from typing import Dict, Iterable, List, Set

try:
    import requests
except Exception as import_error:  # pragma: no cover
    requests = None  # type: ignore


def _print(msg: str) -> None:
    sys.stdout.write(msg + "\n")


def _eprint(msg: str) -> None:
    sys.stderr.write(msg + "\n")


def command_organize(directory: str, dry_run: bool) -> None:
    base_path = Path(directory).expanduser().resolve()
    if not base_path.exists() or not base_path.is_dir():
        _eprint(f"Directory not found: {base_path}")
        sys.exit(2)

    files_moved = 0
    for entry in base_path.iterdir():
        if entry.is_file():
            ext = entry.suffix.lower().lstrip(".") or "no_ext"
            target_dir = base_path / ext
            target_dir_relative = f"{ext}/"
            if dry_run:
                _print(f"Would move {entry.name} -> {target_dir_relative}{entry.name}")
            else:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(entry), str(target_dir / entry.name))
                files_moved += 1

    if dry_run:
        _print("Dry run complete.")
    else:
        _print(f"Moved {files_moved} file(s).")


def command_fetch(url: str, out: str | None, timeout: float) -> None:
    if requests is None:
        _eprint("The 'requests' package is required. Run: pip install -r requirements.txt")
        sys.exit(2)

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover
        _eprint(f"Error fetching URL: {exc}")
        sys.exit(1)

    if out:
        out_path = Path(out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(response.content)
        _print(f"Saved to {out_path}")
    else:
        sys.stdout.buffer.write(response.content)


def _read_csv_headers(file_path: Path) -> List[str]:
    with file_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or [])


def _iter_csv_rows(file_path: Path) -> Iterable[Dict[str, str]]:
    with file_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield {k: (v if v is not None else "") for k, v in row.items()}


def command_merge_csv(inputs: List[str], out: str) -> None:
    input_paths: List[Path] = []
    for pattern in inputs:
        matched = [Path(p) for p in glob(pattern)]
        if matched:
            input_paths.extend(matched)
        else:
            # If it's a direct file path that doesn't match glob
            p = Path(pattern)
            if p.exists() and p.is_file():
                input_paths.append(p)

    input_paths = [p.resolve() for p in input_paths if p.exists() and p.is_file()]
    if not input_paths:
        _eprint("No input CSV files found.")
        sys.exit(2)

    # Union of headers across all files
    headers_set: Set[str] = set()
    for path in input_paths:
        headers_set.update(_read_csv_headers(path))
    headers: List[str] = sorted(headers_set)

    out_path = Path(out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=headers)
        writer.writeheader()
        for path in input_paths:
            for row in _iter_csv_rows(path):
                # Ensure all headers are present
                full_row: Dict[str, str] = {h: row.get(h, "") for h in headers}
                writer.writerow(full_row)

    _print(f"Merged {len(input_paths)} file(s) -> {out_path}")


def command_replace(
    base_path: str,
    pattern: str,
    replacement: str,
    glob_pattern: str,
    use_regex: bool,
    dry_run: bool,
    create_backup: bool,
) -> None:
    root = Path(base_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        _eprint(f"Path not found: {root}")
        sys.exit(2)

    compiled_re = re.compile(pattern) if use_regex else None

    files_changed = 0
    bytes_changed = 0

    for file_str in glob(str(root / glob_pattern), recursive=True):
        file_path = Path(file_str)
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:  # pragma: no cover
            continue

        if use_regex:
            new_text, count = re.subn(compiled_re, replacement, text)  # type: ignore[arg-type]
        else:
            count = text.count(pattern)
            new_text = text.replace(pattern, replacement)

        if count > 0:
            rel = file_path.relative_to(root)
            if dry_run:
                _print(f"Would update {rel} ({count} match(es))")
            else:
                if create_backup:
                    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                    try:
                        shutil.copy2(file_path, backup_path)
                    except Exception:  # pragma: no cover
                        pass
                file_path.write_text(new_text, encoding="utf-8")
                files_changed += 1
                bytes_changed += abs(len(new_text) - len(text))

    if dry_run:
        _print("Dry run complete.")
    else:
        _print(f"Updated {files_changed} file(s); size delta {bytes_changed} byte(s).")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="automation",
        description="Simple Python automation utilities",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # organize
    p_org = subparsers.add_parser("organize", help="Organize files by extension in a folder")
    p_org.add_argument("directory", help="Directory to organize")
    p_org.add_argument("--dry-run", action="store_true", help="Show actions without making changes")
    p_org.set_defaults(func=lambda args: command_organize(args.directory, args.dry_run))

    # fetch
    p_fetch = subparsers.add_parser("fetch", help="Fetch a URL and optionally save to a file")
    p_fetch.add_argument("url", help="URL to fetch")
    p_fetch.add_argument("--out", help="Output file path (optional)")
    p_fetch.add_argument("--timeout", type=float, default=20.0, help="Request timeout in seconds")
    p_fetch.set_defaults(func=lambda args: command_fetch(args.url, args.out, args.timeout))

    # merge-csv
    p_merge = subparsers.add_parser("merge-csv", help="Merge multiple CSV files into one (union of headers)")
    p_merge.add_argument("--inputs", nargs="+", required=True, help="Input CSV files or glob patterns")
    p_merge.add_argument("--out", required=True, help="Output CSV file")
    p_merge.set_defaults(func=lambda args: command_merge_csv(args.inputs, args.out))

    # replace
    p_repl = subparsers.add_parser(
        "replace",
        help="Find and replace text in files (supports regex)",
    )
    p_repl.add_argument("--path", required=True, help="Base directory to search")
    p_repl.add_argument("--glob", default="**/*", help="Glob pattern relative to base path")
    p_repl.add_argument("--find", required=True, help="Text or regex pattern to find")
    p_repl.add_argument("--replace", required=True, help="Replacement text")
    p_repl.add_argument("--regex", action="store_true", help="Treat --find as a regular expression")
    p_repl.add_argument("--dry-run", action="store_true", help="Show changes without writing files")
    p_repl.add_argument("--backup", action="store_true", help="Create .bak backups before writing")
    p_repl.set_defaults(
        func=lambda args: command_replace(
            base_path=args.path,
            pattern=args.find,
            replacement=args.replace,
            glob_pattern=args.glob,
            use_regex=args.regex,
            dry_run=args.dry_run,
            create_backup=args.backup,
        )
    )

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        sys.exit(2)
    func(args)


if __name__ == "__main__":  # pragma: no cover
    main()

