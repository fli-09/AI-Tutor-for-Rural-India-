import os
import uuid
import tempfile
from typing import Optional, Dict, Tuple
from gtts import gTTS
import pyttsx3
import speech_recognition as sr
import whisper
import threading
import time

class VoiceService:
    def __init__(self, audio_folder: str = "audio"):
        self.audio_folder = audio_folder
        # Create audio folder if it doesn't exist
        os.makedirs(self.audio_folder, exist_ok=True)
        
        self.recognizer = sr.Recognizer()
        self.whisper_model = None
        self.offline_tts_engine = None
        self._init_offline_components()
    
    def _init_offline_components(self):
        """Initialize offline TTS and STT components"""
        try:
            # Initialize pyttsx3 for offline TTS
            self.offline_tts_engine = pyttsx3.init()
            self.offline_tts_engine.setProperty('rate', 150)  # Speed of speech
            self.offline_tts_engine.setProperty('volume', 0.9)  # Volume level
            print("✅ Offline TTS (pyttsx3) initialized successfully")
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize offline TTS: {e}")
            self.offline_tts_engine = None
        
        # Check FFmpeg availability
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """Check if FFmpeg is available for audio processing"""
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ FFmpeg is available for audio processing")
                self.ffmpeg_available = True
            else:
                print("⚠️ FFmpeg not available - some audio features may be limited")
                self.ffmpeg_available = False
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"⚠️ FFmpeg not found: {e}")
            print("💡 Install FFmpeg for better audio processing support")
            self.ffmpeg_available = False
    
    def text_to_speech(self, text: str, language: str = 'en', 
                      use_offline: bool = False) -> Dict:
        """
        Convert text to speech using online services (Google TTS)
        Returns: dict with audio file path and metadata
        """
        try:
            audio_id = str(uuid.uuid4())
            audio_filename = f"{audio_id}.mp3"
            audio_path = os.path.join(self.audio_folder, audio_filename)
            
            # Prioritize online TTS for better quality and language support
            try:
                result = self._online_tts(text, audio_path, language)
                if result['success']:
                    return result
                else:
                    # Fallback to offline TTS if online fails
                    if self.offline_tts_engine:
                        return self._offline_tts(text, audio_path, language)
                    else:
                        return result
            except Exception as online_error:
                print(f"⚠️ Online TTS failed: {online_error}")
                # Fallback to offline TTS
                if self.offline_tts_engine:
                    return self._offline_tts(text, audio_path, language)
                else:
                    return {
                        'success': False,
                        'error': f'Both online and offline TTS failed: {online_error}',
                        'audio': None,
                        'filename': None
                    }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'audio': None,
                'filename': None
            }
    
    def _online_tts(self, text: str, audio_path: str, language: str) -> Dict:
        """Use gTTS for online text-to-speech"""
        try:
            # Map language codes for gTTS
            lang_map = {
                'en': 'en',
                'hi': 'hi',
                'ta': 'ta',
                'te': 'te',
                'bn': 'bn',
                'mr': 'mr',
                'gu': 'gu',
                'kn': 'kn',
                'ml': 'ml',
                'pa': 'pa'
            }
            
            tts_lang = lang_map.get(language, 'en')
            print(f"🔊 Using Google TTS with language: {tts_lang}")
            
            # Create gTTS object with better configuration
            tts = gTTS(text=text, lang=tts_lang, slow=False)
            
            # Save audio file
            tts.save(audio_path)
            
            # Verify file was created and has content
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                print(f"✅ TTS audio saved: {audio_path} (size: {os.path.getsize(audio_path)} bytes)")
                
                return {
                    'success': True,
                    'audio': f'/audio/{os.path.basename(audio_path)}',
                    'filename': os.path.basename(audio_path),
                    'language': language,
                    'method': 'google_tts_online'
                }
            else:
                raise Exception("Audio file was not created properly")
            
        except Exception as e:
            print(f"❌ Online TTS failed: {e}")
            return {
                'success': False,
                'error': f'Online TTS failed: {str(e)}',
                'audio': None,
                'filename': None
            }
    
    def _offline_tts(self, text: str, audio_path: str, language: str) -> Dict:
        """Use pyttsx3 for offline text-to-speech"""
        try:
            if not self.offline_tts_engine:
                raise Exception("Offline TTS engine not available")
            
            print(f"🔊 Using offline TTS (pyttsx3) for language: {language}")
            
            # Set voice based on language (basic mapping)
            voices = self.offline_tts_engine.getProperty('voices')
            if voices:
                # Try to find appropriate voice for language
                for voice in voices:
                    if language in voice.id.lower():
                        self.offline_tts_engine.setProperty('voice', voice.id)
                        print(f"✅ Using voice: {voice.name}")
                        break
                else:
                    # Use default voice
                    self.offline_tts_engine.setProperty('voice', voices[0].id)
                    print(f"⚠️ Using default voice: {voices[0].name}")
            
            # Save to temporary file first
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Generate speech
            self.offline_tts_engine.save_to_file(text, temp_path)
            self.offline_tts_engine.runAndWait()
            
            # Verify temp file was created
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise Exception("Failed to generate speech file")
            
            # Convert WAV to MP3 using pydub if available, otherwise copy
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_wav(temp_path)
                audio.export(audio_path, format="mp3")
                print(f"✅ Converted WAV to MP3: {audio_path}")
            except ImportError:
                # Fallback: just copy the WAV file and rename
                import shutil
                shutil.copy2(temp_path, audio_path)
                print(f"⚠️ Using WAV format (pydub not available): {audio_path}")
            
            os.unlink(temp_path)  # Clean up temp file
            
            # Verify final file
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                print(f"✅ Offline TTS audio saved: {audio_path} (size: {os.path.getsize(audio_path)} bytes)")
                
                return {
                    'success': True,
                    'audio': f'/audio/{os.path.basename(audio_path)}',
                    'filename': os.path.basename(audio_path),
                    'language': language,
                    'method': 'pyttsx3_offline'
                }
            else:
                raise Exception("Final audio file was not created properly")
            
        except Exception as e:
            print(f"❌ Offline TTS failed: {e}")
            return {
                'success': False,
                'error': f"Offline TTS failed: {str(e)}",
                'audio': None,
                'filename': None
            }
    
    def speech_to_text(self, audio_file_path: str, 
                      language: str = 'en') -> Dict:
        """
        Convert speech to text using online services (Google Speech Recognition)
        """
        try:
            # Check if audio file exists
            if not os.path.exists(audio_file_path):
                return {
                    'success': False,
                    'error': f"Audio file not found: {audio_file_path}",
                    'text': None
                }
            
            # Use online Google Speech Recognition (no FFmpeg needed)
            return self._online_speech_recognition(audio_file_path, language)
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': None
            }
    
    def _load_whisper_model(self) -> bool:
        """Load Whisper model for offline STT"""
        try:
            if self.whisper_model is None:
                self.whisper_model = whisper.load_model("base")
            return True
        except Exception as e:
            print(f"Warning: Could not load Whisper model: {e}")
            return False
    
    def _whisper_stt(self, audio_file_path: str, language: str) -> Dict:
        """Use Whisper for speech-to-text"""
        try:
            if not self.whisper_model:
                raise Exception("Whisper model not loaded")
            
            # Validate audio file exists and is accessible
            if not audio_file_path:
                raise Exception("Audio file path is empty")
            
            if not os.path.exists(audio_file_path):
                raise Exception(f"Audio file does not exist: {audio_file_path}")
            
            if not os.path.isfile(audio_file_path):
                raise Exception(f"Audio file path is not a file: {audio_file_path}")
            
            file_size = os.path.getsize(audio_file_path)
            if file_size == 0:
                raise Exception(f"Audio file is empty: {audio_file_path}")
            
            print(f"🎤 Whisper STT: Processing file {audio_file_path} (size: {file_size} bytes)")
            
            # Language mapping for Whisper
            lang_map = {
                'en': 'en',
                'hi': 'hi',
                'ta': 'ta',
                'te': 'te',
                'bn': 'bn',
                'mr': 'mr',
                'gu': 'gu',
                'kn': 'kn',
                'ml': 'ml',
                'pa': 'pa'
            }
            
            whisper_lang = lang_map.get(language, 'en')
            
            # Try to transcribe audio with error handling for ffmpeg issues
            try:
                result = self.whisper_model.transcribe(
                    audio_file_path,
                    language=whisper_lang,
                    task="transcribe"
                )
                
                return {
                    'success': True,
                    'text': result['text'].strip(),
                    'language': language,
                    'method': 'whisper'
                }
                
            except Exception as whisper_error:
                # If Whisper fails due to ffmpeg, fall back to speech_recognition
                if "ffmpeg" in str(whisper_error).lower() or "file" in str(whisper_error).lower():
                    print(f"⚠️ Whisper failed due to ffmpeg/file issue: {whisper_error}")
                    print("🔄 Falling back to speech_recognition...")
                    return self._speech_recognition_stt(audio_file_path, language)
                else:
                    raise whisper_error
            
        except Exception as e:
            print(f"❌ Whisper STT error: {str(e)}")
            return {
                'success': False,
                'error': f"Whisper STT failed: {str(e)}",
                'text': None
            }
    
    def _online_speech_recognition(self, audio_file_path: str, 
                                  language: str) -> Dict:
        """Use online Google Speech Recognition for STT (no FFmpeg needed)"""
        try:
            # Language mapping for Google Speech Recognition
            lang_map = {
                'en': 'en-US',
                'hi': 'hi-IN',
                'ta': 'ta-IN',
                'te': 'te-IN',
                'bn': 'bn-IN',
                'mr': 'mr-IN',
                'gu': 'gu-IN',
                'kn': 'kn-IN',
                'ml': 'ml-IN',
                'pa': 'pa-IN'
            }
            
            sr_lang = lang_map.get(language, 'en-US')
            print(f"🎤 Using Google Speech Recognition with language: {sr_lang}")
            
            with sr.AudioFile(audio_file_path) as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.record(source)
                
                # Use Google Speech Recognition (online, no FFmpeg needed)
                text = self.recognizer.recognize_google(
                    audio,
                    language=sr_lang,
                    show_all=False  # Get single best result
                )
                
                print(f"✅ Speech recognized: {text}")
                
                return {
                    'success': True,
                    'text': text.strip(),
                    'language': language,
                    'method': 'google_speech_recognition_online'
                }
                
        except sr.UnknownValueError:
            print("❌ Could not understand audio")
            return {
                'success': False,
                'error': 'Could not understand audio - please speak more clearly',
                'text': None
            }
        except sr.RequestError as e:
            print(f"❌ Speech recognition service error: {e}")
            return {
                'success': False,
                'error': f'Speech recognition service error: {e}',
                'text': None
            }
        except Exception as e:
            print(f"❌ Speech recognition error: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': None
            }
    
    def record_audio(self, duration: int = 5) -> Optional[str]:
        """
        Record audio from microphone (works with or without headphones)
        Returns: path to recorded audio file or None
        """
        try:
            # Check if microphone is available
            try:
                # Try to get available microphones
                mic_list = sr.Microphone.list_microphone_names()
                print(f"Available microphones: {mic_list}")
                
                if not mic_list:
                    print("No microphones found, trying default microphone")
                    mic = sr.Microphone()
                else:
                    # Try different microphone devices in order of preference
                    mic = None
                    preferred_keywords = ['headphone', 'headset', 'earphone', 'bluetooth', 'wireless', 'airpods']
                    fallback_keywords = ['built-in', 'internal', 'default', 'system']
                    
                    # First, try to find preferred devices (headphones, etc.)
                    # But filter out output devices that might be misidentified
                    for i, mic_name in enumerate(mic_list):
                        mic_lower = mic_name.lower()
                        
                        # Skip devices that are clearly output devices
                        if any(output_keyword in mic_lower for output_keyword in ['output', 'speaker', 'playback', 'headphones']):
                            continue
                        # Skip devices that are clearly not microphones
                        if any(not_mic_keyword in mic_lower for not_mic_keyword in ['stereo mix', 'what u hear', 'loopback']):
                            continue
                        
                        if any(keyword in mic_lower for keyword in preferred_keywords):
                            try:
                                print(f"Trying preferred microphone {i}: {mic_name}")
                                mic = sr.Microphone(device_index=i)
                                # Test if this microphone works
                                with mic as source:
                                    self.recognizer.adjust_for_ambient_noise(source, duration=0.1)
                                print(f"Successfully initialized preferred microphone: {mic_name}")
                                break
                            except Exception as e:
                                print(f"Failed to initialize preferred microphone {i}: {e}")
                                continue
                    
                    # If no preferred device found, try fallback devices (built-in, etc.)
                    if mic is None:
                        for i, mic_name in enumerate(mic_list):
                            mic_lower = mic_name.lower()
                            
                            # Skip devices that are clearly output devices
                            if any(output_keyword in mic_lower for output_keyword in ['output', 'speaker', 'playback', 'headphones']):
                                continue
                            # Skip devices that are clearly not microphones
                            if any(not_mic_keyword in mic_lower for not_mic_keyword in ['stereo mix', 'what u hear', 'loopback']):
                                continue
                            
                            if any(keyword in mic_lower for keyword in fallback_keywords):
                                try:
                                    print(f"Trying fallback microphone {i}: {mic_name}")
                                    mic = sr.Microphone(device_index=i)
                                    # Test if this microphone works
                                    with mic as source:
                                        self.recognizer.adjust_for_ambient_noise(source, duration=0.1)
                                    print(f"Successfully initialized fallback microphone: {mic_name}")
                                    break
                                except Exception as e:
                                    print(f"Failed to initialize fallback microphone {i}: {e}")
                                    continue
                    
                    # If still no device found, try any available microphone
                    if mic is None:
                        for i, mic_name in enumerate(mic_list):
                            mic_lower = mic_name.lower()
                            
                            # Skip devices that are clearly output devices
                            if any(output_keyword in mic_lower for output_keyword in ['output', 'speaker', 'playback', 'headphones']):
                                continue
                            # Skip devices that are clearly not microphones
                            if any(not_mic_keyword in mic_lower for not_mic_keyword in ['stereo mix', 'what u hear', 'loopback']):
                                continue
                            
                            try:
                                print(f"Trying any available microphone {i}: {mic_name}")
                                mic = sr.Microphone(device_index=i)
                                # Test if this microphone works
                                with mic as source:
                                    self.recognizer.adjust_for_ambient_noise(source, duration=0.1)
                                print(f"Successfully initialized microphone: {mic_name}")
                                break
                            except Exception as e:
                                print(f"Failed to initialize microphone {i}: {e}")
                                continue
                    
                    # Final fallback to default microphone
                    if mic is None:
                        print("All specific microphones failed, using default microphone")
                        try:
                            mic = sr.Microphone()
                            print("Using default microphone as fallback")
                        except Exception as default_error:
                            print(f"❌ Default microphone failed: {default_error}")
                            return None
                
                # Ensure we have a working microphone
                if mic is None:
                    print("❌ No working microphone found")
                    return None
                
                # Test microphone before using
                try:
                    with mic as source:
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.1)
                    print("✅ Microphone test successful")
                except Exception as test_error:
                    print(f"❌ Microphone test failed: {test_error}")
                    return None
                
                try:
                    with mic as source:
                        print(f"Recording for {duration} seconds...")
                        # Adjust for ambient noise
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        print("Listening... Speak now!")
                        
                        try:
                            audio = self.recognizer.listen(source, timeout=duration, phrase_time_limit=duration)
                            
                            # Save audio to file
                            audio_id = str(uuid.uuid4())
                            audio_filename = f"{audio_id}.wav"
                            audio_path = os.path.join(self.audio_folder, audio_filename)
                            
                            with open(audio_path, "wb") as f:
                                f.write(audio.get_wav_data())
                            
                            # Ensure file is fully written
                            import time
                            time.sleep(0.1)  # Small delay to ensure file is written
                            
                            # Verify file was created and has content
                            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                                print(f"✅ Audio saved to: {audio_path} (size: {os.path.getsize(audio_path)} bytes)")
                                return audio_path
                            else:
                                print(f"❌ Audio file not properly saved: {audio_path}")
                                return None
                            
                        except sr.WaitTimeoutError:
                            print("No speech detected within timeout period")
                            return None
                        except Exception as audio_error:
                            print(f"Error during audio recording: {audio_error}")
                            return None
                except Exception as mic_error:
                    print(f"Error with microphone context: {mic_error}")
                    return None
                    
            except sr.WaitTimeoutError:
                print("No speech detected within timeout")
                return None
            except OSError as e:
                print(f"Microphone access error: {e}")
                return None
                
        except Exception as e:
            print(f"Error recording audio: {e}")
            return None
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages"""
        return {
            'en': 'English',
            'hi': 'Hindi',
            'ta': 'Tamil',
            'te': 'Telugu',
            'bn': 'Bengali',
            'mr': 'Marathi',
            'gu': 'Gujarati',
            'kn': 'Kannada',
            'ml': 'Malayalam',
            'pa': 'Punjabi'
        }
    
    def get_system_status(self) -> Dict[str, any]:
        """Get voice system status and capabilities"""
        return {
            'online_tts_available': True,  # Google TTS always available
            'offline_tts_available': self.offline_tts_engine is not None,
            'ffmpeg_available': getattr(self, 'ffmpeg_available', False),
            'whisper_available': self.whisper_model is not None,
            'server_speech_recognition': True,  # Using server-side Google Speech Recognition
            'speech_recognition_available': True,  # Always available via server
            'supported_languages': self.get_supported_languages(),
            'recommendations': self._get_recommendations()
        }
    
    def _get_recommendations(self) -> list:
        """Get recommendations for improving voice features"""
        recommendations = []
        
        # Server-side services are always available
        recommendations.append("✅ Using server-side Google Speech Recognition (no browser API issues)")
        recommendations.append("✅ Using online Google Text-to-Speech (high quality)")
        
        if not getattr(self, 'ffmpeg_available', False):
            recommendations.append("⚠️ Install FFmpeg for advanced audio processing (optional)")
        
        if not self.offline_tts_engine:
            recommendations.append("⚠️ Install pyttsx3 for offline text-to-speech (optional)")
        
        if not self.whisper_model:
            recommendations.append("⚠️ Install Whisper for offline speech recognition (optional)")
        
        recommendations.append("🌐 Internet connection required for voice features")
        recommendations.append("🎤 Speak clearly for better recognition accuracy")
        recommendations.append("🔊 TTS works in all supported languages")
        recommendations.append("🎯 No more browser network errors - using server-side processing")
        
        return recommendations

# Global instance
voice_service = VoiceService("../audio") 