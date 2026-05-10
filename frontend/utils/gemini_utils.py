"""
Gemini AI utilities for AdoptSense.

Uses the new google-genai SDK (google.genai) instead of the deprecated
google-generativeai package.

Studio photo pipeline — user picks per upload:
  Primary  — FLUX.1-Kontext via Hugging Face Inference API.
             Sends the original photo + prompt; model edits it in-context,
             preserving fur detail, pose, and anatomy while replacing the
             background with a professional studio backdrop + soft shadow.
  Fallback — rembg cutout composited onto a flat neutral backdrop.
             Used when HF_TOKEN is missing or the HF quota is exhausted.

Smart matching uses deterministic scoring — Gemini only parses the
natural-language query into structured JSON; all scoring is computed
locally so we never send the full listings DB to the API.
"""
import base64
import io
import os
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import streamlit as st

_GEMINI_API_KEY: Optional[str] = None
_LOGO_PATH = Path(__file__).parent.parent / "assets" / "logo" / "AdoptSense Logo_best quality_png.png"


def _log(msg: str):
    print(f"[gemini_utils] {msg}", file=sys.stderr, flush=True)


def _get_api_key() -> Optional[str]:
    global _GEMINI_API_KEY
    if _GEMINI_API_KEY:
        return _GEMINI_API_KEY
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key:
            _GEMINI_API_KEY = key
            return key
    except Exception:
        pass
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        _GEMINI_API_KEY = key
    return _GEMINI_API_KEY or None


def set_api_key(key: str):
    global _GEMINI_API_KEY
    _GEMINI_API_KEY = key


def is_configured() -> bool:
    return bool(_get_api_key())


# ── Hugging Face token ────────────────────────────────────────────────────────

_HF_TOKEN: Optional[str] = None


def _get_hf_token() -> Optional[str]:
    global _HF_TOKEN
    if _HF_TOKEN:
        return _HF_TOKEN
    try:
        token = st.secrets.get("HF_TOKEN", "")
        if token:
            _HF_TOKEN = token
            return token
    except Exception:
        pass
    token = os.environ.get("HF_TOKEN", "")
    if token:
        _HF_TOKEN = token
    return _HF_TOKEN or None


def is_hf_configured() -> bool:
    return bool(_get_hf_token())


def _get_client():
    """Return a configured google.genai Client."""
    from google import genai
    return genai.Client(api_key=_get_api_key())


def _logo_b64() -> Optional[str]:
    """Return the logo PNG as a base64 string, or None if not found."""
    try:
        return base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    except Exception:
        return None


# ── AI Loading Overlay ────────────────────────────────────────────────────────

_AI_MSGS = [
    "Sniffing out your perfect match.",
    "Finding your future best friend.",
    "Matching paws with personalities.",
    "Checking who might steal your heart.",
    "Looking for your four-legged soulmate.",
    "Just a paw-step away from love.",
    "Fetching the best matches for you.",
    "Searching for tails that fit your tale.",
    "Finding the pet who gets you.",
    "Making tails wag behind the scenes.",
    "Almost found your new favourite roommate.",
    "Pairing humans with professional cuddlers.",
    "Scanning for maximum cuteness compatibility.",
    "Looking for a pet who matches your vibe.",
    "Your new best friend may be loading.",
    "Sorting by fluff, charm, and heart.",
    "Finding the pawfect companion.",
    "Running the cuddle compatibility check.",
    "Checking who deserves your sofa.",
    "Matching you with your future shadow.",
    "Preparing a shortlist of adorable candidates.",
    "Looking for someone to judge your snacks.",
    "Finding pets with best-friend potential.",
    "Almost there — love has paws.",
    "Sniffing through profiles with care.",
    "Calculating tail-wag probability.",
    "Finding your next hello at the door.",
    "Searching for a tiny heartbeat to bring home.",
    "Matching you with unconditional love.",
    "One small click for you, one giant leap for pet-kind.",
]

_CYCLE_S = 3      # seconds each sentence is shown
_N_MSGS   = len(_AI_MSGS)
_TOTAL_S  = _N_MSGS * _CYCLE_S   # full loop duration in seconds


@contextmanager
def ai_loading(message: str = "Processing with AI…"):
    """Context manager that shows a full-page logo overlay with sequentially
    animated funny sentences during any AI call.

    Usage:
        with ai_loading("Generating description…"):
            ok, result = improve_description(...)
    """
    b64 = _logo_b64()
    if b64:
        # Build one <span> per funny sentence, each positioned absolutely
        # and animated with a staggered delay so they appear one at a time.
        msg_spans = "".join(
            f'<span class="as-ai-msg" style="animation-delay:{i * _CYCLE_S}s;">{msg}</span>'
            for i, msg in enumerate(_AI_MSGS)
        )
        placeholder = st.empty()
        placeholder.markdown(
            f"""
            <style>
            @keyframes as_bounce {{
                0%, 100% {{ transform: translateY(0) scale(1); }}
                50% {{ transform: translateY(-18px) scale(1.06); }}
            }}
            @keyframes as_sentence {{
                0%     {{ opacity: 0; transform: translateY(6px); }}
                0.33%  {{ opacity: 1; transform: translateY(0); }}
                2.67%  {{ opacity: 1; transform: translateY(0); }}
                3%     {{ opacity: 0; transform: translateY(-6px); }}
                100%   {{ opacity: 0; transform: translateY(0); }}
            }}
            .as-ai-overlay {{
                position: fixed; inset: 0;
                background: rgba(30, 39, 97, 0.78);
                backdrop-filter: blur(8px);
                -webkit-backdrop-filter: blur(8px);
                z-index: 9999;
                display: flex; flex-direction: column;
                align-items: center; justify-content: center;
                gap: 28px;
            }}
            .as-ai-overlay img {{
                width: 110px;
                filter: drop-shadow(0 8px 24px rgba(0,0,0,0.5));
                animation: as_bounce 1.3s ease-in-out infinite;
            }}
            .as-ai-title {{
                color: #FFFFFF; font-size: 18px; font-weight: 600;
                letter-spacing: 0.3px; margin: 0;
            }}
            .as-ai-msgs-wrap {{
                position: relative; height: 26px; width: 520px; overflow: visible;
            }}
            .as-ai-msg {{
                position: absolute; left: 0; right: 0; top: 0;
                text-align: center;
                color: rgba(202,220,252,0.92);
                font-size: 14px; font-style: italic; font-weight: 400;
                opacity: 0; white-space: nowrap;
                animation: as_sentence {_TOTAL_S}s ease-in-out infinite;
            }}
            </style>
            <div class="as-ai-overlay">
                <img src="data:image/png;base64,{b64}" alt="AdoptSense" />
                <p class="as-ai-title">{message}</p>
                <div class="as-ai-msgs-wrap">{msg_spans}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        try:
            yield
        finally:
            placeholder.empty()
    else:
        yield


# ── Description improvement ───────────────────────────────────────────────────

_DESCRIPTION_SYSTEM = (
    "You are an expert copywriter for a pet adoption platform. "
    "Your task is to rewrite a pet's listing description to maximise adoption appeal. "
    "Requirements:\n"
    "- Length: exactly 4–8 sentences\n"
    "- Tone: warm, enthusiastic, and positive\n"
    "- Highlight personality traits, care history, and what makes this pet special\n"
    "- End with a gentle call to action encouraging adoption\n"
    "- Do NOT invent medical facts not present in the input\n"
    "- Output ONLY the improved description, no extra commentary"
)


def improve_description(
    raw_description: str,
    pet_characteristics: dict,
    image_bytes: Optional[bytes] = None,
    image_mime: str = "image/jpeg",
) -> tuple[bool, str]:
    key = _get_api_key()
    if not key:
        return False, "Gemini API key not configured."
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)
        type_str = "Dog" if pet_characteristics.get("type") == 1 else "Cat"
        char_lines = [
            f"Species: {type_str}",
            f"Age: {pet_characteristics.get('age', 'Unknown')} months",
            f"Gender: {['', 'Male', 'Female', 'Mixed'][int(pet_characteristics.get('gender', 1))]}",
            f"Health: {['', 'Healthy', 'Minor Injury', 'Serious Injury'][int(pet_characteristics.get('health', 1))]}",
            f"Vaccinated: {['', 'Yes', 'No', 'Unknown'][int(pet_characteristics.get('vaccinated', 3))]}",
            f"Sterilized: {['', 'Yes', 'No', 'Unknown'][int(pet_characteristics.get('sterilized', 3))]}",
            f"Fee: {'Free' if pet_characteristics.get('fee', 0) == 0 else str(pet_characteristics.get('fee', 0))}",
        ]
        prompt = (
            f"Pet characteristics:\n{chr(10).join(char_lines)}\n\n"
            f"Original description:\n{raw_description or '(none provided)'}\n\n"
            "Please write an improved adoption description."
        )
        contents = []
        if image_bytes:
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type=image_mime))
        contents.append(prompt)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=_DESCRIPTION_SYSTEM),
        )
        return True, response.text.strip()
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "ResourceExhausted" in msg or "Quota exceeded" in msg:
            return False, (
                "Gemini quota exceeded — your listing has been saved without AI description "
                "improvement. Try again later or check your Gemini API plan."
            )
        _log(f"improve_description error: {exc}")
        return False, f"Gemini error: {exc}"


# ── FLUX.1-Kontext studio pipeline (primary) ─────────────────────────────────

_FLUX_STUDIO_PROMPT = (
    "This is a photo editing task. Do NOT change the animal in any way. "
    "The dog or cat in the result must be pixel-identical in breed, fur color, fur texture, "
    "face, ears, body shape, pose, and expression to the animal in the input photo. "
    "Only change the background: replace it with a clean seamless light grey studio backdrop. "
    "Add soft diffused studio lighting. "
    "Add a subtle realistic contact shadow directly beneath the animal so it looks grounded. "
    "Do not alter the animal's fur, color, markings, collar, leash, or body in any way. "
    "Do not repose, resize, or reframe the animal. "
    "Do not add or remove any accessories. "
    "The result must look like the exact same animal photographed in a professional studio."
)

_FLUX_MODEL = "black-forest-labs/FLUX.1-Kontext-dev"

_FLUX_NEGATIVE_PROMPT = (
    "different dog, different cat, different animal, different breed, "
    "different fur color, different fur texture, different face, different ears, "
    "different body shape, different pose, sitting when original is standing, "
    "standing when original is sitting, new animal, replaced animal, "
    "cartoon, illustration, painting, drawing, render, 3d, anime, "
    "blurry, low quality, watermark, text, logo, "
    "multiple animals, extra animals, background animal, "
    "outdoor scene, nature, grass, trees, park, street, "
    "colorful background, patterned background, gradient background"
)


def _add_studio_shadow(img):
    """Add a soft elliptical contact shadow + subtle floor reflection beneath the pet.

    Works on any RGB PIL Image returned by FLUX. The shadow is composited
    onto the image using a Gaussian-blurred ellipse mask so it feathers
    naturally into the studio backdrop — no hard edges.
    """
    from PIL import Image, ImageDraw, ImageFilter

    w, h = img.size

    # ── Contact shadow ────────────────────────────────────────────────────────
    # Ellipse sits in the bottom ~8% of the image, horizontally centred,
    # width ~55% of image width. These proportions work well for standing pets.
    shadow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow_layer)

    sx = int(w * 0.225)          # left edge of ellipse
    ex = int(w * 0.775)          # right edge
    sy = int(h * 0.895)          # top of ellipse
    ey = int(h * 0.940)          # bottom of ellipse
    draw.ellipse([sx, sy, ex, ey], fill=(30, 30, 35, 120))

    # Blur heavily so the shadow feathers out softly
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=int(h * 0.018)))

    # Composite shadow beneath the image
    base = img.convert("RGBA")
    base = Image.alpha_composite(base, shadow_layer)

    # ── Floor reflection ──────────────────────────────────────────────────────
    # Thin horizontal gradient strip just above the shadow centre —
    # mimics the faint bright-floor specular seen in studio shots.
    refl_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw2 = ImageDraw.Draw(refl_layer)
    ry = int(h * 0.880)
    ry2 = int(h * 0.900)
    draw2.ellipse([sx + int(w*0.06), ry, ex - int(w*0.06), ry2],
                  fill=(255, 255, 255, 28))
    refl_layer = refl_layer.filter(ImageFilter.GaussianBlur(radius=int(h * 0.012)))
    base = Image.alpha_composite(base, refl_layer)

    return base.convert("RGB")


def _make_studio_with_flux(image_bytes: bytes) -> tuple[bool, bytes | str]:
    """Use FLUX.1-Kontext via Hugging Face Inference API to create a studio portrait.

    Uses a detailed positive prompt + negative prompt to minimise hallucination.
    Post-processes with contact shadow + floor reflection.
    """
    token = _get_hf_token()
    if not token:
        return False, "HF_TOKEN not configured"
    try:
        from huggingface_hub import InferenceClient
        from PIL import Image

        client = InferenceClient(api_key=token)
        input_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        result_img = client.image_to_image(
            image=input_img,
            prompt=_FLUX_STUDIO_PROMPT,
            negative_prompt=_FLUX_NEGATIVE_PROMPT,
            model=_FLUX_MODEL,
        )

        result_img = _add_studio_shadow(result_img)

        out = io.BytesIO()
        result_img.save(out, "PNG")
        _log("Studio via FLUX.1-Kontext (HF) succeeded")
        return True, out.getvalue()

    except Exception as exc:
        err = str(exc)
        if "402" in err or "exceeded" in err.lower() or "credits" in err.lower():
            _log(f"HF quota exhausted: {exc}")
            return False, "hf_quota_exceeded"
        _log(f"_make_studio_with_flux error: {exc}")
        return False, err


def _do_cutout(image_bytes: bytes):
    """rembg background removal — fallback when Gemini image editing is unavailable."""
    try:
        from rembg import remove
        from PIL import Image
    except ImportError:
        _log("rembg or PIL unavailable")
        return None
    try:
        fg_bytes = remove(image_bytes)
    except Exception as exc:
        _log(f"rembg failed: {exc}")
        return None
    if not fg_bytes or len(fg_bytes) < 1000:
        return None
    try:
        return Image.open(io.BytesIO(fg_bytes)).convert("RGBA")
    except Exception as exc:
        _log(f"failed to open rembg output: {exc}")
        return None


# ── Studio path ───────────────────────────────────────────────────────────────

def make_studio_ready(
    image_bytes: bytes, output_path: Path,
) -> tuple[bool, str]:
    ok, result = make_studio_ready_bytes(image_bytes)
    if not ok:
        return False, result  # type: ignore[return-value]
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result)  # type: ignore[arg-type]
        return True, str(output_path)
    except Exception as exc:
        return False, f"Failed to save studio photo: {exc}"


def make_studio_ready_bytes(image_bytes: bytes) -> tuple[bool, bytes | str]:
    """Transform pet photo into studio portrait.

    Priority order:
    1. FLUX.1-Kontext via Hugging Face — best quality, preserves fur detail,
       edits the image in-context without cutout artefacts.
    2. rembg + flat colour backdrop — fallback when HF_TOKEN is missing or
       the HF monthly credit quota is exhausted.
    """
    if is_hf_configured():
        ok, result = _make_studio_with_flux(image_bytes)
        if ok:
            return True, result
        _log(f"FLUX studio failed ({result}), falling back to rembg")

    # rembg fallback: remove background and place on neutral backdrop
    try:
        from PIL import Image
        bg_color = (220, 225, 235)   # soft cool-grey default
        fg = _do_cutout(image_bytes)
        if fg is None:
            return _studio_plain_fallback(image_bytes, bg_color)
        bg = Image.new("RGBA", fg.size, bg_color + (255,))
        bg.paste(fg, (0, 0), fg)
        final = bg.convert("RGB")
        out = io.BytesIO()
        final.save(out, "PNG")
        _log("Studio via rembg fallback succeeded")
        return True, out.getvalue()
    except ImportError:
        return _studio_plain_fallback(image_bytes, (220, 225, 235))


def _studio_plain_fallback(image_bytes: bytes, bg_color: tuple) -> tuple[bool, bytes | str]:
    """Last-resort fallback: return original image if all else fails."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        out = io.BytesIO()
        img.save(out, "PNG")
        return True, out.getvalue()
    except Exception as exc:
        return False, f"Studio fallback error: {exc}"


# ── Text-to-Speech (REST) ─────────────────────────────────────────────────────

def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 24000,
                channels: int = 1, sample_width: int = 2) -> bytes:
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def text_to_speech(text: str, voice: str = "Aoede") -> tuple[bool, bytes | str]:
    """Convert text to speech using Gemini 2.5 Flash TTS (REST).
    Returns (success, wav_bytes) or (False, error_message).
    """
    key = _get_api_key()
    if not key:
        return False, "Gemini API key not configured."
    try:
        import urllib.request
        import json as _json
        import base64 as _b64

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash-preview-tts:generateContent?key={key}"
        )
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": voice}
                    }
                },
            },
        }
        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = _json.loads(resp.read())

        audio_b64 = (
            body["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        )
        pcm_bytes = _b64.b64decode(audio_b64)
        return True, _pcm_to_wav(pcm_bytes)
    except Exception as exc:
        _log(f"TTS error: {exc}")
        return False, f"TTS error: {exc}"


# ── Audio transcription ───────────────────────────────────────────────────────

def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> tuple[bool, str]:
    """Transcribe audio using Gemini 2.5 Flash multimodal."""
    key = _get_api_key()
    if not key:
        return False, "Gemini API key not configured."
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                "Transcribe this audio recording. Output only the transcribed text, no preamble or commentary.",
            ],
        )
        return True, response.text.strip()
    except Exception as exc:
        _log(f"transcribe_audio error: {exc}")
        return False, f"Transcription error: {exc}"


# ── Smart pet matching — deterministic scoring + Gemini query parser ──────────

_QUERY_PARSE_PROMPT = """You are a pet adoption search assistant. Parse the user's natural-language query
into structured JSON filters and preferences for matching pet listings.

Return ONLY valid JSON in this exact shape (no extra text):
{
  "hard_filters": {
    "type": null,
    "max_age_months": null,
    "max_fee": null,
    "vaccinated": null,
    "sterilized": null,
    "dewormed": null,
    "gender": null,
    "maturity_size": null,
    "health": null
  },
  "soft_preferences": {
    "temperament": [],
    "energy_level": null,
    "housing_fit": [],
    "experience_required": null,
    "special_needs": null,
    "keywords": []
  },
  "must_have": [],
  "nice_to_have": [],
  "exclude": []
}

Rules:
- type: 1=Dog, 2=Cat, null=any
- max_age_months: integer or null
- max_fee: number or null (0 means free)
- vaccinated/sterilized/dewormed: 1=yes, 2=no, null=any
- gender: 1=male, 2=female, null=any
- maturity_size: 1=small, 2=medium, 3=large, 4=xlarge, null=any
- health: 1=healthy, 2=minor_injury, 3=serious_injury, null=any
- energy_level: "low", "medium", "high", or null
- housing_fit: array of "apartment", "house", "garden"
- temperament: array of keywords like "calm", "playful", "affectionate", "independent", "social"

IMPORTANT — normalise informal, grammatically incorrect or synonym language:
- "childs", "kids", "child", "babies" → keywords: ["children", "child friendly", "kids"]
- "little house", "small home", "small flat", "tiny apartment", "small space" → housing_fit: ["apartment"], keywords: ["small home"]
- "good to my childs" / "good with kids" / "suitable for children" → keywords: ["child friendly", "children"]
- "not aggressive" / "gentle" / "sweet" → temperament: ["calm", "gentle"]
- "active" / "loves to play" / "energetic" → temperament: ["playful"], energy_level: "high"
- "lazy" / "chill" / "relaxed" → temperament: ["calm"], energy_level: "low"
- "free" / "no fee" / "no charge" / "no adoption fee" → max_fee: 0
- "puppy" / "kitten" / "young" → max_age_months: 12
- Always add canonical synonyms to keywords (e.g. "child friendly" AND "children" when the query implies children)
- Normalise typos and plural/singular forms before extracting values
"""


def _parse_query_with_gemini(query: str) -> Optional[dict]:
    """Use Gemini to parse a natural-language pet query into structured JSON."""
    key = _get_api_key()
    if not key:
        return None
    try:
        from google import genai
        from google.genai import types
        import json as _json
        import re as _re

        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f'User query: "{query}"',
            config=types.GenerateContentConfig(system_instruction=_QUERY_PARSE_PROMPT),
        )
        text = response.text.strip()
        # Extract JSON from response
        m = _re.search(r'\{[\s\S]*\}', text)
        if m:
            return _json.loads(m.group())
    except Exception as exc:
        _log(f"_parse_query_with_gemini error: {exc}")
    return None


# ── Synonym groups for semantic keyword matching ──────────────────────────────
# Each group maps a canonical concept to its aliases. When checking if a
# description "contains" a concept we check ALL aliases in the group.
_SYNONYM_GROUPS: list[list[str]] = [
    # Children / family
    ["children", "child", "childs", "kids", "kid", "child friendly",
     "child-friendly", "kid-friendly", "good with children", "good with kids",
     "safe for children", "safe for kids", "family friendly", "family-friendly",
     "suitable for children", "suitable for kids", "toddler", "baby"],
    # Small home / apartment
    ["apartment", "flat", "small flat", "small apartment", "little house",
     "small home", "small place", "small space", "tiny home", "compact home",
     "indoor", "house"],
    # Calm / gentle
    ["calm", "gentle", "quiet", "relaxed", "easy-going", "mellow", "docile",
     "laid-back", "placid", "sweet-natured", "mild"],
    # Playful / energetic
    ["playful", "energetic", "active", "lively", "bouncy", "spirited",
     "athletic", "sporty", "loves to play", "high energy"],
    # Vaccinated
    ["vaccinated", "vaccination", "shots", "immunized", "up to date",
     "fully vaccinated"],
    # Dog
    ["dog", "dogs", "puppy", "puppies", "pup", "pups", "canine", "doggy"],
    # Cat
    ["cat", "cats", "kitten", "kittens", "kitty", "feline"],
]


def _synonyms_of(word: str) -> list[str]:
    """Return all synonyms for a word including the word itself."""
    w = word.lower()
    for group in _SYNONYM_GROUPS:
        if w in group:
            return group
    return [w]


def _semantic_match(keyword: str, text: str) -> bool:
    """Return True if the text contains the keyword or any of its synonyms."""
    for syn in _synonyms_of(keyword.lower()):
        if syn in text:
            return True
    return False


def _parse_query_fallback(query: str) -> dict:
    """Deterministic keyword-based fallback when Gemini is unavailable."""
    q = query.lower()
    hard_filters: dict = {
        "type": None, "max_age_months": None, "max_fee": None,
        "vaccinated": None, "sterilized": None, "dewormed": None,
        "gender": None, "maturity_size": None, "health": None,
    }
    soft: dict = {
        "temperament": [], "energy_level": None,
        "housing_fit": [], "experience_required": None,
        "special_needs": None, "keywords": [],
    }

    # Type
    if any(w in q for w in ["dog", "dogs", "puppy", "puppies", "pup", "canine"]):
        hard_filters["type"] = 1
    elif any(w in q for w in ["cat", "cats", "kitten", "kittens", "kitty", "feline"]):
        hard_filters["type"] = 2

    # Fee
    if any(w in q for w in ["free", "no fee", "no adoption fee", "no charge", "without fee"]):
        hard_filters["max_fee"] = 0

    # Health flags
    if any(w in q for w in ["vaccinated", "vaccination", "shots", "immunized"]):
        hard_filters["vaccinated"] = 1
    if any(w in q for w in ["sterilized", "neutered", "spayed", "fixed"]):
        hard_filters["sterilized"] = 1

    # Size
    if any(w in q for w in ["small", "tiny", "little", "compact", "mini"]):
        hard_filters["maturity_size"] = 1
    elif any(w in q for w in ["large", "big", "giant", "extra large", "xl"]):
        hard_filters["maturity_size"] = 3

    # Gender
    if "male" in q and "female" not in q:
        hard_filters["gender"] = 1
    elif "female" in q:
        hard_filters["gender"] = 2

    # Age
    if any(w in q for w in ["puppy", "kitten", "young", "baby", "junior"]):
        hard_filters["max_age_months"] = 12

    # Temperament
    if any(w in q for w in ["calm", "quiet", "gentle", "relaxed", "chill", "easy"]):
        soft["temperament"].append("calm")
        soft["energy_level"] = "low"
    if any(w in q for w in ["playful", "energetic", "active", "lively", "sporty"]):
        soft["temperament"].append("playful")
        soft["energy_level"] = "high"

    # Housing
    if any(w in q for w in ["apartment", "flat", "small flat", "little house",
                             "small home", "small space", "tiny", "indoor"]):
        soft["housing_fit"].append("apartment")
        soft["keywords"].append("apartment")

    # Children — capture many informal variants
    if any(w in q for w in ["children", "childs", "child", "kids", "kid",
                             "family", "toddler", "baby", "babies"]):
        soft["keywords"] += ["children", "child friendly", "kids"]

    # Cats / dogs coexistence
    if any(w in q for w in ["good with cats", "lives with cats", "cat friendly"]):
        soft["keywords"].append("good with cats")
    if any(w in q for w in ["good with dogs", "lives with dogs", "dog friendly"]):
        soft["keywords"].append("good with dogs")

    return {
        "hard_filters": hard_filters,
        "soft_preferences": soft,
        "must_have": [],
        "nice_to_have": [],
        "exclude": [],
    }


def _score_listing(listing: dict, parsed: dict) -> float:
    """
    Deterministic compatibility scoring with synonym-aware matching.

    compatibility_score =
        0.40 * hard_filter_match_score +
        0.30 * soft_preference_match_score +
        0.20 * description_keyword_match_score +
        0.10 * lifestyle_match_score
    """
    hf = parsed.get("hard_filters", {})
    soft = parsed.get("soft_preferences", {})
    exclude = [k.lower() for k in parsed.get("exclude", [])]

    desc = (
        (listing.get("description_improved") or listing.get("description") or "")
        .lower()
    )
    # Also include pet name in the text corpus for matching
    name = (listing.get("pet_name") or "").lower()
    full_text = desc + " " + name

    # ── Hard filter match (0-1) ───────────────────────────────────────────────
    hf_checks = []
    if hf.get("type") is not None:
        hf_checks.append(listing.get("type") == hf["type"])
    if hf.get("max_age_months") is not None:
        hf_checks.append((listing.get("age") or 0) <= hf["max_age_months"])
    if hf.get("max_fee") is not None:
        hf_checks.append((listing.get("fee") or 0) <= hf["max_fee"])
    if hf.get("vaccinated") is not None:
        hf_checks.append(listing.get("vaccinated") == hf["vaccinated"])
    if hf.get("sterilized") is not None:
        hf_checks.append(listing.get("sterilized") == hf["sterilized"])
    if hf.get("dewormed") is not None:
        hf_checks.append(listing.get("dewormed") == hf["dewormed"])
    if hf.get("gender") is not None:
        hf_checks.append(listing.get("gender") == hf["gender"])
    if hf.get("maturity_size") is not None:
        hf_checks.append(listing.get("maturity_size") == hf["maturity_size"])
    if hf.get("health") is not None:
        hf_checks.append(listing.get("health") == hf["health"])

    hard_score = (sum(hf_checks) / len(hf_checks)) if hf_checks else 1.0

    # ── Soft preference match (0-1) — synonym-aware ───────────────────────────
    soft_checks = []
    temperament = [t.lower() for t in soft.get("temperament", [])]
    keywords = [k.lower() for k in soft.get("keywords", [])]

    listing_temperament = (listing.get("temperament_tags") or "").lower()
    listing_energy = (listing.get("energy_level") or "").lower()
    listing_housing = (listing.get("housing_fit") or "").lower()

    for t in temperament:
        soft_checks.append(
            _semantic_match(t, listing_temperament) or _semantic_match(t, full_text)
        )

    if soft.get("energy_level"):
        wanted = soft["energy_level"].lower()
        if listing_energy:
            soft_checks.append(listing_energy == wanted)
        else:
            if wanted == "low":
                soft_checks.append(_semantic_match("calm", full_text))
            elif wanted == "high":
                soft_checks.append(_semantic_match("playful", full_text))
            else:
                soft_checks.append(True)

    housing_wants = [h.lower() for h in soft.get("housing_fit", [])]
    for h in housing_wants:
        if listing_housing:
            soft_checks.append(_semantic_match(h, listing_housing))
        else:
            soft_checks.append(_semantic_match(h, full_text))

    soft_score = (sum(soft_checks) / len(soft_checks)) if soft_checks else 0.5

    # ── Description keyword match (0-1) — synonym-aware ──────────────────────
    desc_keywords = list(set(temperament + keywords))
    if desc_keywords:
        hits = sum(1 for kw in desc_keywords if _semantic_match(kw, full_text))
        desc_score = min(1.0, hits / len(desc_keywords))
    else:
        desc_score = 0.5

    # ── Lifestyle match (0-1) ─────────────────────────────────────────────────
    lifestyle_score = 0.5
    children_wanted = any(_semantic_match(k, "children kids family") for k in keywords)
    if children_wanted:
        good_children = listing.get("good_with_children")
        if good_children is not None:
            lifestyle_score = 1.0 if good_children == 1 else 0.1
        elif _semantic_match("children", full_text):
            lifestyle_score = 0.85

    # ── Exclude keywords penalty ──────────────────────────────────────────────
    exclude_penalty = 0.0
    for ex in exclude:
        if _semantic_match(ex, full_text):
            exclude_penalty += 0.4
    exclude_penalty = min(1.0, exclude_penalty)

    # ── Final formula ─────────────────────────────────────────────────────────
    score = (
        0.40 * hard_score +
        0.30 * soft_score +
        0.20 * desc_score +
        0.10 * lifestyle_score
    ) * (1.0 - exclude_penalty)

    return max(0.0, min(1.0, score))


def smart_match_pets(query: str, listings: list[dict]) -> list[dict]:
    """Rank listings by compatibility with a natural-language query.

    Returns the listings list sorted by compatibility_percentage (desc),
    with each listing dict augmented with a 'compatibility_percentage' key.
    Falls back to original order if query is empty.
    """
    if not listings or not query.strip():
        return listings

    # Parse query via Gemini (or fallback)
    parsed = _parse_query_with_gemini(query) if is_configured() else None
    if not parsed:
        parsed = _parse_query_fallback(query)

    # Score each listing
    scored = []
    for lst in listings:
        score = _score_listing(lst, parsed)
        pct = round(score * 100)
        entry = dict(lst)
        entry["compatibility_percentage"] = pct
        scored.append((pct, entry))

    # Sort descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored]