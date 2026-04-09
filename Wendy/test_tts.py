"""
MiMo TTS Offline Test Script

Test the Xiaomi MiMo-V2-TTS API independently from the Wendy app.
Run: python test_tts.py

Outputs mp3 files to tts_output/ for comparison.
"""

import os
import sys
import base64
import json
import requests

# MiMo TTS Configuration
MIMO_API_URL = "https://token-plan-sgp.xiaomimimo.com/v1"
MIMO_API_KEY = "tp-s34sb1kzmw2xaxxzsqj8jh5p7k3woxnjunpdvk9744n40dto"
MIMO_TTS_MODEL = "mimo-v2-tts"

# Test phrases — Wendy speaking in character
TEST_PHRASES = [
    "Well hey there, sugar. I'm Wendy, from Possum Hollow up in eastern Kentucky. You look a little lost — you alright?",
    "My paw's a former coal miner. Had an accident in the mine a few years back. He don't talk about it much, but I can tell it still weighs on him.",
    "You ever been up to the ridge at sunset? Lord, there ain't nothin' like watchin' the sun dip behind them mountains. Makes you feel real small, but in a good way.",
]


def synthesize_speech(text: str, voice: str, output_path: str) -> bool:
    """Call MiMo TTS API and save audio to file."""
    try:
        headers = {
            "Authorization": f"Bearer {MIMO_API_KEY}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": MIMO_TTS_MODEL,
            "messages": [
                {"role": "user", "content": "Speak this line."},
                {"role": "assistant", "content": text}
            ],
            "audio": {
                "format": "mp3",
                "voice": voice,
            }
        }
        
        print(f"  → Requesting TTS with voice: {voice}")
        print(f"  → Text: {text[:60]}...")
        
        response = requests.post(
            f"{MIMO_API_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        
        if response.status_code != 200:
            print(f"  ✗ API returned {response.status_code}: {response.text[:300]}")
            return False
        
        data = response.json()
        audio_b64 = data["choices"][0]["message"]["audio"]["data"]
        audio_bytes = base64.b64decode(audio_b64)
        
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        
        file_size = os.path.getsize(output_path)
        print(f"  ✓ Saved: {output_path} ({file_size} bytes)")
        return True
        
    except requests.exceptions.Timeout:
        print(f"  ✗ Request timed out after 30 seconds")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"  ✗ Connection error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return False


def main():
    print("=" * 60)
    print("  MiMo TTS Offline Test — Wendy NPC Voice")
    print("=" * 60)
    print()
    
    os.makedirs("tts_output", exist_ok=True)
    
    # Test 1: Basic connectivity
    print("[1/2] Testing API connectivity...")
    try:
        test_text = "Hello, this is a connectivity test."
        headers = {
            "Authorization": f"Bearer {MIMO_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": MIMO_TTS_MODEL,
            "messages": [
                {"role": "user", "content": "Speak this line."},
                {"role": "assistant", "content": test_text}
            ],
            "audio": {
                "format": "mp3",
                "voice": "default_en",
            }
        }
        resp = requests.post(
            f"{MIMO_API_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            print("  ✓ API is reachable and responding\n")
        else:
            print(f"  ✗ API returned status {resp.status_code}")
            print(f"  Response: {resp.text[:300]}\n")
            sys.exit(1)
    except Exception as e:
        print(f"  ✗ Cannot reach API: {e}")
        print("  Check your network connection and API key.\n")
        sys.exit(1)
    
    # Test 2: Generate Wendy dialogue samples
    print("[2/2] Generating Wendy dialogue samples...")
    for i, phrase in enumerate(TEST_PHRASES):
        output_path = f"tts_output/wendy_line_{i+1}.mp3"
        print(f"\n  Line {i+1}/{len(TEST_PHRASES)}")
        synthesize_speech(phrase, "default_en", output_path)
    
    print()
    print("=" * 60)
    print("  Test complete! Play the mp3 files to compare voices.")
    print("=" * 60)
    print()
    print("Files generated:")
    for f in sorted(os.listdir("tts_output")):
        if f.endswith(".mp3"):
            size = os.path.getsize(os.path.join("tts_output", f))
            print(f"  tts_output/{f} ({size} bytes)")


if __name__ == "__main__":
    main()
