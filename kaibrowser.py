import subprocess
import sys
import os
import platform

venv_dir = "venv"
is_windows = platform.system() == "Windows"
pip_path = os.path.join(venv_dir, "Scripts" if is_windows else "bin", "pip")
python_path = os.path.join(venv_dir, "Scripts" if is_windows else "bin", "python")

if not os.path.exists(venv_dir):
    print("Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    print("Installing packages...")
    subprocess.run(
        [
            pip_path,
            "install",
            "PyQt6",
            "selenium",
            "webdriver-manager",
            "PyQt6-WebEngine",
            "keyring",
            "requests",
        ],
        check=True,
    )
else:
    print("Virtual environment found, skipping setup...")

print("Launching Kai Browser...")
subprocess.run([python_path, "launch_browser.py"], check=True)
