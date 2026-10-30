import io
import wave
import pytest
from app.recorder import AudioRecorder
from app.speech_engine import SpeechEngine, auto_punctuate_by_expression, apply_bengali_speech_corrections

def test_bengali_speech_corrections_gita():
    assert apply_bengali_speech_corrections("আমি গিটার পড়লে অনেক শান্তি পাই") == "আমি গীতা পড়লে অনেক শান্তি পাই"
    assert apply_bengali_speech_corrections("শ্রীমদ্ভগবদ্ গিটার পাঠ") == "শ্রীমদ্ভগবদ্ গীতা পাঠ"

def test_bengali_speech_corrections_accuracy_and_press():
    assert apply_bengali_speech_corrections("যাতে এ করেন সেটা বৃদ্ধি পায়") == "যাতে accuracy টা বৃদ্ধি পায়"
    assert apply_bengali_speech_corrections("পেস রিলিজ দেওয়া হয়েছে") == "প্রেস রিলিজ দেওয়া হয়েছে"
    assert apply_bengali_speech_corrections("ক্লিপ বোর্ড থেকে পেস্ট করো") == "ক্লিপবোর্ড থেকে পেস্ট করো"

def test_bengali_transcription_does_not_add_sentence_ending_danda():
    assert auto_punctuate_by_expression("আমি আজ এখানে কাজ করছি", "bn-BD") == "আমি আজ এখানে কাজ করছি"

def test_bengali_question_punctuation_is_preserved():
    assert auto_punctuate_by_expression("আপনি কেমন আছেন", "bn-BD") == "আপনি কেমন আছেন?"

def test_existing_bengali_sentence_punctuation_is_preserved():
    assert auto_punctuate_by_expression("আমি আজ এখানে কাজ করছি।", "bn-BD") == "আমি আজ এখানে কাজ করছি।"

def test_recorder_empty_stop():
    recorder = AudioRecorder()
    assert recorder.is_recording is False
    data = recorder.stop_recording()
    assert data == b""

def test_speech_engine_empty_audio():
    engine = SpeechEngine()
    # Providing empty bytes returns empty string without crashing
    res = engine.transcribe(b"", language="bn-BD")
    assert res == ""

def test_speech_engine_silent_wav():
    engine = SpeechEngine()
    # Create valid silent 1-second WAV
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00" * 32000)
    silent_bytes = buf.getvalue()

    # Silent audio should return empty string without raising unhandled exception
    res = engine.transcribe(silent_bytes, language="bn-BD")
    assert res == ""
