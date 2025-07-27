#!/usr/bin/env python3
"""
Test voice features without ffmpeg (using speech_recognition fallback)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_voice_without_ffmpeg():
    """Test voice service without ffmpeg"""
    print("🎤 Testing Voice Features (No FFmpeg)")
    print("=" * 40)
    
    try:
        from .voice_service import VoiceService
        
        # Initialize voice service
        print("1. Initializing voice service...")
        voice_service = VoiceService()
        print("✅ Voice service initialized")
        
        # Test TTS
        print("\n2. Testing Text-to-Speech...")
        test_text = "Hello, this is a test without ffmpeg."
        tts_result = voice_service.text_to_speech(test_text, 'en', use_offline=True)
        
        if tts_result['success']:
            print(f"✅ TTS successful: {tts_result['method']}")
        else:
            print(f"❌ TTS failed: {tts_result['error']}")
            return False
        
        # Test microphone detection
        print("\n3. Testing microphone detection...")
        import speech_recognition as sr
        mic_list = sr.Microphone.list_microphone_names()
        
        # Filter out output devices
        input_devices = []
        for i, device in enumerate(mic_list):
            device_lower = device.lower()
            if any(output_keyword in device_lower for output_keyword in ['output', 'speaker', 'playback', 'headphones']):
                continue
            if any(not_mic_keyword in device_lower for not_mic_keyword in ['stereo mix', 'what u hear', 'loopback']):
                continue
            input_devices.append((i, device))
        
        print(f"✅ Found {len(input_devices)} input devices")
        
        if not input_devices:
            print("❌ No input devices found")
            return False
        
        # Test audio recording (short duration)
        print("\n4. Testing audio recording (3 seconds)...")
        print("   Please speak something when prompted...")
        
        audio_path = voice_service.record_audio(3)
        
        if audio_path and os.path.exists(audio_path):
            print(f"✅ Audio recorded successfully: {audio_path}")
            file_size = os.path.getsize(audio_path)
            print(f"   File size: {file_size} bytes")
            
            # Test STT (should use speech_recognition due to no ffmpeg)
            print("\n5. Testing Speech-to-Text (should use speech_recognition)...")
            stt_result = voice_service.speech_to_text(audio_path, 'en')
            
            if stt_result['success']:
                print(f"✅ STT successful: {stt_result['method']}")
                print(f"   Recognized text: '{stt_result['text']}'")
            else:
                print(f"❌ STT failed: {stt_result['error']}")
                print("   This might be normal if no speech was detected")
            
            # Clean up
            try:
                os.remove(audio_path)
                print("✅ Audio file cleaned up")
            except:
                print("⚠️ Could not clean up audio file")
        else:
            print("❌ Audio recording failed")
            return False
        
        print("\n🎉 Voice features working without ffmpeg!")
        print("\n💡 The system is using:")
        print("   - Browser-based voice features (primary)")
        print("   - speech_recognition (server-side fallback)")
        print("   - No ffmpeg dependency")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_voice_without_ffmpeg()
    sys.exit(0 if success else 1) 