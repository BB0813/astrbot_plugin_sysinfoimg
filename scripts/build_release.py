from __future__ import annotations

from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
INCLUDE_FILES = [
    "__init__.py",
    "_conf_schema.json",
    "CONTRIBUTORS.md",
    "dashboard_runtime.py",
    "history_store.py",
    "LICENSE",
    "main.py",
    "metadata.yaml",
    "monitor.py",
    "README.md",
    "requirements.txt",
    "utils.py",
]
INCLUDE_DIRS = [
    "templates",
]


def parse_metadata(metadata_path: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for raw_line in metadata_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_release_files(target_root: Path) -> None:
    for rel in INCLUDE_FILES:
        src = ROOT / rel
        if not src.exists():
            raise FileNotFoundError(f"Missing release file: {src}")
        dst = target_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    for rel in INCLUDE_DIRS:
        src_dir = ROOT / rel
        if not src_dir.exists():
            raise FileNotFoundError(f"Missing release directory: {src_dir}")
        dst_dir = target_root / rel
        shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))


def make_flat_zip(source_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            archive.write(path, path.relative_to(source_dir).as_posix())


def make_nested_zip(source_dir: Path, zip_path: Path, root_name: str) -> None:
    if zip_path.exists():
        zip_path.unlink()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            archive.write(path, (Path(root_name) / path.relative_to(source_dir)).as_posix())


def main() -> None:
    metadata = parse_metadata(ROOT / "metadata.yaml")
    plugin_name = metadata.get("name")
    version = metadata.get("version")
    if not plugin_name or not plugin_name.isidentifier():
        raise ValueError(f"Invalid metadata name: {plugin_name!r}")
    if not version:
        raise ValueError("Missing metadata version")

    release_dir = ROOT / f"release_upload_{version}"
    flat_dir = release_dir / "astrbot_upload_flat"
    manual_dir = release_dir / plugin_name

    reset_dir(flat_dir)
    reset_dir(manual_dir)
    copy_release_files(flat_dir)
    copy_release_files(manual_dir)

    upload_zip = DIST_DIR / f"{plugin_name}_{version}_astrbot_upload.zip"
    manual_zip = DIST_DIR / f"{plugin_name}_{version}_manual_folder.zip"
    make_flat_zip(flat_dir, upload_zip)
    make_nested_zip(manual_dir, manual_zip, plugin_name)

    print(f"plugin_name={plugin_name}")
    print(f"version={version}")
    print(f"flat_dir={flat_dir}")
    print(f"manual_dir={manual_dir}")
    print(f"upload_zip={upload_zip}")
    print(f"manual_zip={manual_zip}")


if __name__ == "__main__":
    main()
