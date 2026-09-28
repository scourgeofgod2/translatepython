"""Download babeldoc models/fonts from ModelScope + GitHub (HF may be blocked)."""
from __future__ import annotations

import hashlib
from pathlib import Path

import truststore

truststore.inject_into_ssl()
import httpx  # noqa: E402

CACHE = Path.home() / ".cache" / "babeldoc"
MODELS = CACHE / "models"
FONTS = CACHE / "fonts"
MODELS.mkdir(parents=True, exist_ok=True)
FONTS.mkdir(parents=True, exist_ok=True)

ONNX_NAME = "doclayout_yolo_docstructbench_imgsz1024.onnx"
ONNX_URL = (
    "https://www.modelscope.cn/models/AI-ModelScope/DocLayout-YOLO-DocStructBench-onnx"
    "/resolve/master/doclayout_yolo_docstructbench_imgsz1024.onnx"
)
ONNX_SHA3 = "60be061226930524958b5465c8c04af3d7c03bcb0beb66454f5da9f792e3cf2a"

FONT_META_URL = (
    "https://raw.githubusercontent.com/funstory-ai/BabelDOC-Assets/refs/heads/main/font_metadata.json"
)
FONT_URL = (
    "https://raw.githubusercontent.com/funstory-ai/BabelDOC-Assets/refs/heads/main/fonts/{name}"
)
WANT = ("GoNoto", "Noto")


def sha3(path: Path) -> str:
    h = hashlib.sha3_256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    dst = MODELS / ONNX_NAME
    if not (dst.exists() and sha3(dst) == ONNX_SHA3):
        print(f"Downloading {ONNX_NAME} (~75 MB) from ModelScope...")
        r = httpx.get(ONNX_URL, timeout=180, follow_redirects=True)
        r.raise_for_status()
        dst.write_bytes(r.content)
        if sha3(dst) != ONNX_SHA3:
            dst.unlink(missing_ok=True)
            raise SystemExit("ONNX hash mismatch")
        print(f"  ok {dst.stat().st_size} bytes")
    else:
        print("ONNX already cached")

    meta = httpx.get(FONT_META_URL, timeout=30).json()
    for name, info in meta.items():
        if not any(w in name for w in WANT):
            continue
        dest = FONTS / name
        expect = info.get("sha3_256")
        if dest.exists() and expect and sha3(dest) == expect:
            print(f"font cached: {name}")
            continue
        print(f"font: {name}")
        r = httpx.get(FONT_URL.format(name=name), timeout=120, follow_redirects=True)
        r.raise_for_status()
        dest.write_bytes(r.content)
        if expect and sha3(dest) != expect:
            dest.unlink(missing_ok=True)
            print("  hash mismatch, skipped")
        else:
            print(f"  ok {dest.stat().st_size} bytes")

    print("Assets ready under", CACHE)


if __name__ == "__main__":
    main()
