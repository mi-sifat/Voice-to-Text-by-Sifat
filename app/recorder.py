import io
import wave
import threading
import logging
from typing import List, Dict, Any, Optional, Callable
import sounddevice as sd
import numpy as np

logger = logging.getLogger("SifatVoiceType.recorder")

class AudioRecorder:
    """Captures microphone audio using sounddevice and NumPy.
    
    Designed for robust operation on any Windows PC — gracefully handles
    missing, disconnected, or permission-locked microphones.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._is_recording = False
        self._frames: List[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self.device_index: Optional[int] = None
        self.on_volume_callback: Optional[Callable[[float], None]] = None

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @staticmethod
    def get_input_devices() -> List[Dict[str, Any]]:
        """Returns a list of valid microphone input devices.
        
        Filters out virtual/loopback devices and deduplicates names.
        Safe to call on any PC — never raises exceptions.
        """
        devices = []
        seen_names = set()
        try:
            device_list = sd.query_devices()
            # Get the default input device info for highlighting
            try:
                default_input = sd.query_devices(kind='input')
                default_idx = default_input.get('index', None) if isinstance(default_input, dict) else None
            except Exception:
                default_idx = None

            for idx, dev in enumerate(device_list):
                if dev.get("max_input_channels", 0) <= 0:
                    continue
                
                name = dev.get("name", f"Microphone {idx}")
                
                # Skip known virtual/loopback device patterns that cause issues
                lower_name = name.lower()
                skip_patterns = [
                    "stereo mix", "what u hear", "wave out",
                    "loopback", "virtual cable", "voicemeeter"
                ]
                if any(p in lower_name for p in skip_patterns):
                    continue

                # Deduplicate — same mic can appear under multiple host APIs
                # Prefer the first occurrence (usually MME or WASAPI)
                clean_name = name.strip()
                if clean_name in seen_names:
                    continue
                seen_names.add(clean_name)

                # Quick test: can we actually open this device?
                usable = True
                try:
                    test_info = sd.query_devices(idx)
                    if test_info.get("default_samplerate", 0) <= 0:
                        usable = False
                except Exception:
                    usable = False

                if not usable:
                    continue

                is_default = (idx == default_idx) if default_idx is not None else False
                display_name = f"★ {name}" if is_default else name

                devices.append({
                    "index": idx,
                    "name": display_name,
                    "channels": dev.get("max_input_channels", 1),
                    "default_samplerate": dev.get("default_samplerate", 16000),
                    "hostapi": dev.get("hostapi", 0),
                    "is_default": is_default
                })
        except Exception as e:
            logger.warning(f"Failed to enumerate audio devices: {e}")

        # Sort: default device first, then alphabetical
        devices.sort(key=lambda d: (not d.get("is_default", False), d["name"]))
        return devices

    def set_device(self, device_index: Optional[int]):
        self.device_index = device_index

    def _audio_callback(self, indata, frames, time_info, status):
        """Internal callback for sounddevice stream."""
        if status:
            logger.debug(f"Audio stream status: {status}")
        if not self._is_recording:
            return
        with self._lock:
            self._frames.append(indata.copy())
        
        # Calculate volume level (RMS) for UI feedback
        if self.on_volume_callback:
            try:
                rms = float(np.sqrt(np.mean(indata**2)))
                self.on_volume_callback(rms)
            except Exception:
                pass

    def _find_working_device(self) -> Optional[int]:
        """Tries to find a working microphone if the selected one fails.
        Returns device index or None."""
        devices = self.get_input_devices()
        for dev in devices:
            try:
                test_stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype='int16',
                    device=dev["index"],
                    blocksize=1024
                )
                test_stream.start()
                test_stream.stop()
                test_stream.close()
                logger.info(f"Fallback microphone found: {dev['name']} (index {dev['index']})")
                return dev["index"]
            except Exception:
                continue
        return None

    def start_recording(self) -> bool:
        """Starts recording audio from selected microphone.
        
        If the selected device fails, automatically tries to find a working
        alternative. Raises RuntimeError only if no microphone works.
        """
        if self._is_recording:
            return False

        with self._lock:
            self._frames.clear()

        device = self.device_index
        
        # Try opening the selected device
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
                device=device,
                callback=self._audio_callback,
                blocksize=1024
            )
            self._stream.start()
            self._is_recording = True
            return True
        except Exception as e:
            logger.warning(f"Selected microphone (index={device}) failed: {e}")
            # Clean up failed stream
            if self._stream:
                try:
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

        # Fallback: try to find any working microphone
        fallback_device = self._find_working_device()
        if fallback_device is not None:
            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype='int16',
                    device=fallback_device,
                    callback=self._audio_callback,
                    blocksize=1024
                )
                self._stream.start()
                self._is_recording = True
                self.device_index = fallback_device
                return True
            except Exception as e2:
                logger.error(f"Fallback microphone also failed: {e2}")
                if self._stream:
                    try:
                        self._stream.close()
                    except Exception:
                        pass
                    self._stream = None

        self._is_recording = False
        raise RuntimeError(
            "কোনো মাইক্রোফোন কাজ করছে না।\n\n"
            "সমাধান:\n"
            "• মাইক্রোফোন সংযুক্ত আছে কিনা দেখুন\n"
            "• Windows Settings → Privacy → Microphone → App access ON করুন\n"
            "• Sound Settings থেকে Input Device চেক করুন"
        )

    def stop_recording(self) -> bytes:
        """Stops recording and returns WAV formatted audio bytes."""
        if not self._is_recording and not self._frames:
            return b""

        self._is_recording = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.debug(f"Stream close warning: {e}")
            self._stream = None

        with self._lock:
            if not self._frames:
                return b""
            audio_data = np.concatenate(self._frames, axis=0)
            self._frames.clear()

        # Write WAV buffer
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        return wav_buffer.getvalue()
