from __future__ import annotations

import hashlib
from io import BytesIO
from urllib.parse import quote_plus, urlparse

import streamlit as st
from PIL import Image
from streamlit_paste_button import paste_image_button

from handoff import build_chatgpt_prompt, clipboard_button_html, normalize_image


st.set_page_config(page_title="AI 評論寫手", page_icon="✍️", layout="centered")

st.markdown(
    """
    <style>
      html, body, [class*="css"] { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
      .block-container { max-width: 800px; padding-top: 2.4rem; padding-bottom: 4rem; }
      .hero { background: linear-gradient(120deg,#f0f5ee 0%,#fbf8f1 100%); padding: 1.55rem 1.8rem; border-radius: 18px; margin-bottom: 1.5rem; border: 1px solid #e8ece3; }
      .eyebrow { text-transform: uppercase; letter-spacing: .12em; color: #52765c; font-weight: 700; font-size: .72rem; }
      .hero h1 { color: #23392a; font-size: 1.85rem; margin: .4rem 0 .3rem; }
      .hero p { color: #647266; margin: 0; }
      .step { color:#4d7657; font-size:.76rem; letter-spacing:.08em; font-weight:700; margin:1.2rem 0 .2rem; }
      div[data-testid="stFileUploader"] { background:#fbfcfa; border:1px dashed #cbd7ca; border-radius:14px; padding:.35rem; }
      .privacy { color:#667168; font-size:.88rem; background:#f4f7f1; padding:.8rem 1rem; border-radius:10px; }
      .stButton > button[kind="primary"] { background:#315a3a; border-color:#315a3a; }
    </style>
    <div class="hero"><div class="eyebrow">A more thoughtful way to remember</div>
      <h1>把一次造訪，寫成真實的分享</h1><p>照片交由你在 ChatGPT 親自查看，真實感受由你來描述。</p></div>
    """,
    unsafe_allow_html=True,
)


def _clear_review() -> None:
    st.session_state.review_version = st.session_state.get("review_version", 0) + 1


for state_key, default in (
    ("photos", []),
    ("photo_fingerprints", set()),
    ("form_version", 0),
    ("prompt_version", 0),
    ("review_version", 0),
    ("upload_version", 0),
    ("paste_version", 0),
):
    if state_key not in st.session_state:
        st.session_state[state_key] = default

version = st.session_state.form_version

st.markdown('<div class="step">01 — PLACE INFORMATION</div>', unsafe_allow_html=True)
st.subheader("Place Information")
place_name = st.text_input("Place name *", placeholder="店家或景點名稱", key=f"place_name_{version}")
place_category = st.text_input("Place category", placeholder="例如：咖啡廳、餐廳、博物館", key=f"place_category_{version}")
place_col1, place_col2 = st.columns(2)
with place_col1:
    place_address = st.text_input("Address", placeholder="知道地址時填寫", key=f"place_address_{version}")
with place_col2:
    place_city = st.text_input("City and country", placeholder="例如：台北，台灣", key=f"place_city_{version}")
maps_url_input = st.text_input("Google Maps URL (optional)", placeholder="貼上此地點的 Google Maps 網址", key=f"maps_url_{version}")

maps_url = ""
parsed_maps = urlparse(maps_url_input.strip())
maps_host = (parsed_maps.hostname or "").lower()
if maps_url_input.strip() and parsed_maps.scheme == "https" and (
    maps_host == "maps.app.goo.gl"
    or maps_host == "maps.google.com"
    or (maps_host.endswith(".google.com") and parsed_maps.path.startswith("/maps"))
):
    maps_url = maps_url_input.strip()
elif maps_url_input.strip():
    st.warning("請輸入 Google Maps 的 https 網址；稍後會以地點名稱搜尋 Google Maps。")
if not maps_url and place_name.strip():
    maps_url = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(place_name.strip())

st.markdown('<div class="step">02 — PHOTO SELECTION AND PREVIEW</div>', unsafe_allow_html=True)
st.subheader("Photo Selection and Preview")
st.markdown(
    '<div class="privacy"><strong>Your photos are not analyzed inside this application. Copy the generated prompt to ChatGPT, then attach your photos there.</strong><br>照片只在本機應用程式的目前工作階段預覽，不會傳送到任何 AI API，也不會永久保存。最多 5 張。</div>',
    unsafe_allow_html=True,
)

paste_col, paste_note = st.columns([1, 2])
with paste_col:
    try:
        pasted = paste_image_button(
            "📋 Paste Image",
            text_color="#315a3a",
            background_color="#edf3eb",
            hover_background_color="#dfeadd",
            key=f"paste_image_{version}_{st.session_state.paste_version}",
            errors="raise",
        )
        if pasted.image_data is not None:
            if len(st.session_state.photos) >= 5:
                st.warning("每篇評論最多使用 5 張照片。")
            else:
                image_bytes = normalize_image(pasted.image_data)
                fingerprint = hashlib.sha256(image_bytes).hexdigest()
                if fingerprint not in st.session_state.photo_fingerprints:
                    st.session_state.photos.append(image_bytes)
                    st.session_state.photo_fingerprints.add(fingerprint)
                    st.rerun()
    except Exception as exc:
        st.caption(f"剪貼簿無法使用：{exc}")
with paste_note:
    st.caption("先複製圖片，再按 Paste Image。瀏覽器需允許剪貼簿存取；如無法貼上，請改用下方拖放或選取。")

uploads = st.file_uploader(
    "Drag and drop or browse photos",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
    key=f"photo_upload_{version}_{st.session_state.upload_version}",
)
if uploads:
    try:
        for uploaded in uploads:
            image_bytes = normalize_image(Image.open(BytesIO(uploaded.getvalue())))
            fingerprint = hashlib.sha256(image_bytes).hexdigest()
            if fingerprint not in st.session_state.photo_fingerprints and len(st.session_state.photos) < 5:
                st.session_state.photos.append(image_bytes)
                st.session_state.photo_fingerprints.add(fingerprint)
    except Exception as exc:
        st.error(f"無法讀取照片：{exc}")
    if len(st.session_state.photos) >= 5 and len(uploads) > len(st.session_state.photos):
        st.info("照片總數已限制為 5 張。")

if st.session_state.photos:
    st.caption(f"{len(st.session_state.photos)} / 5 photos selected")
    thumbnails = st.columns(min(len(st.session_state.photos), 5))
    for index, (column, image_bytes) in enumerate(zip(thumbnails, st.session_state.photos)):
        column.image(image_bytes, use_container_width=True)
        if column.button("Remove", key=f"remove_photo_{version}_{index}"):
            removed = st.session_state.photos.pop(index)
            st.session_state.photo_fingerprints.discard(hashlib.sha256(removed).hexdigest())
            st.session_state.upload_version += 1
            st.session_state.paste_version += 1
            st.rerun()

st.markdown('<div class="step">03 — PERSONAL EXPERIENCE NOTES</div>', unsafe_allow_html=True)
st.subheader("Personal Experience Notes")
personal_notes = st.text_area(
    "Personal experience notes",
    placeholder="Write casually or use keywords. For example: coffee was excellent, quiet atmosphere, friendly staff, close to the station.",
    height=130,
    label_visibility="collapsed",
    key=f"personal_notes_{version}",
)

st.markdown('<div class="step">04 — GENERATE WITH CHATGPT</div>', unsafe_allow_html=True)
st.subheader("Generate with ChatGPT")
st.write("產生一段可編輯的提示詞，再自行複製到 ChatGPT。開啟 ChatGPT 不會自動傳送提示詞或照片。")
if st.button("Generate ChatGPT Prompt", type="primary", use_container_width=True, key=f"generate_prompt_{version}"):
    if not place_name.strip():
        st.error("請先填寫地點名稱。")
    else:
        st.session_state.generated_prompt = build_chatgpt_prompt(
            place_name=place_name,
            category=place_category,
            address=place_address,
            city_country=place_city,
            personal_notes=personal_notes,
            photo_count=len(st.session_state.photos),
        )
        st.session_state.prompt_version += 1
        st.rerun()

if st.session_state.get("generated_prompt"):
    prompt_text = st.text_area(
        "ChatGPT prompt (editable)",
        value=st.session_state.generated_prompt,
        height=360,
        key=f"prompt_text_{st.session_state.prompt_version}",
    )
    prompt_action_col, chatgpt_action_col = st.columns(2)
    with prompt_action_col:
        st.html(
            clipboard_button_html(
                prompt_text,
                "Copy Prompt",
                "Prompt copied ✓",
                element_id=f"prompt-copy-{st.session_state.prompt_version}",
            ),
            unsafe_allow_javascript=True,
        )
    with chatgpt_action_col:
        st.link_button(
            "Open ChatGPT ↗",
            "https://chatgpt.com",
            type="primary",
            use_container_width=True,
            help="Opens ChatGPT in a new tab. Prompt and photos are not transferred.",
        )
    st.caption("在 ChatGPT 對話中手動貼上提示詞，並自行附上照片。你的 ChatGPT 訂閱方案仍受其使用量與功能限制。")

st.markdown('<div class="step">05 — PASTE CHATGPT REVIEW</div>', unsafe_allow_html=True)
st.subheader("Paste ChatGPT Review")
st.caption("ChatGPT 產生評論後，將內容貼到這裡即可編輯及複製。此應用程式不會發布評論。")
review_text = st.text_area(
    "ChatGPT review",
    height=190,
    placeholder="Paste the review ChatGPT generated here…",
    label_visibility="collapsed",
    key=f"review_text_{st.session_state.review_version}",
)
review_action_col, clear_review_col, maps_col = st.columns([1, 1, 1])
with review_action_col:
    st.html(
        clipboard_button_html(
            review_text,
            "Copy Final Review",
            "Review copied ✓",
            element_id=f"review-copy-{st.session_state.review_version}",
        ),
        unsafe_allow_javascript=True,
    )
with clear_review_col:
    st.button("Clear Review", on_click=_clear_review, use_container_width=True)
with maps_col:
    if maps_url:
        st.link_button("Open Google Maps ↗", maps_url, use_container_width=True)
    else:
        st.button("Open Google Maps", disabled=True, use_container_width=True)

