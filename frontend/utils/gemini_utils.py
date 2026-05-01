"""
Gemini AI utilities for AdoptSense.
- Improve pet descriptions using Gemini Flash
- Generate studio-ready pet photos (background removal + studio backdrop)
"""
import io
import os
from pathlib import Path
from typing import Optional

import streamlit as st

_GEMINI_API_KEY: Optional[str] = None


def _get_api_key() -> Optional[str]:
    global _GEMINI_API_KEY
    if _GEMINI_API_KEY:
        return _GEMINI_API_KEY
    # Priority: st.secrets → environment variable
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
    """
    Improve a pet description using Gemini.
    Returns (success, improved_text_or_error_message).
    """
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


# ── Studio backdrop colour selection ─────────────────────────────────────────

def get_studio_bg_color(image_bytes: bytes) -> tuple[bool, tuple[int, int, int]]:
    """
    Ask Gemini to suggest an optimal studio backdrop colour for the pet photo.
    Returns (success, (R, G, B)).
    On any error returns (False, (240, 240, 245)) so callers always get a usable colour.
    """
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


# ── Studio-ready photo ────────────────────────────────────────────────────────

def make_studio_ready(
    image_bytes: bytes,
    output_path: Path,
    bg_color: tuple = (240, 240, 245),
) -> tuple[bool, str]:
    """
    Remove pet background and place on a clean studio backdrop.
    Saves result to output_path as PNG.
    Returns (success, message).
    """
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
    image_bytes: bytes,
    bg_color: tuple = (240, 240, 245),
) -> tuple[bool, bytes | str]:
    """
    Remove pet background and place on a clean studio backdrop.
    Returns (success, png_bytes_or_error_message).
    rembg runtime failures (e.g. model-download errors) fall back to PIL compositing.
    """
    try:
        from rembg import remove
        from PIL import Image

        try:
            fg_bytes = remove(image_bytes)
        except Exception:
            # rembg is installed but failed at runtime (network error, model download, etc.)
            # Fall back to plain PIL compositing without background removal.
            return _studio_fallback_bytes(image_bytes, bg_color)

        fg = Image.open(io.BytesIO(fg_bytes)).convert("RGBA")
        bg = _make_studio_bg(fg.size, bg_color)
        bg.paste(fg, (0, 0), fg)
        final = bg.convert("RGB")
        out = io.BytesIO()
        final.save(out, "PNG")
        return True, out.getvalue()
    except ImportError:
        return _studio_fallback_bytes(image_bytes, bg_color)
    except Exception as exc:
        return False, f"Studio processing error: {exc}"


def make_sticker(image_bytes: bytes) -> tuple[bool, bytes]:
    """
    Return PNG bytes with transparent background (sticker format).
    Primary: rembg. Fallback: returns original image.
    """
    try:
        from rembg import remove
        result = remove(image_bytes)
        return True, result
    except ImportError:
        return True, image_bytes
    except Exception:
        return False, b""


def _make_studio_bg(size: tuple, base_color: tuple) -> "Image.Image":
    from PIL import Image
    try:
        import numpy as np
        w, h = size
        r0, g0, b0 = base_color
        # Vertical gradient: slightly darker at top (0.9×) → lighter at bottom (1.0×)
        factors = np.linspace(0.9, 1.0, h, dtype=np.float32)
        r_col = np.clip(r0 * factors, 0, 255).astype(np.uint8)
        g_col = np.clip(g0 * factors, 0, 255).astype(np.uint8)
        b_col = np.clip(b0 * factors, 0, 255).astype(np.uint8)
        arr = np.zeros((h, w, 4), dtype=np.uint8)
        arr[:, :, 0] = r_col[:, np.newaxis]
        arr[:, :, 1] = g_col[:, np.newaxis]
        arr[:, :, 2] = b_col[:, np.newaxis]
        arr[:, :, 3] = 255
        return Image.fromarray(arr, "RGBA")
    except ImportError:
        # numpy unavailable — slow pixel-by-pixel fallback
        w, h = size
        bg = Image.new("RGBA", (w, h))
        for y in range(h):
            factor = 0.9 + 0.1 * (y / h)
            r = int(base_color[0] * factor)
            g = int(base_color[1] * factor)
            b = int(base_color[2] * factor)
            for x in range(w):
                bg.putpixel((x, y), (r, g, b, 255))
        return bg


def _studio_fallback_bytes(
    image_bytes: bytes, bg_color: tuple
) -> tuple[bool, bytes | str]:
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        bg = Image.new("RGB", img.size, bg_color)
        out = io.BytesIO()
        bg.save(out, "PNG")
        return True, out.getvalue()
    except Exception as exc:
        return False, f"PIL fallback error: {exc}"


def _studio_fallback_pil(
    image_bytes: bytes, output_path: Path, bg_color: tuple
) -> tuple[bool, str]:
    ok, result = _studio_fallback_bytes(image_bytes, bg_color)
    if not ok:
        return False, result  # type: ignore[return-value]
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result)  # type: ignore[arg-type]
        return True, str(output_path)
    except Exception as exc:
        return False, f"Save error: {exc}"
