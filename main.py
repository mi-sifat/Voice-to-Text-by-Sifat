import sys
import os
from dotenv import load_dotenv

# Load environment variables if present
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.single_instance import acquire_single_instance_lock, release_single_instance_lock
from app.ui import launch_app

if __name__ == "__main__":
    # Ensure only ONE instance runs across the entire system
    if not acquire_single_instance_lock():
        print("Sifat Voice Type is already running in background or system tray.")
        sys.exit(0)

    try:
        launch_app()
    finally:
        release_single_instance_lock()
