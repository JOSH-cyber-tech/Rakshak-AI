import logging
import os
import time

import requests
from dotenv import load_dotenv

try:
    import groq as _groq_sdk
except ImportError:
    _groq_sdk = None

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.1-8b-instant"
OLLAMA_MODEL = "gemma3"
OLLAMA_URL = "http://localhost:11434/api/generate"


class LLMResponse:
    def __init__(self, text: str, engine: str):
        self.text = text
        self.engine = engine

    def __repr__(self):
        return f"LLMResponse(engine={self.engine!r}, text={self.text[:80]!r})"


def _groq_generate(prompt: str) -> LLMResponse:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError("GROQ_API_KEY not configured")

    from groq import Groq

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        timeout=10,
    )
    text = response.choices[0].message.content
    return LLMResponse(text=text, engine="groq")


def _fallback_generate(prompt: str) -> LLMResponse:
    response = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    text = response.json()["response"]
    return LLMResponse(text=text, engine="ollama")


def generate(prompt: str, retries: int = 3) -> LLMResponse:
    for attempt in range(retries):
        try:
            response = _groq_generate(prompt)
            if response and len(response.text.strip()) > 10:
                logger.info("Engine: Groq (%s)", GROQ_MODEL)
                return response
        except Exception as e:
            logger.warning("Groq attempt %d failed: %s", attempt + 1, e)
            time.sleep(1)
    logger.warning("Groq failed after %d attempts — falling back to Ollama/%s", retries, OLLAMA_MODEL)
    return _fallback_generate(prompt)
