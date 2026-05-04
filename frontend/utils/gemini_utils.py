"""
Gemini AI utilities for AdoptSense.

Studio photo pipeline — two local variants the user picks per upload:

  Bokeh — keeps original background but heavily blurs it (large-aperture
          look). Pet stays sharp on top. Realistic, photographic. Best
          when the original setting is pleasant (park, home, garden).

  Studio — replaces background entirely with a Gemini-suggested backdrop
           colour + radial vignette + drop shadow. Best when the original
           background is unflattering (cage, dirty floor, harsh wall).

Both variants share the same cutout step (rembg + smart cleanup), so the
foreground pet looks identical in both — only the backdrop differs.

Cutout cleanup:
- isnet-general-use (much better on animals than default u2net)
- NO alpha-matting (it washes out light-coloured pets)
- Smart alpha cleanup: keep all confident pixels (alpha >= 120) AND any
  pixel directly connected to a confident region (fixes missing limbs).
  See _smart_alpha_clean for details.

The description / colour / sticker functions are unchanged from Simon's
original.
"""
import io
import os
import sys
import traceback
from pathlib import Path
from typing import Optional

import streamlit as st

_GEMINI_API_KEY: Optional[str] = None


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


# ── Description improvement (unchanged) ──────────────────────────────────────

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
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=_DESCRIPTION_SYSTEM,
        )
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
        char_text = "\n".join(char_lines)
        prompt = (
            f"Pet characteristics:\n{char_text}\n\n"
            f"Original description:\n{raw_description or '(none provided)'}\n\n"
            "Please write an improved adoption description."
        )
        parts = []
        if image_bytes:
            parts.append({"mime_type": image_mime, "data": image_bytes})
        parts.append(prompt)
        response = model.generate_content(parts)
        return True, response.text.strip()
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "ResourceExhausted" in msg or "Quota exceeded" in msg:
            return False, (
                "Gemini quota exceeded — your listing has been saved without AI description "
                "improvement. Try again later or check your Gemini API plan."
            )
        return False, f"Gemini error: {exc}"


def get_studio_bg_color(image_bytes: bytes) -> tuple[bool, tuple[int, int, int]]:
    key = _get_api_key()
    if not key:
        return False, (240, 240, 245)
    try:
        import google.generativeai as genai
        import json
        import re
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        prompt = (
            "You are a professional pet photographer. "
            "Look at this pet photo and suggest the single best solid studio backdrop colour "
            "that will complement the pet's fur/coat and make the animal stand out beautifully. "
            "Avoid colours that clash with or are too similar to the pet's main colour. "
            "Prefer soft, muted, photogenic tones. "
            "Respond with ONLY a JSON object, no other text. "
            "Example: {\"r\": 220, \"g\": 235, \"b\": 250}"
        )
        parts = [{"mime_type": "image/jpeg", "data": image_bytes}, prompt]
        response = model.generate_content(parts)
        text = response.text.strip()
        m = re.search(r'\{[^}]+\}', text)
        if m:
            obj = json.loads(m.group())
            r = max(0, min(255, int(obj.get("r", 240))))
            g = max(0, min(255, int(obj.get("g", 240))))
            b = max(0, min(255, int(obj.get("b", 245))))
            return True, (r, g, b)
    except Exception:
        pass
    return False, (240, 240, 245)


# ════════════════════════════════════════════════════════════════════════════
# Cutout (shared by Bokeh + Studio)
# ════════════════════════════════════════════════════════════════════════════

_REMBG_SESSIONS: dict = {}


def _get_rembg_session(model_name: str = "isnet-general-use"):
    if model_name in _REMBG_SESSIONS:
        return _REMBG_SESSIONS[model_name]
    from rembg import new_session
    _log(f"loading rembg model '{model_name}'")
    sess = new_session(model_name)
    _REMBG_SESSIONS[model_name] = sess
    _log(f"rembg model '{model_name}' loaded")
    return sess


def _do_cutout(image_bytes: bytes):
    """Default rembg.remove() — nothing else. Simon's original approach.

    History note: I tried isnet, alpha-matting, hard thresholds, flood-fill,
    saturation/contrast boosts, etc. Every "improvement" made the result
    worse on real pet photos. The default u2net model with no parameters
    and no post-processing produced the cleanest result. Keeping it that
    way.
    """
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
        _log("rembg returned empty result")
        return None
    try:
        return Image.open(io.BytesIO(fg_bytes)).convert("RGBA")
    except Exception as exc:
        _log(f"failed to open rembg output: {exc}")
        return None


def _smart_alpha_clean(rgba_img):
    """Keep confident foreground + grow into candidate pixels via flood-fill.

    rembg often produces "weak" alpha (30-120) on two kinds of pixels:
      a) genuine soft edges (fur, whiskers) — keep
      b) thin body parts (legs, tail tips) — keep, or get "missing leg" bug
      c) noise far from the pet — drop

    Strategy: start with confident pixels (alpha >= 120). Then iteratively
    expand into adjacent candidate pixels (alpha >= 30), one ring per
    iteration, until no more candidates touch the kept set. This walks
    along connected limbs naturally — even long thin ones — but never
    jumps to noise that has no path back to the body.

    Uses scipy if available (fast). Falls back to a Python loop otherwise.
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return rgba_img

    arr = np.array(rgba_img)
    alpha = arr[:, :, 3]

    confident = alpha >= 120
    candidate = (alpha >= 30) & (alpha < 120)

    try:
        from scipy import ndimage
        # Connected-component label of (confident OR candidate). Any
        # component that contains at least one confident pixel survives.
        all_fg = confident | candidate
        labels, n_components = ndimage.label(all_fg)
        if n_components == 0:
            keep = confident
        else:
            # Find which component IDs contain confident pixels
            component_has_confident = np.zeros(n_components + 1, dtype=bool)
            confident_labels = labels[confident]
            component_has_confident[confident_labels] = True
            keep = component_has_confident[labels]
    except ImportError:
        # Manual flood-fill via repeated dilation, stop when stable
        keep = confident.copy()
        for _ in range(50):  # safety cap
            shifted_up = np.roll(keep, -1, axis=0)
            shifted_dn = np.roll(keep, 1, axis=0)
            shifted_lf = np.roll(keep, -1, axis=1)
            shifted_rt = np.roll(keep, 1, axis=1)
            neighbour = shifted_up | shifted_dn | shifted_lf | shifted_rt
            new_keep = keep | (candidate & neighbour)
            if np.array_equal(new_keep, keep):
                break
            keep = new_keep

    new_alpha = np.where(keep, 255, 0).astype(np.uint8)
    arr[:, :, 3] = new_alpha
    return Image.fromarray(arr, "RGBA")


def _enhance_subject(rgba_img):
    """Modest saturation + contrast bump."""
    try:
        from PIL import Image, ImageEnhance
        r, g, b, a = rgba_img.split()
        rgb = Image.merge("RGB", (r, g, b))
        rgb = ImageEnhance.Color(rgb).enhance(1.10)
        rgb = ImageEnhance.Contrast(rgb).enhance(1.05)
        nr, ng, nb = rgb.split()
        return Image.merge("RGBA", (nr, ng, nb, a))
    except Exception:
        return rgba_img


# ════════════════════════════════════════════════════════════════════════════
# Bokeh path — sharp pet on a blurred version of the original background
# ════════════════════════════════════════════════════════════════════════════

def make_bokeh_bytes(image_bytes: bytes) -> tuple[bool, bytes | str]:
    """Sharp pet on a blurred version of its own original background.

    Same minimal cutout as Studio — just paste it back on the blurred
    original. No shadow, no darkening, no enhancement. Less is more.
    """
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        return False, "PIL not available"

    fg = _do_cutout(image_bytes)
    if fg is None:
        return False, "Background removal failed — please try Studio mode."

    try:
        original = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        if original.size != fg.size:
            original = original.resize(fg.size, Image.LANCZOS)
        blur_radius = max(20, min(fg.size) // 25)
        blurred_bg = original.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        blurred_bg = blurred_bg.convert("RGBA")
    except Exception as exc:
        _log(f"Bokeh background prep failed: {exc}")
        return False, f"Background blur failed: {exc}"

    try:
        blurred_bg.paste(fg, (0, 0), fg)
        final = blurred_bg.convert("RGB")
        out = io.BytesIO()
        final.save(out, "PNG")
        _log("Bokeh succeeded")
        return True, out.getvalue()
    except Exception as exc:
        _log(f"Bokeh composition failed: {exc}")
        return False, f"Bokeh composition error: {exc}"


def make_bokeh(image_bytes: bytes, output_path: Path) -> tuple[bool, str]:
    ok, result = make_bokeh_bytes(image_bytes)
    if not ok:
        return False, result  # type: ignore[return-value]
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result)  # type: ignore[arg-type]
        return True, str(output_path)
    except Exception as exc:
        return False, f"Failed to save bokeh photo: {exc}"


# ════════════════════════════════════════════════════════════════════════════
# Studio path — sharp pet on a Gemini-suggested replacement backdrop
# ════════════════════════════════════════════════════════════════════════════

def make_studio_ready(
    image_bytes: bytes, output_path: Path, bg_color: tuple = (240, 240, 245),
) -> tuple[bool, str]:
    ok, result = make_studio_ready_bytes(image_bytes, bg_color)
    if not ok:
        return False, result  # type: ignore[return-value]
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result)  # type: ignore[arg-type]
        return True, str(output_path)
    except Exception as exc:
        return False, f"Failed to save studio photo: {exc}"


def make_studio_ready_bytes(
    image_bytes: bytes, bg_color: tuple = (240, 240, 245),
) -> tuple[bool, bytes | str]:
    """Pet on a flat coloured backdrop. Plain composition, no extra effects."""
    try:
        from PIL import Image
    except ImportError:
        return _studio_fallback_bytes(image_bytes, bg_color)

    fg = _do_cutout(image_bytes)
    if fg is None:
        return _studio_fallback_bytes(image_bytes, bg_color)

    # Flat coloured backdrop — no vignette, no gradient. Matches the
    # original Simon-era pipeline that produced the cleanest results.
    bg = Image.new("RGBA", fg.size, bg_color + (255,))
    bg.paste(fg, (0, 0), fg)
    final = bg.convert("RGB")
    out = io.BytesIO()
    final.save(out, "PNG")
    _log("Studio succeeded")
    return True, out.getvalue()


def make_sticker(image_bytes: bytes) -> tuple[bool, bytes]:
    try:
        from rembg import remove
    except ImportError:
        return True, image_bytes
    try:
        try:
            sess = _get_rembg_session("isnet-general-use")
            result = remove(image_bytes, session=sess)
        except Exception:
            result = remove(image_bytes)
        return True, result
    except Exception:
        return False, b""


def _make_studio_bg(size: tuple, base_color: tuple):
    from PIL import Image
    try:
        import numpy as np
        w, h = size
        r0, g0, b0 = base_color
        cx, cy = w / 2, h / 2
        max_dist = (cx ** 2 + cy ** 2) ** 0.5
        y_idx, x_idx = np.indices((h, w), dtype=np.float32)
        dist = np.sqrt((x_idx - cx) ** 2 + (y_idx - cy) ** 2) / max_dist
        brightness = 1.05 - dist * 0.27
        arr = np.zeros((h, w, 4), dtype=np.uint8)
        arr[:, :, 0] = np.clip(r0 * brightness, 0, 255).astype(np.uint8)
        arr[:, :, 1] = np.clip(g0 * brightness, 0, 255).astype(np.uint8)
        arr[:, :, 2] = np.clip(b0 * brightness, 0, 255).astype(np.uint8)
        arr[:, :, 3] = 255
        return Image.fromarray(arr, "RGBA")
    except ImportError:
        return Image.new("RGBA", size, base_color + (255,))


def _build_drop_shadow(fg_rgba):
    from PIL import Image, ImageFilter
    w, h = fg_rgba.size
    alpha = fg_rgba.split()[-1]
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_solid = Image.new("RGBA", (w, h), (20, 20, 30, 110))
    shadow.paste(shadow_solid, (0, 0), alpha)
    blur_radius = max(8, min(w, h) // 60)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    offset_x = max(4, w // 200)
    offset_y = max(6, h // 120)
    offset_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    offset_layer.paste(shadow, (offset_x, offset_y), shadow)
    return offset_layer


def _studio_fallback_bytes(image_bytes: bytes, bg_color: tuple):
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        bg = Image.new("RGB", img.size, bg_color)
        out = io.BytesIO()
        bg.save(out, "PNG")
        return True, out.getvalue()
    except Exception as exc:
        return False, f"PIL fallback error: {exc}"


def _studio_fallback_pil(image_bytes: bytes, output_path: Path, bg_color: tuple):
    ok, result = _studio_fallback_bytes(image_bytes, bg_color)
    if not ok:
        return False, result  # type: ignore[return-value]
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result)  # type: ignore[arg-type]
        return True, str(output_path)
    except Exception as exc:
        return False, f"Save error: {exc}"


# ════════════════════════════════════════════════════════════════════════════
# Text-to-Speech  (gemini-2.5-flash-preview-tts via REST)
# ════════════════════════════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════════════════════════════
# Audio transcription  (gemini-2.5-flash multimodal)
# ════════════════════════════════════════════════════════════════════════════

def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> tuple[bool, str]:
    """Transcribe audio using Gemini 2.5 Flash multimodal.
    Returns (success, transcript_text) or (False, error_message).
    """
    key = _get_api_key()
    if not key:
        return False, "Gemini API key not configured."
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        parts = [
            {"mime_type": mime_type, "data": audio_bytes},
            "Transcribe this audio recording. Output only the transcribed text, no preamble or commentary.",
        ]
        response = model.generate_content(parts)
        return True, response.text.strip()
    except Exception as exc:
        _log(f"transcribe_audio error: {exc}")
        return False, f"Transcription error: {exc}"


# ════════════════════════════════════════════════════════════════════════════
# Smart pet matching  (gemini-2.5-flash ranking)
# ════════════════════════════════════════════════════════════════════════════

def smart_match_pets(query: str, listings: list[dict]) -> list[int]:
    """Rank listings by how well they match a natural-language query.
    Returns listing IDs sorted best-match-first. Falls back to original order on error.
    """
    if not listings:
        return []
    key = _get_api_key()
    if not key:
        return [lst["id"] for lst in listings]
    try:
        import google.generativeai as genai
        import json as _json
        import re as _re
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")

        summaries = []
        for lst in listings:
            type_str = {1: "Dog", 2: "Cat"}.get(lst.get("type", 0), "Other")
            gender_str = {1: "Male", 2: "Female", 3: "Mixed"}.get(lst.get("gender", 1), "")
            age_m = lst.get("age", 0) or 0
            age_str = f"{int(age_m / 12)}y" if age_m >= 12 else f"{int(age_m)}m"
            size_str = {1: "Small", 2: "Medium", 3: "Large", 4: "XL"}.get(
                lst.get("maturity_size", 2), "Medium"
            )
            vacc_str = {1: "vaccinated", 2: "not vaccinated"}.get(lst.get("vaccinated", 3), "")
            ster_str = {1: "sterilized", 2: "not sterilized"}.get(lst.get("sterilized", 3), "")
            hlth_str = {1: "healthy", 2: "minor injury", 3: "serious injury"}.get(
                lst.get("health", 1), "healthy"
            )
            fee_str = "free" if (lst.get("fee") or 0) == 0 else f"fee {lst.get('fee')}"
            desc = (lst.get("description_improved") or lst.get("description") or "")[:200]
            name = lst.get("pet_name") or "Unknown"
            summaries.append(
                f'ID:{lst["id"]} | {name} | {type_str} {gender_str} {age_str} {size_str} '
                f'| {vacc_str} {ster_str} {hlth_str} | {fee_str} | {desc}'
            )

        prompt = (
            "You are a pet adoption matching assistant. "
            "Rank the following pet listings by how well they match the user's query.\n\n"
            f'User query: "{query}"\n\n'
            f"Pet listings:\n" + "\n".join(summaries) + "\n\n"
            "Return ONLY a JSON array of listing IDs in order from best to worst match. "
            "Example: [42, 17, 5]"
        )
        response = model.generate_content(prompt)
        text = response.text.strip()
        m = _re.search(r'\[[\d,\s]+\]', text)
        if m:
            ranked_ids = _json.loads(m.group())
            valid_ids = {lst["id"] for lst in listings}
            ranked = [i for i in ranked_ids if i in valid_ids]
            ranked_set = set(ranked)
            for lst in listings:
                if lst["id"] not in ranked_set:
                    ranked.append(lst["id"])
            return ranked
    except Exception as exc:
        _log(f"smart_match_pets error: {exc}")
    return [lst["id"] for lst in listings]
