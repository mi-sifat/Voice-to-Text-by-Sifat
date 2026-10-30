"""
Clipboard Image Helper for Sifat Voice Type.
Extracts images from Windows clipboard across all sources:
- Chrome / Edge "Copy image" (image/png, text/html with <img>, CF_DIB)
- File Explorer copied files (CF_HDROP / text/uri-list)
- Screenshots and Snipping Tool (CF_DIB, CF_DIBV5)
- Direct image URLs and base64 data URIs
- Sets native CF_DIB and Qt clipboard formats for 100% paste compatibility.
"""

import os
import io
import re
import time
import base64
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

from PySide6.QtGui import QImage, QGuiApplication
from PySide6.QtCore import QMimeData

try:
    from PIL import Image, ImageGrab
except ImportError:
    Image = None
    ImageGrab = None

try:
    import requests
except ImportError:
    requests = None

# Windows API setup for 64-bit and 32-bit Windows
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.ico', '.tiff')
CF_DIB = 8
GMEM_MOVEABLE = 0x0002


def extract_clipboard_image(mime: Optional[QMimeData] = None, qclip = None) -> Tuple[Optional[QImage], str]:
    """
    Extracts an image from clipboard through multiple fallback tiers.
    Returns (QImage, source_description) or (None, "").
    """
    if mime is None and qclip is not None:
        try:
            mime = qclip.mimeData()
        except Exception:
            mime = None

    # Tier 1: Direct Qt MIME formats (image/png, image/jpeg, etc.)
    # Chrome often registers 'image/png' on clipboard
    if mime is not None:
        for fmt in ('image/png', 'image/jpeg', 'image/jpg', 'image/bmp', 'image/webp', 'image/x-ms-bmp'):
            if mime.hasFormat(fmt):
                try:
                    raw_bytes = mime.data(fmt)
                    qimg = QImage()
                    if qimg.loadFromData(raw_bytes) and not qimg.isNull():
                        return qimg, f"mime:{fmt}"
                except Exception:
                    pass

    # Tier 2: QClipboard.image()
    if qclip is not None:
        try:
            qimg = qclip.image()
            if qimg and not qimg.isNull():
                return qimg, "qclip.image"
        except Exception:
            pass

    # Tier 3: PIL ImageGrab (reads native CF_DIB / CF_DIBV5 from Windows clipboard directly)
    # Only check global system clipboard if qclip is passed or mime was not explicitly provided
    if ImageGrab is not None and (qclip is not None or mime is None):
        try:
            grabbed = ImageGrab.grabclipboard()
            if grabbed is not None:
                if Image is not None and isinstance(grabbed, Image.Image):
                    buf = io.BytesIO()
                    grabbed.save(buf, format="PNG")
                    qimg = QImage()
                    if qimg.loadFromData(buf.getvalue()) and not qimg.isNull():
                        return qimg, "native:cf_dib"
                elif isinstance(grabbed, list) and len(grabbed) > 0:
                    first_file = str(grabbed[0])
                    if first_file.lower().endswith(IMAGE_EXTENSIONS) and os.path.isfile(first_file):
                        qimg = QImage(first_file)
                        if not qimg.isNull():
                            return qimg, "file:grabbed"
        except Exception:
            pass

    # Tier 4: File Explorer URLs (CF_HDROP / text/uri-list)
    if mime is not None and mime.hasUrls():
        try:
            for url in mime.urls():
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    if local_path.lower().endswith(IMAGE_EXTENSIONS) and os.path.isfile(local_path):
                        qimg = QImage(local_path)
                        if not qimg.isNull():
                            return qimg, "file:urls"
        except Exception:
            pass

    # Tier 5: HTML clipboard format (Chrome copies <img src="..."> in HTML)
    if mime is not None and (mime.hasHtml() or mime.hasFormat("text/html")):
        try:
            html_content = ""
            if mime.hasHtml():
                html_content = mime.html()
            elif mime.hasFormat("text/html"):
                html_content = bytes(mime.data("text/html")).decode("utf-8", errors="ignore")

            if html_content:
                # Look for data URI first: <img src="data:image/...;base64,...">
                m_data = re.search(r'<img[^>]+src=["\'](data:image/[^;]+;base64,[^"\']+)["\']', html_content, re.IGNORECASE)
                if m_data:
                    data_uri = m_data.group(1)
                    b64_part = data_uri.split(',', 1)[1]
                    raw_data = base64.b64decode(b64_part)
                    qimg = QImage()
                    if qimg.loadFromData(raw_data) and not qimg.isNull():
                        return qimg, "html:data_uri"

                # Look for HTTP/HTTPS image URL: <img src="https://...">
                # Only extract if text is short (indicating an image copy rather than an entire web article)
                m_url = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', html_content, re.IGNORECASE)
                if m_url and requests is not None:
                    txt = mime.text() if mime.hasText() else ""
                    if len(txt.strip()) < 300:  # Image copy typically has empty or brief alt-text
                        img_url = m_url.group(1)
                        try:
                            resp = requests.get(img_url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
                            if resp.status_code == 200:
                                qimg = QImage()
                                if qimg.loadFromData(resp.content) and not qimg.isNull():
                                    return qimg, "html:http_img"
                        except Exception:
                            pass
        except Exception:
            pass

    # Tier 6: Text containing local image path or data URI
    if mime is not None and mime.hasText():
        try:
            txt = mime.text().strip()
            # If user copied a path like C:\...\photo.png
            if txt.lower().endswith(IMAGE_EXTENSIONS) and os.path.isfile(txt):
                qimg = QImage(txt)
                if not qimg.isNull():
                    return qimg, "text:local_path"
            # If user copied a data URI
            if txt.startswith("data:image/") and ";base64," in txt:
                b64_part = txt.split(',', 1)[1]
                raw_data = base64.b64decode(b64_part)
                qimg = QImage()
                if qimg.loadFromData(raw_data) and not qimg.isNull():
                    return qimg, "text:data_uri"
        except Exception:
            pass

    return None, ""


def set_windows_clipboard_image(image_path: str, qclip = None) -> bool:
    """
    Sets the image on Windows clipboard using native Win32 CF_DIB (and QClipboard fallback)
    for 100% paste compatibility across all applications without thread conflicts.
    """
    if not image_path or not os.path.isfile(image_path):
        return False

    # 1. Native Windows CF_DIB via Win32 API (standard for all Windows apps)
    if Image is not None:
        try:
            pil_img = Image.open(image_path)
            output = io.BytesIO()
            pil_img.convert("RGB").save(output, format="BMP")
            data = output.getvalue()[14:]  # Strip 14-byte BITMAPFILEHEADER
            output.close()

            h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if h_mem:
                ptr = kernel32.GlobalLock(h_mem)
                if ptr:
                    ctypes.memmove(ptr, data, len(data))
                    kernel32.GlobalUnlock(h_mem)

                    for _ in range(5):
                        if user32.OpenClipboard(0):
                            try:
                                user32.EmptyClipboard()
                                res = user32.SetClipboardData(CF_DIB, h_mem)
                                if res:
                                    return True
                            finally:
                                user32.CloseClipboard()
                            break
                        time.sleep(0.02)
        except Exception:
            pass

    # 2. PySide6 QClipboard fallback
    try:
        app = QGuiApplication.instance()
        if app is not None:
            cb = qclip or QGuiApplication.clipboard()
            if cb:
                qimg = QImage(image_path)
                if not qimg.isNull():
                    cb.setImage(qimg)
                    return True
    except Exception:
        pass

    return False
