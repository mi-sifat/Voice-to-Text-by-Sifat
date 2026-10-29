import ctypes
import sys
import os

MUTEX_NAME = "Global\\SifatVoiceType_SingleInstance_Mutex"
kernel32 = ctypes.windll.kernel32

_mutex_handle = None

def acquire_single_instance_lock() -> bool:
    """
    Creates a named Windows mutex to guarantee that only ONE instance 
    of Sifat Voice Type can run at a time across the entire system.
    """
    global _mutex_handle
    ERROR_ALREADY_EXISTS = 183
    
    _mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_err = kernel32.GetLastError()
    
    if last_err == ERROR_ALREADY_EXISTS:
        return False
    return True

def release_single_instance_lock():
    global _mutex_handle
    if _mutex_handle:
        kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None
