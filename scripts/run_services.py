from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "auth_server.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8001",
            ],
            cwd=ROOT,
        ),
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            cwd=ROOT,
        ),
    ]
    try:
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
