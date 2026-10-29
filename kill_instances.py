import os
import sys
import ctypes
import psutil

def kill_app_instances():
    current_pid = os.getpid()
    killed = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info['name']
            pid = proc.info['pid']
            if name and "SifatVoiceType" in name and pid != current_pid:
                proc.kill()
                killed += 1
                print(f"Killed {name} ({pid})")
        except Exception as e:
            pass
    print(f"Total killed: {killed}")

if __name__ == "__main__":
    kill_app_instances()
