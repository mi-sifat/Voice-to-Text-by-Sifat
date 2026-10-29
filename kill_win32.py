import ctypes

def kill_process(pid):
    PROCESS_TERMINATE = 0x0001
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if handle:
        res = ctypes.windll.kernel32.TerminateProcess(handle, 1)
        ctypes.windll.kernel32.CloseHandle(handle)
        print(f"Terminated PID {pid}: {bool(res)}")
    else:
        print(f"Could not open PID {pid}, error: {ctypes.GetLastError()}")

if __name__ == "__main__":
    for pid in [9680, 18716]:
        kill_process(pid)
