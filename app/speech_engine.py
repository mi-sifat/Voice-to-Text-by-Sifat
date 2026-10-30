import io
import re
import time
import logging
from typing import Optional
import speech_recognition as sr

logger = logging.getLogger("SifatVoiceType.speech_engine")

# Common English technical, conversational, and vocabulary words in Bengali phonetics
BENGALI_PRONUNCIATION_TO_ENGLISH = {
    # Pronouns, Be-verbs & Auxiliaries
    'সো': 'so', 'গাইজ': 'guys', 'গাইস': 'guys', 'নাও': 'now', 'আই': 'I', 'এম': 'am', 'এ': 'a', 'এন': 'an',
    'মাই': 'my', 'মি': 'me', 'ইউ': 'you', 'ইউর': 'your', 'হি': 'he', 'হিজ': 'his', 'হিম': 'him',
    'শি': 'she', 'হার': 'her', 'উই': 'we', 'আওয়ার': 'our', 'আস': 'us', 'দে': 'they', 'দেয়ার': 'their', 'দেম': 'them',
    'ইট': 'it', 'ইটস': 'its', 'দিস': 'this', 'দ্যাট': 'that', 'দোজ': 'those',
    'ইজ': 'is', 'আর': 'are', 'ওয়াজ': 'was', 'ওয়ার': 'were', 'বি': 'be', 'বিন': 'been',
    'হ্যাভ': 'have', 'হ্যাস': 'has', 'হ্যাজ': 'has', 'হ্যাড': 'had',
    'ডু': 'do', 'ডাজ': 'does', 'ডিড': 'did', 'ডান': 'done',
    'ক্যান': 'can', 'কুড': 'could', 'উইল': 'will', 'উড': 'would', 'শ্যাল': 'shall', 'শুড': 'should',
    'মে': 'may', 'মাইট': 'might', 'মাস্ট': 'must',

    # Conversational & Greetings
    'হ্যালো': 'hello', 'হাই': 'hi', 'হে': 'hey', 'বাই': 'bye', 'গুডবাই': 'goodbye',
    'থ্যাংকস': 'thanks', 'থ্যাঙ্কস': 'thanks', 'থ্যাংক': 'thank', 'ওয়েলকাম': 'welcome', 'সরি': 'sorry', 'প্লিজ': 'please',
    'ওকে': 'OK', 'অলরাইট': 'alright', 'ইয়েস': 'yes', 'নো': 'no',
    'গুড': 'good', 'ব্যাড': 'bad', 'গ্রেট': 'great', 'অসাম': 'awesome', 'নাইস': 'nice', 'কুল': 'cool',
    'ব্রো': 'bro', 'ডিউড': 'dude', 'স্যার': 'sir', 'ম্যাম': 'maam', 'বস': 'boss',

    # Technology, Development & Web
    'ওয়েব': 'web', 'ডেভেলপার': 'developer', 'ডেভলপার': 'developer', 'ডিজাইনার': 'designer',
    'প্রোগ্রামার': 'programmer', 'প্রোগ্রামিং': 'programming', 'কোডার': 'coder', 'কোড': 'code', 'কোডিং': 'coding',
    'সফটওয়্যার': 'software', 'সফটওয়্যার': 'software', 'হার্ডওয়্যার': 'hardware', 'প্রোগ্রাম': 'program',
    'অ্যাপ': 'app', 'অ্যাপস': 'apps', 'অ্যাপ্লিকেশন': 'application',
    'ওয়েবসাইট': 'website', 'ওয়েবসাইট': 'website', 'সাইট': 'site', 'পেজ': 'page', 'পেইজ': 'page',
    'সার্ভার': 'server', 'ডাটা': 'data', 'ডেটা': 'data', 'ডাটাবেস': 'database', 'ডাটাবেইজ': 'database',
    'কম্পিউটার': 'computer', 'ল্যাপটপ': 'laptop', 'পিসি': 'PC', 'উইন্ডোজ': 'Windows',
    'স্ক্রিন': 'screen', 'ডিসপ্লে': 'display', 'মনিটর': 'monitor',
    'কিবোর্ড': 'keyboard', 'মাউস': 'mouse', 'প্রিন্টার': 'printer',
    'ইন্টারনেট': 'internet', 'ওয়াইফাই': 'WiFi', 'ওয়াইফাই': 'WiFi', 'নেটওয়ার্ক': 'network',
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
    'ওয়ার্ক': 'work', 'ওয়ার্ক': 'work', 'জব': 'job', 'অফিস': 'office', 'প্রজেক্ট': 'project',
    'মিটিং': 'meeting', 'ক্লাস': 'class', 'এক্সাম': 'exam', 'রেজাল্ট': 'result',
    'স্টুডেন্ট': 'student', 'টিচার': 'teacher', 'স্কুল': 'school', 'কলেজ': 'college', 'ভার্সিটি': 'varsity',
    'গো': 'go', 'কাম': 'come', 'সি': 'see', 'লুক': 'look', 'ওয়াচ': 'watch',
    'রিড': 'read', 'রাইট': 'write', 'স্পিক': 'speak', 'টক': 'talk', 'লিসেন': 'listen',
    'স্টার্ট': 'start', 'স্টপ': 'stop', 'ওপেন': 'open', 'ক্লোজ': 'close',
    'হেল্প': 'help', 'চেক': 'check', 'সেন্ড': 'send', 'গিভ': 'give', 'টেক': 'take',
    'লেটার': 'later', 'টুমরো': 'tomorrow', 'টুডে': 'today', 'ইয়েস্টারডে': 'yesterday',
    'টাইম': 'time', 'মিনিট': 'minute', 'সেকেন্ড': 'second', 'আওয়ার': 'hour',
    'মানি': 'money', 'ক্যাশ': 'cash', 'পেমেন্ট': 'payment', 'কার্ড': 'card', 'অ্যাকাউন্ট': 'account'
}

BENGALI_QUESTION_WORDS = {
    'কি', 'কী', 'কেন', 'কোথায়', 'কোথায়', 'কে', 'কার', 'কাকে', 'কত', 
    'কেমন', 'কখন', 'নাকি', 'কীভাবে', 'কিভাবে', 'কবে', 'কিসের'
}

# Explicit punctuation spoken commands (if user speaks them deliberately)
EXPLICIT_PUNCTUATION = {
    'দাঁড়ি': '।', 'দাড়ি': '।', 'পূর্ণচ্ছেদ': '।',
    'কমা': ',', 'কোমা': ',',
    'প্রশ্নবোধক চিহ্ন': '?', 'প্রশ্নচিহ্ন': '?', 'জিজ্ঞাসা চিহ্ন': '?',
    'আশ্চর্যবোধক চিহ্ন': '!', 'বিস্ময়চিহ্ন': '!',
    'ক্লোন': ':', 'কোলন': ':', 'সেমিকোলন': ';',
    'নতুন লাইন': '\n', 'নতুন প্যারা': '\n\n'
}


def convert_mixed_english_flow(text: str) -> str:
    """
    Converts English speech flows and phonetic English words inside Bengali text
    into proper English characters seamlessly.
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

        # Check for consecutive chains of phonetic English words (e.g. "so guys now I am a web developer")
        j = i
        match_chain = []
        while j < n:
            test_clean = re.sub(r'[^\w\u0980-\u09FF]', '', words[j])
            if test_clean in BENGALI_PRONUNCIATION_TO_ENGLISH:
                match_chain.append(BENGALI_PRONUNCIATION_TO_ENGLISH[test_clean])
                j += 1
            else:
                break

        # If a sequence of 2 or more English words was spoken, convert the whole phrase
        if len(match_chain) >= 2:
            res.append(' '.join(match_chain))
            i = j
            continue

        # Single word check for distinct technical / technology terms
        if w_clean in BENGALI_PRONUNCIATION_TO_ENGLISH and w_clean in (
            'ফেসবুক', 'ফেসবুকে', 'ইউটিউব', 'ইউটিউবে', 'গুগল', 'ক্রোম', 'কম্পিউটার', 
            'ল্যাপটপ', 'সফটওয়্যার', 'সফটওয়্যার', 'ওয়েবসাইট', 'ওয়েবসাইট', 'অনলাইন',
            'অফলাইন', 'ইন্টারনেট', 'ওয়াইফাই', 'ওয়ার্ক', 'ওয়ার্কিং', 'প্রোগ্রামিং', 'কোডিং'
        ):
            res.append(BENGALI_PRONUNCIATION_TO_ENGLISH[w_clean])
            i += 1
            continue

        res.append(w)
        i += 1

    return ' '.join(res)


def auto_punctuate_by_expression(text: str, language: str = "bn-BD") -> str:
    """
    Natural punctuation handler:
    1. Replaces spoken punctuation commands if explicitly spoken (e.g., 'দাঁড়ি', 'কমা').
    2. Adds '?' ONLY if question words ('কি', 'কেন', 'কেমন', etc.) are present.
    3. NEVER automatically appends '।' or ',' when speech stops or key is released mid-sentence.
    """
    if not text:
        return text

    text = re.sub(r'\s+', ' ', text).strip()

    # Handle explicit verbal punctuation keywords
    for spoken, mark in EXPLICIT_PUNCTUATION.items():
        text = re.sub(r'\b' + re.escape(spoken) + r'\b', mark, text)

    if language == "en-US":
        words = text.split()
        if words:
            first_w = words[0].lower().strip('.,?!')
            if first_w in ('is', 'are', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'what', 'where', 'when', 'why', 'who', 'how'):
                if not text.endswith(('?', '.', '!')):
                    return text + "?"
        return text

    # For Bengali & Mixed:
    # Check if sentence contains question expressions
    words = text.split()
    if not words:
        return text

    has_question = False
    for w in words:
        clean_w = re.sub(r'[^\w\u0980-\u09FF]', '', w)
        if clean_w in BENGALI_QUESTION_WORDS:
            has_question = True
            break

    # If it is clearly a question and user didn't put ending punctuation, add '?'
    if has_question and not text.endswith(('?', '।', '!', ',')):
        text = text + '?'

    # Clean spacing around punctuation
    formatted = re.sub(r'\s+([।,?!:;])', r'\1', text)
    formatted = re.sub(r'([।,?!:;])([^\s।,?!:;])', r'\1 \2', formatted)
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
            Transcribed string formatted naturally without unwanted commas or sentence-end dandas.
        """
        if not wav_bytes or len(wav_bytes) <= 44:
            return ""

        try:
            with io.BytesIO(wav_bytes) as audio_file:
                with sr.AudioFile(audio_file) as source:
                    audio_data = self.recognizer.record(source)
        except Exception as e:
            raise ValueError(f"Invalid audio format: {str(e)}")

        raw_text = ""

        # --- In 'auto' (Mixed) Mode ---
        if language == "auto":
            # 1. First, check with English (US)
            eng_text = ""
            try:
                eng_text = self.recognizer.recognize_google(audio_data, language="en-US")
            except Exception:
                eng_text = ""

            # 2. Check with Bengali (BD)
            bn_text = ""
            try:
                bn_text = self.recognizer.recognize_google(audio_data, language="bn-BD")
            except Exception:
                bn_text = ""

            # Intelligent Decision:
            # If English recognition returned pure English speech with 2+ words, and user was speaking English
            eng_words = eng_text.split() if eng_text else []
            bn_words = bn_text.split() if bn_text else []

            if eng_text and not bn_text:
                raw_text = eng_text
            elif bn_text and not eng_text:
                raw_text = convert_mixed_english_flow(bn_text)
            elif eng_text and bn_text:
                # If audio is strongly English (e.g. 3+ valid English words and bn_text is short phonetic garble)
                if len(eng_words) >= 3 and len(bn_words) <= len(eng_words) + 1:
                    raw_text = eng_text
                else:
                    # Bengali dominant with English phrases: apply convert_mixed_english_flow
                    raw_text = convert_mixed_english_flow(bn_text)
            else:
                return ""

        # --- Pure Single Language Mode ---
        else:
            target_lang = "bn-BD" if language == "bn-BD" else "en-US"
            try:
                raw_text = self.recognizer.recognize_google(audio_data, language=target_lang)
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as e:
                raise ConnectionError(f"Speech recognition service unreachable: {str(e)}")
            except Exception as e:
                raise RuntimeError(f"Transcription error: {str(e)}")

        if not raw_text:
            return ""

        result = raw_text.strip()

        # Apply expression-based natural punctuation (clean & no auto-danda/comma on release)
        return auto_punctuate_by_expression(result, language=language)
