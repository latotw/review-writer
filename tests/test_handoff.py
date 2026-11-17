import io
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from streamlit.testing.v1 import AppTest

from handoff import (
    CHATGPT_REVIEW_INSTRUCTIONS,
    build_chatgpt_prompt,
    clipboard_button_html,
    normalize_image,
)


class PromptGenerationTests(unittest.TestCase):
    def test_prompt_includes_place_details_notes_and_manual_photo_instruction(self):
        prompt = build_chatgpt_prompt(
            place_name="山邊咖啡",
            category="咖啡廳",
            address="中山路 10 號",
            city_country="台中，台灣",
            personal_notes="手沖咖啡有果香，靠窗座位很安靜。",
            photo_count=2,
        )

        for detail in (
            "山邊咖啡",
            "咖啡廳",
            "中山路 10 號",
            "台中，台灣",
            "手沖咖啡有果香，靠窗座位很安靜。",
            "selected 2 photo(s)",
            "I will attach the relevant photos manually in ChatGPT",
            "The local application has not analyzed them",
        ):
            self.assertIn(detail, prompt)
        self.assertIn("Traditional Chinese Google Maps review", prompt)

    def test_prompt_includes_all_grounding_and_style_instructions(self):
        prompt = build_chatgpt_prompt("Old Fort", personal_notes="Walked around the courtyard.")

        self.assertIn(CHATGPT_REVIEW_INSTRUCTIONS, prompt)
        self.assertIn("First, carefully examine the photos I attach.", prompt)
        self.assertIn("Traditional Chinese (Taiwan)", prompt)
        self.assertIn("Never infer taste, service quality, friendliness, actual prices", prompt)
        self.assertIn("ask me one useful clarification question", prompt)
        self.assertIn("Place category: Not provided", prompt)
        self.assertIn("Address: Not provided", prompt)
        self.assertIn("Personal experience notes:\nWalked around the courtyard.", prompt)

    def test_prompt_never_claims_local_photo_analysis_or_transfer(self):
        prompt = build_chatgpt_prompt("Test place", photo_count=1)

        self.assertIn("The local application has not analyzed them.", prompt)
        self.assertIn("Do not assume that selected local-app photos were transferred here.", prompt)


class HandoffTests(unittest.TestCase):
    def test_copy_button_contains_prompt_and_clipboard_feedback(self):
        prompt = "Review for & <Cafe>\n咖啡與安靜座位"
        markup = clipboard_button_html(prompt, "Copy Prompt", "Prompt copied ✓")

        self.assertIn("navigator.clipboard.writeText(text)", markup)
        self.assertIn("Prompt copied ✓", markup)
        self.assertIn("Review for &amp; &lt;Cafe&gt;", markup)
        self.assertIn("咖啡與安靜座位", markup)
        self.assertIn("copy-widget-source", markup)
        self.assertIn("copy-widget-button", markup)

    def test_image_normalization_stays_local_and_resizes(self):
        image = Image.new("RGB", (2400, 1200), "white")
        result = normalize_image(image)
        normalized = Image.open(io.BytesIO(result))

        self.assertEqual(normalized.format, "JPEG")
        self.assertLessEqual(max(normalized.size), 1600)

    def test_application_generates_prompt_with_no_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=20).run()
            self.assertEqual(len(app.exception), 0)

            place_name = next(widget for widget in app.text_input if widget.label == "Place name *")
            place_name.set_value("海邊步道")
            app.run()

            generate = next(button for button in app.button if button.label == "Generate ChatGPT Prompt")
            generate.click().run()
            self.assertEqual(len(app.exception), 0)

            prompt_editor = next(widget for widget in app.text_area if widget.label == "ChatGPT prompt (editable)")
            self.assertIn("海邊步道", prompt_editor.value)
            self.assertIn("I will attach relevant photos manually in ChatGPT if available", prompt_editor.value)
            chatgpt_link = next(widget for widget in app.get("link_button") if widget.label == "Open ChatGPT ↗")
            self.assertEqual(chatgpt_link.url, "https://chatgpt.com")


if __name__ == "__main__":
    unittest.main()

