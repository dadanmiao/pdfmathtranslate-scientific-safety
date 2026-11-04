"""Apply, verify and restore this version-pinned patch without importing the app."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def inside(root, relative):
    root = root.resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or target == root:
        raise ValueError(f"Unsafe patch path: {relative}")
    return target


def check_versions(app, manifest):
    for package, expected in (("pdf2zh_next", manifest["app_version"]), ("babeldoc", manifest["babeldoc_version"])):
        matches = list((app / "site-packages").glob(f"{package}-*.dist-info/METADATA"))
        versions = []
        for metadata in matches:
            versions.extend(line.partition(":")[2].strip() for line in metadata.read_text("utf-8").splitlines() if line.startswith("Version:"))
        if versions != [expected]:
            raise ValueError(f"Unsupported {package} version(s) {versions}; expected {expected}")


def manage(app, mode, bundle=None):
    app = Path(app).resolve()
    bundle = Path(bundle or ROOT / "patches").resolve()
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    check_versions(app, manifest)
    plan = []
    seen = set()
    # Validate the entire plan before writing any installed file.
    for entry in manifest["files"]:
        relative = entry["path"]
        target = inside(app, relative)
        if target in seen:
            raise ValueError(f"Duplicate patch target: {relative}")
        seen.add(target)
        payload = inside(bundle / "patched", relative)
        if digest(payload) != entry["sha256"]:
            raise ValueError(f"Damaged patch payload: {relative}")
        current = digest(target)
        original = entry.get("original_sha256")
        if mode == "verify":
            if current != entry["sha256"]:
                raise ValueError(f"Patch is missing or changed: {relative}")
            continue
        if current not in (original, entry["sha256"], *entry.get("previous_sha256", [])):
            raise ValueError(f"Local file does not match any supported version: {relative}")
        if mode == "apply":
            if current == entry["sha256"]:
                continue
            content = payload.read_bytes()
        elif mode == "restore":
            if current == original:
                continue
            if original:
                baseline = inside(bundle / "original", relative)
                if digest(baseline) != original:
                    raise ValueError(f"Damaged baseline payload: {relative}")
                content = baseline.read_bytes()
            else:
                content = None
        else:
            raise ValueError(f"Unknown mode: {mode}")
        plan.append((target, content, target.read_bytes() if target.is_file() else None))
    if not plan:
        print(f"{mode}: all {len(manifest['files'])} patch files checked; no changes needed.")
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = app.parent / "patch-backups" / stamp
    backup.mkdir(parents=True)
    for target, _, previous in plan:
        if previous is not None:
            saved = backup / target.relative_to(app)
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(previous)
    changed = []
    try:
        for target, content, previous in plan:
            changed.append((target, previous))
            target.parent.mkdir(parents=True, exist_ok=True)
            if content is None:
                target.unlink()
            else:
                temporary = target.with_name(target.name + ".patch-tmp")
                temporary.write_bytes(content)
                os.replace(temporary, target)
    except Exception:
        for target, previous in reversed(changed):
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(previous)
        raise
    print(f"{mode}: updated {len(plan)} files; previous files backed up to {backup}")
    return len(plan)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("apply", "verify", "restore"))
    parser.add_argument("--app-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        manage(args.app_dir, args.mode)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Patch refused: {error}\n")
