"""
MiMo TTS Client for Wendy NPC Voice Synthesis

Generates audio responses for Wendy's chat messages using
Xiaomi MiMo-V2-TTS API.
"""

import base64
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_MIMO_URL = "https://token-plan-sgp.xiaomimimo.com/v1"
DEFAULT_VOICE = "default_en"
DEFAULT_MODEL = "mimo-v2-tts"


class TTSError(Exception):
    """Custom exception for TTS failures."""
    pass


class MiMoTTSClient:
    """Client for Xiaomi MiMo-V2-TTS API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = DEFAULT_MODEL,
        default_voice: str = DEFAULT_VOICE,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.default_voice = default_voice
        self.timeout = timeout
        self._available = None  # Cache connectivity check

    def _check_connectivity(self) -> bool:
        """Quick connectivity check (cached)."""
        if self._available is not None:
            return self._available

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": "Speak this line."},
                        {"role": "assistant", "content": "test"},
                    ],
                    "audio": {
                        "format": "mp3",
                        "voice": self.default_voice,
                    },
                },
                timeout=10,
            )
            self._available = resp.status_code < 500
        except Exception:
            self._available = False

        return self._available

    def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[bytes]:
        """
        Synthesize speech from text.

        Args:
            text: Text to convert to speech
            voice: Voice identifier (uses default_voice if not specified)

        Returns:
            Audio bytes (mp3) or None if TTS fails
        """
        if not text or not text.strip():
            return None

        voice = voice or self.default_voice

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": "Speak this line."},
                    {"role": "assistant", "content": text},
                ],
                "audio": {
                    "format": "mp3",
                    "voice": voice,
                },
            }

            logger.info(f"TTS request: voice={voice}, text_len={len(text)}")

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                logger.warning(
                    f"TTS API error: {response.status_code} — {response.text[:200]}"
                )
                return None

            data = response.json()

            # Extract base64-encoded audio from response
            try:
                audio_b64 = data["choices"][0]["message"]["audio"]["data"]
                audio_bytes = base64.b64decode(audio_b64)
            except (KeyError, IndexError, ValueError) as e:
                logger.error(f"TTS response parse error: {e}")
                logger.error(f"Response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                if isinstance(data, dict) and "choices" in data and data["choices"]:
                    logger.error(f"First choice keys: {list(data['choices'][0].keys())}")
                    if "message" in data["choices"][0]:
                        logger.error(f"Message keys: {list(data['choices'][0]['message'].keys())}")
                return None

            logger.info(f"TTS generated: {len(audio_bytes)} bytes")
            return audio_bytes

        except requests.exceptions.Timeout:
            logger.warning(f"TTS request timed out after {self.timeout}s")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"TTS connection error: {e}")
            return None
        except Exception as e:
            logger.error(f"TTS unexpected error: {e}")
            return None

    def get_available_voices(self) -> list:
        """Return list of known voice identifiers."""
        return [
            "default_en",
            "English_expressive_narrator",
            "English_radiant_girl",
            "English_magnetic_voiced_man",
            "English_compelling_lady1",
        ]


def create_tts_client(config: dict) -> Optional[MiMoTTSClient]:
    """
    Factory function to create TTS client from config.

    Returns None if TTS is disabled or misconfigured.
    """
    tts_config = config.get("tts", {})

    if not tts_config.get("enabled", False):
        logger.info("TTS is disabled in config")
        return None

    api_key = tts_config.get("api_key", "")
    if not api_key:
        logger.warning("TTS enabled but no api_key configured")
        return None

    return MiMoTTSClient(
        base_url=tts_config.get("base_url", DEFAULT_MIMO_URL),
        api_key=api_key,
        model=tts_config.get("model", DEFAULT_MODEL),
        default_voice=tts_config.get("default_voice", DEFAULT_VOICE),
        timeout=tts_config.get("timeout_seconds", 30),
    )
