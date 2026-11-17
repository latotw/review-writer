"""Local prompt construction and browser-side handoff markup."""

from __future__ import annotations

import html
import io
import json
import re

from PIL import Image, ImageOps


MAX_IMAGE_EDGE = 1600
MAX_IMAGE_BYTES = 4 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}

CHATGPT_REVIEW_INSTRUCTIONS = """You are an experienced travel writer helping me write authentic Google Maps reviews.

First, carefully examine the photos I attach.

Identify only details that are directly visible, such as interior design, seating, lighting, food presentation, architecture, scenery, and visible facilities.

Separate visual observations from my personal experiences.

Never infer taste, service quality, friendliness, actual prices, comfort, or other experiences from photographs alone.

Use my personal notes as the source of actual experiences.

Use Traditional Chinese (Taiwan) as the output language (繁體中文，台灣用語).

Combine confirmed place information, visual observations, and my personal experiences into a natural Traditional Chinese Google Maps review.

Writing style:
- Detailed and observant.
- Authentic and natural.
- Like a thoughtful traveler sharing a real experience.
- Avoid generic marketing language.
- Avoid exaggerated adjectives.
- Avoid repetitive AI-style expressions.
- Prefer approximately 100–200 Chinese characters.
- Never invent experiences or unsupported details.

If my notes are insufficient, ask me one useful clarification question instead of making assumptions."""


def build_chatgpt_prompt(
    place_name: str,
    category: str = "",
    address: str = "",
    city_country: str = "",
    personal_notes: str = "",
    photo_count: int = 0,
) -> str:
    """Build a place-specific prompt. This function makes no network requests."""
    details = [
        f"Place name: {place_name.strip() or 'Not provided'}",
        f"Place category: {category.strip() or 'Not provided'}",
        f"Address: {address.strip() or 'Not provided'}",
        f"City and country: {city_country.strip() or 'Not provided'}",
        "Personal experience notes:\n" + (personal_notes.strip() or "Not provided."),
        (
            f"Photos: I have selected {photo_count} photo(s) in the local application. "
            "I will attach the relevant photos manually in ChatGPT. The local application has not analyzed them."
            if photo_count
            else "Photos: I will attach relevant photos manually in ChatGPT if available."
        ),
    ]
    return (
        CHATGPT_REVIEW_INSTRUCTIONS
        + "\n\nPlace and experience details:\n"
        + "\n\n".join(details)
        + "\n\nPlease analyze only the photos attached to this ChatGPT conversation. "
        "Do not assume that selected local-app photos were transferred here."
    )


def normalize_image(image: Image.Image) -> bytes:
    """Orient, resize and compress an image locally for session preview."""
    image = ImageOps.exif_transpose(image)
    if image.format and image.format.upper() not in ALLOWED_IMAGE_FORMATS:
        raise ValueError("請使用 JPG、PNG 或 WebP 圖片。")
    image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
    if image.mode not in ("RGB", "L"):
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
    elif image.mode == "L":
        image = image.convert("RGB")

    output = io.BytesIO()
    quality = 86
    image.save(output, format="JPEG", quality=quality, optimize=True)
    while output.tell() > MAX_IMAGE_BYTES and quality > 55:
        output = io.BytesIO()
        quality -= 8
        image.save(output, format="JPEG", quality=quality, optimize=True)
    if output.tell() > MAX_IMAGE_BYTES:
        raise ValueError("圖片壓縮後仍過大，請改用較小的圖片。")
    return output.getvalue()


def clipboard_button_html(
    text: str,
    label: str,
    success: str = "Copied ✓",
    element_id: str = "copy-widget",
) -> str:
    """Return a self-contained button that copies text in the user's browser."""
    widget_id = re.sub(r"[^A-Za-z0-9_-]", "-", element_id)
    escaped_text = html.escape(text, quote=False)
    escaped_label = html.escape(label, quote=True)
    success_literal = json.dumps(success, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<!doctype html>
<div style="margin:0;font-family:Arial,sans-serif">
<textarea id="{widget_id}-source" aria-hidden="true" tabindex="-1" style="position:fixed;left:-10000px;top:0">{escaped_text}</textarea>
<button id="{widget_id}-button" type="button" style="width:100%;height:42px;border:1px solid #cbd7ca;border-radius:8px;background:#f5f8f3;color:#315a3a;font-size:14px;font-weight:600;cursor:pointer">{escaped_label}</button>
<script>
const button = document.getElementById('{widget_id}-button');
button.addEventListener('click', async () => {{
  const text = document.getElementById('{widget_id}-source').value;
  try {{
    await navigator.clipboard.writeText(text);
    button.textContent = {success_literal};
  }} catch (error) {{
    const field = document.getElementById('{widget_id}-source');
    field.style.position = 'static'; field.style.left = 'auto'; field.style.width = '100%';
    field.style.height = '80px'; field.select();
    button.textContent = 'Clipboard unavailable — copy the selected text';
  }}
}});
</script>
</div>"""

