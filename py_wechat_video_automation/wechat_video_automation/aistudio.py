from typing import Dict, Any, Optional
import time
from google import generativeai as genai


class AIStudioClient:
    def __init__(self, api_key: str, model_name: str) -> None:
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def analyze_video(self, file_path: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        uploaded = genai.upload_file(path=file_path)
        # Wait for processing if needed
        while uploaded.state.name == "PROCESSING":
            time.sleep(1)
            uploaded = genai.get_file(uploaded.name)
        if uploaded.state.name != "SUCCEEDED":
            raise RuntimeError(f"Upload failed: {uploaded.state.name}")

        final_prompt = prompt or (
            "Provide a concise summary of the video's content, key scenes, and any text or speech."
        )
        response = self.model.generate_content([uploaded, final_prompt])
        text = response.text if hasattr(response, "text") else str(response)
        return {
            "model": self.model.model_name,
            "file": uploaded.name,
            "analysis_text": text,
        }