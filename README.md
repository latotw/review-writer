# AI Review Writer

A single-page Streamlit app for preparing a grounded Google Maps review prompt, handing it off to ChatGPT manually, and copying the review back for editing. The app does not call any AI API, does not require an API key, and does not publish reviews.

## Run locally

Python 3.11 or newer is required.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

No `.env` file or API credentials are needed. `.env.example` is retained as a reminder that this app has no key settings.

## Workflow

1. Enter the place name and any known category, address, city, and Google Maps URL.
2. Add up to five photos by dragging, browsing, or using the clipboard paste button.
3. Write personal experience notes.
4. Generate and edit the place-specific prompt.
5. Copy the prompt, open [ChatGPT](https://chatgpt.com) in a new tab, paste it yourself, and attach the photos yourself.
6. Paste ChatGPT's review into the app, edit it if desired, and copy the final text.
7. Open the Google Maps listing and publish the review yourself if you choose.

Opening ChatGPT does not transfer the prompt, photos, or notes. ChatGPT analyzes photos only after you manually attach them and submit the prompt in your own account. Your ChatGPT subscription's usage limits and feature availability still apply.

## Photo privacy and clipboard limits

Photos are resized locally for previews and kept in the current Streamlit session only. This application does not send photos or personal notes to an AI service or another external API, and it does not save them permanently. When running locally, Streamlit receives the selected image in the local app session so it can show the preview. Photos only reach ChatGPT if you choose to attach them there.

Clipboard paste depends on browser clipboard support, user permission, and a secure context such as `localhost` or HTTPS. Copying from Google Photos may provide a link instead of image data; if paste does not work, save the individual photo and use upload. Drag-and-drop and file upload are available as fallbacks.

## Tests

```bash
python -m unittest discover -s tests -v
```

