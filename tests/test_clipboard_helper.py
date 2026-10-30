import os
import io
import pytest
from PySide6.QtGui import QImage
from PySide6.QtCore import QMimeData, QByteArray, QBuffer, QIODevice, QUrl
from app.clipboard_helper import extract_clipboard_image, set_windows_clipboard_image

@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app

def test_extract_from_mime_png(qapp):
    # Create test image
    img = QImage(30, 20, QImage.Format_RGB32)
    img.fill(0xFF112233)
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    png_bytes = buf.data()

    mime = QMimeData()
    mime.setData("image/png", png_bytes)

    extracted, src = extract_clipboard_image(mime=mime)
    assert extracted is not None
    assert not extracted.isNull()
    assert extracted.width() == 30
    assert extracted.height() == 20
    assert "image/png" in src

def test_extract_from_data_uri_html(qapp):
    # 1x1 red PNG data URI
    data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    html = f"<html><body><img src='{data_uri}' alt='test'></body></html>"

    mime = QMimeData()
    mime.setData("text/html", QByteArray(html.encode('utf-8')))

    extracted, src = extract_clipboard_image(mime=mime)
    assert extracted is not None
    assert not extracted.isNull()
    assert extracted.width() == 1
    assert extracted.height() == 1
    assert src == "html:data_uri"

def test_extract_from_local_file_url(tmp_path, qapp):
    test_img = tmp_path / "test_pic.png"
    qimg = QImage(40, 40, QImage.Format_RGB32)
    qimg.fill(0xFF556677)
    qimg.save(str(test_img), "PNG")

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(test_img))])

    extracted, src = extract_clipboard_image(mime=mime)
    assert extracted is not None
    assert not extracted.isNull()
    assert extracted.width() == 40
    assert src == "file:urls"

def test_set_windows_clipboard_image(tmp_path, qapp):
    test_img = tmp_path / "set_clip.png"
    qimg = QImage(50, 50, QImage.Format_RGB32)
    qimg.fill(0xFFAABBCC)
    qimg.save(str(test_img), "PNG")

    res = set_windows_clipboard_image(str(test_img))
    assert res is True

    # Clean up clipboard after test
    import pyperclip
    pyperclip.copy("")

def test_extract_from_text_local_path(tmp_path, qapp):
    test_img = tmp_path / "text_pic.jpg"
    qimg = QImage(25, 25, QImage.Format_RGB32)
    qimg.fill(0xFF336699)
    qimg.save(str(test_img), "JPEG")

    mime = QMimeData()
    mime.setText(str(test_img))

    extracted, src = extract_clipboard_image(mime=mime)
    assert extracted is not None
    assert not extracted.isNull()
    assert extracted.width() == 25
    assert src == "text:local_path"

def test_extract_from_non_image_text(qapp):
    mime = QMimeData()
    mime.setText("This is normal copied text from a website or document.")

    extracted, src = extract_clipboard_image(mime=mime)
    assert extracted is None
    assert src == ""
