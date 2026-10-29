import io
import re
import time
import logging
import urllib.parse
import urllib.request
import json
from typing import Optional
import speech_recognition as sr

logger = logging.getLogger("SifatVoiceType.speech_engine")

# Common English technical, conversational, and vocabulary words in Bengali phonetics
BENGALI_PRONUNCIATION_TO_ENGLISH = {
    # Pronouns, Be-verbs & Auxiliaries
    'সো': 'so', 'গাইজ': 'guys', 'গাইস': 'guys', 'নাউ': 'now', 'আই': 'I', 'এম': 'am', 'এ': 'a', 'এন': 'an',
    'মাই': 'my', 'মি': 'me', 'ইউ': 'you', 'ইউর': 'your', 'হি': 'he', 'হিজ': 'his', 'হিম': 'him',
    'শি': 'she', 'হার': 'her', 'উই': 'we', 'আওয়ার': 'our', 'আস': 'us', 'দে': 'they', 'দেয়ার': 'their', 'দেম': 'them',
    'ইট': 'it', 'ইটস': 'its', 'দিস': 'this', 'দ্যাট': 'that', 'দোজ': 'those',
    'ইজ': 'is', 'আর': 'are', 'ওয়াজ': 'was', 'ওয়ার': 'were', 'বি': 'be', 'বিন': 'been',
    'হ্যাভ': 'have', 'হ্যাজ': 'has', 'হ্যাড': 'had',
    'ডু': 'do', 'ডাজ': 'does', 'ডিড': 'did', 'ডান': 'done',
    'ক্যান': 'can', 'কুড': 'could', 'উইল': 'will', 'উড': 'would', 'শ্যাল': 'shall', 'শুড': 'should',
    'মে': 'may', 'মাইট': 'might', 'মাস্ট': 'must',

    # Conversational & Greetings
    'হ্যালো': 'hello', 'হাই': 'hi', 'হে': 'hey', 'বাই': 'bye', 'গুডবাই': 'goodbye',
    'থ্যাংকস': 'thanks', 'থ্যাংক': 'thank', 'ওয়েলকাম': 'welcome', 'সরি': 'sorry', 'প্লিজ': 'please',
    'ওকে': 'OK', 'অলরাইট': 'alright', 'ইয়েস': 'yes', 'নো': 'no',
    'গুড': 'good', 'ব্যাড': 'bad', 'গ্রেট': 'great', 'অসাম': 'awesome', 'নাইস': 'nice', 'কুল': 'cool',
    'ব্রো': 'bro', 'ডিউড': 'dude', 'স্যার': 'sir', 'ম্যাম': 'maam', 'বস': 'boss',

    # Technology & Development
    'ওয়েব': 'web', 'ডেভলপার': 'developer', 'ডেভেলপার': 'developer', 'ডিজাইনার': 'designer',
    'প্রোগ্রামার': 'programmer', 'কোডার': 'coder', 'কোড': 'code', 'কোডিং': 'coding',
    'সফটওয়্যার': 'software', 'হার্ডওয়্যার': 'hardware', 'প্রোগ্রাম': 'program',
    'অ্যাপ': 'app', 'অ্যাপস': 'apps', 'অ্যাপ্লিকেশন': 'application',
    'ওয়েবসাইট': 'website', 'সাইট': 'site', 'পেজ': 'page', 'পেইজ': 'page',
    'সার্ভার': 'server', 'ডাটা': 'data', 'ডেটা': 'data', 'ডাটাবেস': 'database',
    'কম্পিউটার': 'computer', 'ল্যাপটপ': 'laptop', 'পিসি': 'PC', 'উইন্ডোজ': 'Windows',
    'স্ক্রিন': 'screen', 'ডিসপ্লে': 'display', 'মনিটর': 'monitor',
    'কিবোর্ড': 'keyboard', 'মাউস': 'mouse', 'প্রিন্টার': 'printer',
    'ইন্টারনেট': 'internet', 'ওয়াইফাই': 'WiFi', 'নেটওয়ার্ক': 'network',
    'অনলাইন': 'online', 'অফলাইন': 'offline',

    # Social & Media
    'ফেসবুক': 'Facebook', 'ফেসবুকে': 'Facebook-এ', 'ইউটিউব': 'YouTube', 'ইউটিউবে': 'YouTube-এ',
    'গুগল': 'Google', 'গুগলে': 'Google-এ', 'ক্রোম': 'Chrome',
    'হোয়াটসঅ্যাপ': 'WhatsApp', 'মেসেঞ্জার': 'Messenger', 'টেলিগ্রাম': 'Telegram', 'ইনস্টাগ্রাম': 'Instagram',
    'ভিডিও': 'video', 'অডিও': 'audio', 'ফটো': 'photo', 'ছবি': 'photo', 'পিক': 'pic',
    'পোস্ট': 'post', 'কমেন্ট': 'comment', 'শেয়ার': 'share', 'লাইক': 'like',
    'সাবস্ক্রাইব': 'subscribe', 'চ্যানেল': 'channel', 'গ্রুপ': 'group',
    'লিংক': 'link', 'ফাইল': 'file', 'ফোল্ডার': 'folder', 'ড্রাইভ': 'drive',
    'ডাউনলোড': 'download', 'আপলোড': 'upload', 'কপি': 'copy', 'পেস্ট': 'paste',
    'কল': 'call', 'মেসেজ': 'message', 'টেক্সট': 'text', 'চ্যাট': 'chat',

    # Work, Daily Life & Common Verbs
    'ওয়ার্ক': 'work', 'জব': 'job', 'অফিস': 'office', 'প্রজেক্ট': 'project',
    'মিটিং': 'meeting', 'ক্লাস': 'class', 'এক্সাম': 'exam', 'রেজাল্ট': 'result',
    'স্টুডেন্ট': 'student', 'টিচার': 'teacher', 'স্কুল': 'school', 'কলেজ': 'college', 'ভার্সিটি': 'varsity',
    'গো': 'go', 'কাম': 'come', 'সি': 'see', 'লুক': 'look', 'ওয়াচ': 'watch',
    'রিড': 'read', 'রাইট': 'write', 'স্পিক': 'speak', 'টক': 'talk', 'লিসেন': 'listen',
    'স্টার্ট': 'start', 'স্টপ': 'stop', 'ওপেন': 'open', 'ক্লোজ': 'close',
    'হেল্প': 'help', 'চেক': 'check', 'সেন্ড': 'send', 'গিভ': 'give', 'টেক': 'take',
    'লেটার': 'later', 'টুমরো': 'tomorrow', 'টুডে': 'today', 'ইয়েস্টারডে': 'yesterday',
    'টাইম': 'time', 'মিনিট': 'minute', 'সেকেন্ড': 'second', 'আওয়ার': 'hour',
    'মানি': 'money', 'ক্যাশ': 'cash', 'পেমেন্ট': 'payment', 'কার্ড': 'card', 'অ্যাকাউন্ট': 'account'
}

BENGALI_QUESTION_WORDS = {
    'কি', 'কী', 'কেন', 'কোথায়', 'কোথায়', 'কে', 'কার', 'কাকে', 'কত', 
    'কেমন', 'কখন', 'নাকি', 'কীভাবে', 'কিভাবে', 'কবে', 'কিসের'
}

BENGALI_CONJUNCTIONS = {
    'কারণ', 'যেহেতু', 'তাহলে', 'তবে', 'সুতরাং', 'অতএব', 'যদিও', 'কিন্তু', 'অথচ', 'নইলে', 'নতুবা'
}

BENGALI_TERMINAL_VERBS = {
    'আছে', 'আছেন', 'আছো', 'আছি', 'ছিল', 'ছিলেন', 'ছিলে', 'ছিলাম', 
    'হবে', 'হবেন', 'হলো', 'হল', 'হয়েছে', 'হইছে', 'হয়েছিল', 'হয়', 'হয়',
    'যাব', 'যাবে', 'যাবেন', 'গেছে', 'গেল', 'গেলেন', 'গিয়েছিল', 'গিয়েছে', 'যাই', 'যান',
    'করব', 'করবো', 'করবে', 'করবেন', 'করেছে', 'করেছেন', 'করলো', 'করল', 'করেছি', 'করি', 'করেন',
    'দিল', 'দিলো', 'দিলেন', 'দিয়েছে', 'দিব', 'দেবে', 'দেবেন', 'দিই', 'দেন',
    'নেবে', 'নেবেন', 'নিল', 'নিলো', 'নিলেন', 'নিয়েছে', 'নিব',
    'পারে', 'পারেন', 'পারব', 'পারবে', 'পারবেন', 'পারি', 'পারল', 'পারলেন',
    'পড়ল', 'পড়লো', 'পড়েছে', 'পড়ি', 'বলল', 'বললো', 'বললেন', 'বলেছে', 'বলেছেন',
    'দেখল', 'দেখলো', 'দেখলেন', 'দেখেছে', 'দেখেছেন', 'চাই', 'চায়', 'চান',
    'পেল', 'পেলো', 'পেলেন', 'পেয়েছে', 'পেয়েছেন', 'বসল', 'উঠল', 'উঠেছে',
    'পারলাম', 'করলাম', 'গেলাম', 'খেলাম', 'দিলাম', 'নিলাম', 'বললাম', 'দেখলাম'
}


def convert_mixed_english_flow(text: str) -> str:
    """
    Intelligently converts English speech flows into proper English words
    using dictionary lookahead and fallback online romanized translation when needed.
    """
    if not text:
        return text

    words = text.split()
    n = len(words)
    res = []
    i = 0

    while i < n:
        w = words[i]
        w_clean = re.sub(r'[^\w\u0980-\u09FF]', '', w)

        # Lookahead: is there a chain of English words spoken in succession?
        j = i
        match_chain = []
        while j < n:
            test_clean = re.sub(r'[^\w\u0980-\u09FF]', '', words[j])
            if test_clean in BENGALI_PRONUNCIATION_TO_ENGLISH:
                match_chain.append(BENGALI_PRONUNCIATION_TO_ENGLISH[test_clean])
                j += 1
            else:
                break

        # If 2 or more English words appear in succession, convert the whole phrase
        if len(match_chain) >= 2:
            res.append(' '.join(match_chain))
            i = j
            continue

        # Single word check for distinct high-frequency tech/media terms
        if w_clean in BENGALI_PRONUNCIATION_TO_ENGLISH and w_clean in (
            'ফেসবুক', 'ফেসবুকে', 'ইউটিউব', 'ইউটিউবে', 'গুগল', 'ক্রোম', 'কম্পিউটার', 'ল্যাপটপ', 'সফটওয়্যার', 'ওয়েবসাইট'
        ):
            res.append(BENGALI_PRONUNCIATION_TO_ENGLISH[w_clean])
            i += 1
            continue

        res.append(w)
        i += 1

    return ' '.join(res)


def auto_punctuate_by_expression(text: str, language: str = "bn-BD") -> str:
    """
    Adds natural punctuation based on tone and expression without requiring verbal commands.
    """
    if not text:
        return text

    text = re.sub(r'\s+', ' ', text).strip()

    if language == "en-US":
        if not text.endswith(('.', '?', '!')):
            first_w = text.lower().split()[0] if text.split() else ""
            if first_w in ('is', 'are', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'what', 'where', 'when', 'why', 'who', 'how'):
                return text + "?"
            return text + "."
        return text

    words = text.split()
    if not words:
        return text

    n = len(words)
    result = []
    sentence_has_question = False

    for i, w in enumerate(words):
        clean_w = re.sub(r'[^\w\u0980-\u09FF]', '', w)
        if clean_w in BENGALI_QUESTION_WORDS:
            sentence_has_question = True

        result.append(w)

        # Natural comma before conjunctions
        if i + 1 < n:
            next_w = re.sub(r'[^\w\u0980-\u09FF]', '', words[i + 1])
            if next_w in BENGALI_CONJUNCTIONS and i >= 2:
                if not result[-1].endswith(('।', ',', '?', '!')):
                    result[-1] = result[-1] + ','
                continue

        # Sentence completion via terminal verbs
        is_terminal = clean_w in BENGALI_TERMINAL_VERBS
        is_last = (i == n - 1)

        if is_last:
            if not result[-1].endswith(('।', '?', '!', ',')):
                mark = '?' if sentence_has_question else '।'
                result[-1] = result[-1] + mark
        elif is_terminal:
            next_w = re.sub(r'[^\w\u0980-\u09FF]', '', words[i + 1])
            particles = {'না', 'নি', 'তো', 'কি', 'কী', 'যে', 'বা', 'এবং', 'ও', 'আর', 'কিনা', 'কখন'}
            if next_w not in particles and len(result) >= 3:
                if not result[-1].endswith(('।', '?', '!', ',')):
                    mark = '?' if sentence_has_question else '।'
                    result[-1] = result[-1] + mark
                    sentence_has_question = False

    formatted = ' '.join(result)
    formatted = re.sub(r'\s+([।,?!])', r'\1', formatted)
    formatted = re.sub(r'([।,?!])([^\s।,?!])', r'\1 \2', formatted)
    return formatted.strip()


class SpeechEngine:
    """Handles audio transcription supporting Bengali, English, and auto/mixed speech."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    def transcribe(self, wav_bytes: bytes, language: str = "bn-BD") -> str:
        """
        Transcribes WAV audio bytes into text with natural expression-based punctuation
        and strict language separation.
        
        Args:
            wav_bytes: Raw WAV audio bytes.
            language: 'bn-BD' (Pure Bengali), 'en-US' (Pure English), or 'auto' (Mixed).
        
        Returns:
            Transcribed string formatted naturally.
        """
        if not wav_bytes or len(wav_bytes) <= 44:
            return ""

        try:
            with io.BytesIO(wav_bytes) as audio_file:
                with sr.AudioFile(audio_file) as source:
                    audio_data = self.recognizer.record(source)
        except Exception as e:
            raise ValueError(f"Invalid audio format: {str(e)}")

        target_lang = "bn-BD" if language in ("bn-BD", "auto") else "en-US"

        raw_text = ""
        try:
            raw_text = self.recognizer.recognize_google(audio_data, language=target_lang)
        except sr.UnknownValueError:
            if language == "auto" and target_lang != "en-US":
                try:
                    raw_text = self.recognizer.recognize_google(audio_data, language="en-US")
                except sr.UnknownValueError:
                    return ""
                except sr.RequestError as req_err:
                    raise ConnectionError(f"Speech recognition service unreachable: {req_err}")
            else:
                return ""
        except sr.RequestError as e:
            raise ConnectionError(f"Could not request results from recognition service: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Transcription error: {str(e)}")

        if not raw_text:
            return ""

        result = raw_text.strip()

        # In 'auto' mode (Mixed): convert English speech flows into English script!
        if language == "auto":
            result = convert_mixed_english_flow(result)

        # Apply expression-based natural punctuation
        return auto_punctuate_by_expression(result, language=language)
