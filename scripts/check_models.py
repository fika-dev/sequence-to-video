import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from google import genai
from infrastructure.config import load_config

config = load_config()
PROJECT = config.api.google_project_id
LOCATION = config.api.google_location

def check_gemini_flash():
    print("\n[1/4] Gemini 2.0 Flash (영상 분석)...")
    try:
        client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say 'OK' if you can hear me.",
        )
        print(f"  ✓ OK - Response: {response.text.strip()[:50]}")
        return True
    except Exception as e:
        print(f"  ✗ FAIL - {type(e).__name__}: {e}")
        return False

def check_gemini_image():
    print("\n[2/4] Gemini 3 Pro Image (이미지 생성)...")
    try:
        import asyncio
        from io import BytesIO
        from PIL import Image
        
        async def gen():
            client = genai.Client(vertexai=True, project=PROJECT, location="global")
            from google.genai import types
            config = types.GenerateContentConfig(
                temperature=1.0,
                response_modalities=["IMAGE"],
            )
            response = await client.aio.models.generate_content(
                model="gemini-3-pro-image-preview",
                contents=["A simple red circle on white background"],
                config=config,
            )
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        img = Image.open(BytesIO(part.inline_data.data))
                        return img.size
            return None
        
        result = asyncio.run(gen())
        if result:
            print(f"  ✓ OK - Generated image {result}")
            return True
        else:
            print("  ✗ FAIL - No image generated")
            return False
    except Exception as e:
        print(f"  ✗ FAIL - {type(e).__name__}: {e}")
        return False

def check_veo():
    print("\n[3/4] Veo 3.1 (영상 생성) - 요청만 테스트...")
    try:
        from google.genai import types
        client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt="A red ball bouncing",
            config=types.GenerateVideosConfig(aspect_ratio="9:16"),
        )
        print(f"  ✓ OK - Operation started: {operation.name[:60] if operation.name else 'submitted'}...")
        return True
    except Exception as e:
        print(f"  ✗ FAIL - {type(e).__name__}: {e}")
        return False

def check_tts():
    print("\n[4/4] Google Cloud TTS (Chirp v3)...")
    try:
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()
        
        synthesis_input = texttospeech.SynthesisInput(text="테스트")
        voice = texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            name="ko-KR-Chirp3-HD-Leda",
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        print(f"  ✓ OK - Generated {len(response.audio_content)} bytes")
        return True
    except Exception as e:
        print(f"  ✗ FAIL - {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Model Connectivity Check (Vertex AI)")
    print(f"Project: {PROJECT}")
    print(f"Location: {LOCATION}")
    print("=" * 50)
    
    results = {
        "Gemini 2.0 Flash": check_gemini_flash(),
        "Gemini 3 Pro Image": check_gemini_image(),
        "Veo 3.1": check_veo(),
        "Cloud TTS": check_tts(),
    }
    
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    for name, ok in results.items():
        status = "✓" if ok else "✗"
        print(f"  {status} {name}")
    
    all_ok = all(results.values())
    sys.exit(0 if all_ok else 1)
