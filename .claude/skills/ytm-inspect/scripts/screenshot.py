#!/usr/bin/env python3
"""
YTMusic visual inspector — takes a screenshot of any YTMusic page using Edge.
Usage: python screenshot.py [url] [output_path]
"""
import subprocess
import sys
import os
from pathlib import Path


def ensure_selenium():
    try:
        from selenium import webdriver  # noqa
    except ImportError:
        print("[ytm-inspect] Installing selenium...", flush=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "selenium", "-q"], check=True)


def screenshot(url: str, out_path: str, width: int = 1280, height: int = 800):
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    import time

    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument(f"--window-size={width},{height}")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--lang=es-ES")
    opts.use_chromium = True

    print(f"[ytm-inspect] Cargando {url} ...", flush=True)
    driver = webdriver.Edge(options=opts)
    try:
        driver.get(url)
        time.sleep(3)
        driver.save_screenshot(out_path)
    finally:
        driver.quit()


def main():
    url = "https://music.youtube.com"
    if len(sys.argv) >= 2 and sys.argv[1].startswith("http"):
        url = sys.argv[1]

    out_path = sys.argv[2] if len(sys.argv) >= 3 else str(
        Path(os.environ.get("TEMP", os.environ.get("TMPDIR", "/tmp"))) / "ytm_inspect.png"
    )

    ensure_selenium()
    screenshot(url, out_path)
    print(f"SCREENSHOT:{out_path}", flush=True)


if __name__ == "__main__":
    main()
