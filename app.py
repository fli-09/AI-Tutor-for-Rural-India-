import os
import time
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from dotenv import load_dotenv
load_dotenv()

# Import our service modules
from services.llm_service import llm_service
from services.pdf_service import pdf_service
from services.voice_service import voice_service
from services.database_service import db_service
from services.rag_service import rag_service
from services.adaptive_learning import adaptive_learning
from services.teacher_mode import teacher_mode
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests

app = Flask(__name__, 
           template_folder='../templates',
           static_folder='../static')
app.secret_key = 'ai_tutor_rural_india_secret_key_2024'

# Configuration
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
app.config['AUDIO_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'audio')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['AUDIO_FOLDER'], exist_ok=True)

# Log the actual paths being used
print(f"📁 Upload folder: {app.config['UPLOAD_FOLDER']}")
print(f"📁 Audio folder: {app.config['AUDIO_FOLDER']}")
print(f"📁 Upload folder exists: {os.path.exists(app.config['UPLOAD_FOLDER'])}")
print(f"📁 Audio folder exists: {os.path.exists(app.config['AUDIO_FOLDER'])}")

# Initialize user session
def get_user_id():
    """Get or create user ID for session"""
    if 'user_id' not in session:
        session['user_id'] = f"user_{uuid.uuid4().hex[:8]}"
    return session['user_id']

# Flask-Limiter for rate limiting
limiter = Limiter(get_remote_address, app=app, default_limits=["100 per hour"])

# Periodic cleanup for old audio files (run on each startup)
def cleanup_audio_folder(days=2):
    folder = app.config['AUDIO_FOLDER']
    now = time.time()
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if os.path.isfile(path):
            if now - os.path.getmtime(path) > days * 86400:
                try:
                    os.remove(path)
                except Exception:
                    pass
cleanup_audio_folder()

@app.route('/')
def index():
    """Main page with PDF upload and question generation"""
    return render_template('index.html')

@app.route('/upload')
def upload_page():
    """PDF upload page"""
    return render_template('upload.html')

@app.route('/quiz')
def quiz_page():
    """Quiz page"""
    return render_template('quiz.html')

@app.route('/profile')
def profile_page():
    """Profile page"""
    return render_template('profile.html')

@app.route('/ask', methods=['GET', 'POST'])
def ask_question_page():
    """Ask questions page"""
    if request.method == 'POST':
        # Handle POST request for asking questions
        try:
            data = request.json
            question = data.get('question', '').strip()
            user_id = get_user_id()
            
            if not question:
                return jsonify({'error': 'Question is required'}), 400
            
            # Use the RAG service to process the question
            answer_data = rag_service.process_question(question, llm_service, user_id)
            
            return jsonify({
                'success': True,
                'question': question,
                'answer': answer_data['answer'],
                'confidence': answer_data['confidence'],
                'sources': answer_data['sources'],
                'context_chunks': answer_data['context_chunks'],
                'answer_type': answer_data.get('answer_type', 'unknown')
            })
            
        except Exception as e:
            return jsonify({'error': f'Error processing question: {str(e)}'}), 500
    
    # Handle GET request for the page
    return render_template('ask_question.html')

@app.route('/generate_questions', methods=['POST'])
@limiter.limit("30 per hour")
def generate_questions():
    """Generate questions from uploaded PDF"""
    try:
        print("📄 Generate Questions endpoint called")
        
        if 'pdf' not in request.files:
            print("❌ No PDF file in request")
            return jsonify({'error': 'No PDF file uploaded'}), 400
        
        file = request.files['pdf']
        if file.filename == '':
            print("❌ No filename provided")
            return jsonify({'error': 'No file selected'}), 400
        
        print(f"📄 Processing file: {file.filename}")
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            print(f"❌ Invalid file type: {file.filename}")
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"📁 Saving file to: {filepath}")
        
        try:
            file.save(filepath)
            print(f"✅ File saved successfully, size: {os.path.getsize(filepath)} bytes")
        except Exception as save_error:
            print(f"❌ Error saving file: {save_error}")
            return jsonify({'error': f'Error saving file: {str(save_error)}'}), 500
        
        # Validate PDF
        print("🔍 Validating PDF...")
        is_valid, message = pdf_service.validate_pdf(filepath)
        if not is_valid:
            print(f"❌ PDF validation failed: {message}")
            os.remove(filepath)  # Clean up invalid file
            return jsonify({'error': message}), 400
        
        print("✅ PDF validation passed")
        
        # Extract text from PDF
        print("📄 Extracting text from PDF...")
        pdf_data = pdf_service.extract_text_from_pdf(filepath)
        
        print(f"📊 PDF extraction result: success={pdf_data.get('success', False)}")
        
        # Check if PDF extraction was successful
        if not pdf_data.get('success', False):
            error_msg = pdf_data.get('error', 'Failed to extract text from PDF')
            print(f"❌ PDF extraction failed: {error_msg}")
            os.remove(filepath)  # Clean up file
            return jsonify({'error': error_msg}), 500
        
        print("✅ PDF text extraction successful")
        
        # Check if we have cached questions for this PDF
        print("🔍 Checking for cached questions...")
        cached_questions = db_service.get_questions_for_pdf(filename)
        target_language = request.form.get('target_language')
        
        if cached_questions:
            print("✅ Using cached questions")
            questions = cached_questions
        else:
            print("🔄 Generating new questions...")
            # Generate questions using LLM
            num_questions = request.form.get('num_questions', 5, type=int)
            question_type = request.form.get('question_type', 'mcq')
            
            print(f"📝 Generating {num_questions} {question_type} questions...")
            
            try:
                questions = llm_service.generate_questions_from_text(
                    pdf_data['text'], 
                    num_questions, 
                    question_type
                )
                print(f"✅ Generated {len(questions)} questions successfully")
            except Exception as llm_error:
                print(f"❌ LLM question generation failed: {llm_error}")
                os.remove(filepath)  # Clean up file
                return jsonify({'error': f'Failed to generate questions: {str(llm_error)}'}), 500
            
            # Save questions to database for reuse
            try:
                db_service.save_generated_questions(filename, questions)
                print("✅ Questions saved to database")
            except Exception as db_error:
                print(f"⚠️ Warning: Failed to save questions to database: {db_error}")
                # Continue processing even if database save fails
            
            # Save PDF metadata
            try:
                db_service.save_pdf_document(filename, pdf_data['metadata'])
                print("✅ PDF metadata saved")
            except Exception as meta_error:
                print(f"⚠️ Warning: Failed to save PDF metadata: {meta_error}")
                # Continue processing even if metadata save fails
            
            # Add PDF content to RAG database for doubt resolution
            try:
                rag_service.add_pdf_content(
                    filename, 
                    pdf_data['text'], 
                    metadata={
                        'language': pdf_data.get('language', 'en'),
                        'topics': pdf_data.get('topics', []),
                        'upload_timestamp': datetime.now().isoformat()
                    }
                )
                print("✅ PDF content added to RAG database")
            except Exception as rag_error:
                print(f"⚠️ Warning: RAG service error (non-critical): {rag_error}")
                # Continue processing even if RAG fails
        # If translation requested, translate questions
        if target_language and target_language != 'en':
            print(f"🌐 Translating questions to {target_language}...")
            try:
                for q in questions:
                    q['question'] = translate_text(q['question'], target_language)
                    q['options'] = [translate_text(opt, target_language) for opt in q['options']]
                    if 'explanation' in q:
                        q['explanation'] = translate_text(q['explanation'], target_language)
                print("✅ Translation completed")
            except Exception as trans_error:
                print(f"⚠️ Warning: Translation failed: {trans_error}")
                # Continue with original language
        
        print("✅ Question generation process completed successfully")
        
        return jsonify({
            'questions': questions,
            'structure': pdf_data.get('structured_content', {}),
            'pdf_info': pdf_data,
            'cached': bool(cached_questions)
        })
        
    except RequestEntityTooLarge:
        print("❌ File too large error")
        return jsonify({'error': 'File too large. Maximum size is 50MB'}), 413
    except Exception as e:
        print(f"❌ Unexpected error in generate_questions: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500

# Helper for translation

def translate_text(text, target_lang):
    try:
        url = 'https://translate.googleapis.com/translate_a/single'
        params = {
            'client': 'gtx',
            'sl': 'auto',
            'tl': target_lang,
            'dt': 't',
            'q': text
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        return ''.join([seg[0] for seg in result[0]])
    except Exception:
        return text

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    """Submit quiz answers and calculate score"""
    try:
        data = request.json
        user_id = get_user_id()
        
        questions = data.get('questions', [])
        answers = data.get('answers', {})
        pdf_filename = data.get('pdf_filename', '')
        time_taken = data.get('time_taken', 0)
        
        # Calculate score
        correct_answers = 0
        total_questions = len(questions)
        
        for i, question in enumerate(questions):
            user_answer = answers.get(str(i), '')
            # Handle both field names for correct answer
            correct_answer = question.get('correct_answer') or question.get('answer', '')
            
            if user_answer == correct_answer:
                correct_answers += 1
        
        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        # Extract topics from questions
        topics = list(set(q.get('topic', 'General') for q in questions))
        
        # Prepare quiz data for database
        quiz_data = {
            'pdf_filename': pdf_filename,
            'questions': questions,
            'answers': answers,
            'score': round(score, 2),
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'time_taken': time_taken,
            'topics': topics,
            'language': 'en'  # Default language
        }
        
        # Save to database
        attempt_id = db_service.save_quiz_attempt(user_id, quiz_data)
        
        # Record individual question attempts to adaptive learning system
        try:
            from services.adaptive_learning import QuestionAttempt
            from datetime import datetime
            
            recorded_attempts = 0
            for i, question in enumerate(questions):
                user_answer = answers.get(str(i), '')
                correct_answer = question.get('correct_answer') or question.get('answer', '')
                is_correct = user_answer == correct_answer
                
                # Calculate time taken per question (approximate)
                avg_time_per_question = time_taken / total_questions if total_questions > 0 else 0
                
                # Get topic from question, fallback to 'General' if not available
                topic = question.get('topic', 'General')
                if not topic or topic == '':
                    topic = 'General'
                
                # Get difficulty from question, fallback to 'medium' if not available
                difficulty = question.get('difficulty', 'medium')
                if not difficulty or difficulty == '':
                    difficulty = 'medium'
                
                # Get cognitive level from question, fallback to 'application' if not available
                cognitive_level = question.get('cognitive_level', 'application')
                if not cognitive_level or cognitive_level == '':
                    cognitive_level = 'application'
                
                attempt = QuestionAttempt(
                    question_id=f"quiz_{attempt_id}_q_{i}",
                    topic=topic,
                    difficulty=difficulty,
                    cognitive_level=cognitive_level,
                    correct=is_correct,
                    time_taken=avg_time_per_question,
                    timestamp=datetime.now(),
                    confidence=0.5  # Default confidence
                )
                
                adaptive_learning.record_attempt(user_id, attempt)
                recorded_attempts += 1
                
                print(f"📝 Recorded attempt {i+1}/{total_questions}: topic={topic}, difficulty={difficulty}, correct={is_correct}")
            
            print(f"✅ Successfully recorded {recorded_attempts}/{total_questions} question attempts to adaptive learning system")
            
            # Verify the recording worked by checking user profile
            if user_id in adaptive_learning.students:
                profile = adaptive_learning.students[user_id]
                print(f"📊 User profile updated: total_questions={profile.total_questions}, correct_answers={profile.correct_answers}")
            else:
                print("⚠️ Warning: User profile not found after recording attempts")
            
        except Exception as e:
            print(f"❌ Error recording attempts to adaptive learning system: {e}")
            import traceback
            traceback.print_exc()
            # Continue processing even if adaptive learning recording fails
        
        return jsonify({
            'success': True,
            'attempt_id': attempt_id,
            'score': round(score, 2),
            'correct_answers': correct_answers,
            'total_questions': total_questions,
            'feedback': _generate_feedback(score)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error submitting quiz: {str(e)}'}), 500

def _generate_feedback(score):
    """Generate feedback based on score"""
    if score >= 90:
        return "Excellent! You have a strong understanding of this topic."
    elif score >= 80:
        return "Great job! You're doing well, keep it up!"
    elif score >= 70:
        return "Good work! You're on the right track."
    elif score >= 60:
        return "Not bad! Review the material and try again."
    else:
        return "Keep practicing! Review the content and try the quiz again."

@app.route('/speak', methods=['POST'])
def speak():
    """Convert text to speech"""
    try:
        print("🔊 Speak endpoint called")
        data = request.json
        if not data:
            print("❌ Speak endpoint: No data provided")
            return jsonify({'error': 'No data provided'}), 400
            
        text = data.get('text', '')
        language = data.get('language', 'en')
        use_offline = data.get('use_offline', False)
        
        print(f"🔊 Speak endpoint: Text='{text[:50]}...', Language={language}, Offline={use_offline}")
        
        if not text:
            print("❌ Speak endpoint: No text provided")
            return jsonify({'error': 'No text provided'}), 400
        
        # Convert text to speech
        print("🔊 Speak endpoint: Calling voice_service.text_to_speech")
        result = voice_service.text_to_speech(text, language, use_offline)
        
        print(f"🔊 Speak endpoint: TTS result success={result.get('success', False)}")
        
        if result['success']:
            print(f"✅ Speak endpoint: TTS successful, audio file: {result.get('filename', 'unknown')}")
            return jsonify(result)
        else:
            print(f"❌ Speak endpoint: TTS failed: {result.get('error', 'unknown error')}")
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        print(f"❌ Speak endpoint: Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error in text-to-speech: {str(e)}'}), 500

@app.route('/listen', methods=['GET', 'POST'])
def listen():
    """Convert speech to text"""
    if request.method == 'GET':
        return jsonify({
            'error': 'This endpoint only accepts POST requests. Please use the voice features in the application.',
            'usage': 'Send a POST request with JSON body: {"language": "en", "duration": 5}'
        }), 405
    try:
        data = request.json
        if not data:
            print("❌ Listen endpoint: No data provided")
            return jsonify({'error': 'No data provided'}), 400
            
        language = data.get('language', 'en')
        duration = data.get('duration', 5)
        
        print(f"🎤 Listen endpoint: Recording {duration}s of audio in {language}")
        
        # Check if voice service is available
        if not voice_service:
            print("❌ Listen endpoint: Voice service not available")
            return jsonify({'error': 'Voice service not available'}), 500
        
        # Record audio
        try:
            audio_path = voice_service.record_audio(duration)
        except Exception as record_error:
            print(f"❌ Listen endpoint: Audio recording failed: {record_error}")
            return jsonify({'error': f'Audio recording failed: {str(record_error)}'}), 500
        
        if not audio_path:
            print("❌ Listen endpoint: Failed to record audio - no speech detected")
            return jsonify({'error': 'Failed to record audio - no speech detected. Please speak clearly into your microphone.'}), 500
        
        print(f"✅ Listen endpoint: Audio recorded at {audio_path}")
        
        # Convert speech to text
        try:
            result = voice_service.speech_to_text(audio_path, language)
        except Exception as stt_error:
            print(f"❌ Listen endpoint: Speech-to-text failed: {stt_error}")
            # Clean up audio file even if STT failed
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                    print(f"✅ Listen endpoint: Audio file cleaned up after STT error")
            except Exception as cleanup_error:
                print(f"⚠️ Listen endpoint: Failed to cleanup audio file: {cleanup_error}")
            return jsonify({'error': f'Speech-to-text failed: {str(stt_error)}'}), 500
        
        # Clean up audio file AFTER successful STT processing
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"✅ Listen endpoint: Audio file cleaned up")
        except Exception as cleanup_error:
            print(f"⚠️ Listen endpoint: Failed to cleanup audio file: {cleanup_error}")
        
        if result['success']:
            print(f"✅ Listen endpoint: Speech recognized: '{result['text']}'")
            return jsonify(result)
        else:
            print(f"❌ Listen endpoint: Speech recognition failed: {result['error']}")
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        print(f"❌ Listen endpoint: Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error in speech-to-text: {str(e)}'}), 500

@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files"""
    try:
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], filename)
        if os.path.exists(audio_path):
            return send_from_directory(app.config['AUDIO_FOLDER'], filename)
        else:
            print(f"❌ Audio file not found: {audio_path}")
            return jsonify({'error': 'Audio file not found'}), 404
    except Exception as e:
        print(f"❌ Error serving audio file: {e}")
        return jsonify({'error': 'Error serving audio file'}), 500

@app.route('/progress')
def progress():
    """Progress dashboard page"""
    user_id = get_user_id()
    user_progress = db_service.get_user_progress(user_id)
    topic_analytics = db_service.get_topic_analytics(user_id)
    recent_attempts = db_service.get_recent_attempts(user_id, 5)
    
    # Provide default values if no progress data exists
    if user_progress is None:
        user_progress = {
            'total_attempts': 0,
            'average_score': 0,
            'total_score': 0,
            'total_time': 0,
            'improvement_rate': 0,
            'strengths': [],
            'weaknesses': [],
            'topics': {},
            'recent_attempts': []
        }
    
    if topic_analytics is None:
        topic_analytics = {
            'topics': [],
            'scores': []
        }
    
    if recent_attempts is None:
        recent_attempts = []
    
    return render_template('progress.html', 
                         progress=user_progress,
                         analytics=topic_analytics,
                         recent_attempts=recent_attempts)

@app.route('/api/progress')
def api_progress():
    """API endpoint for progress data"""
    user_id = get_user_id()
    user_progress = db_service.get_user_progress(user_id)
    topic_analytics = db_service.get_topic_analytics(user_id)
    recent_attempts = db_service.get_recent_attempts(user_id, 10)
    
    # Provide default values if no progress data exists
    if user_progress is None:
        user_progress = {
            'total_attempts': 0,
            'average_score': 0,
            'total_score': 0,
            'total_time': 0,
            'improvement_rate': 0,
            'strengths': [],
            'weaknesses': [],
            'topics': {},
            'recent_attempts': []
        }
    
    if topic_analytics is None:
        topic_analytics = {
            'topics': [],
            'scores': []
        }
    
    if recent_attempts is None:
        recent_attempts = []
    
    return jsonify({
        'progress': user_progress,
        'analytics': topic_analytics,
        'recent_attempts': recent_attempts
    })

@app.route('/api/stats')
def api_stats():
    """Get overall application statistics"""
    stats = db_service.get_dashboard_stats()
    return jsonify(stats)

@app.route('/api/languages')
def api_languages():
    """Get supported languages"""
    languages = voice_service.get_supported_languages()
    return jsonify(languages)

@app.route('/api/voice_status')
def api_voice_status():
    """Get voice system status and recommendations"""
    try:
        status = voice_service.get_system_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({
            'error': f'Error getting voice status: {str(e)}',
            'offline_tts_available': False,
            'ffmpeg_available': False,
            'whisper_available': False,
            'speech_recognition_available': True,
            'recommendations': ['Check voice service configuration']
        }), 500

@app.route('/explain', methods=['POST'])
def explain_question():
    """Generate explanation for a specific question"""
    try:
        data = request.json
        question = data.get('question', '')
        answer = data.get('answer', '')
        
        if not question or not answer:
            return jsonify({'error': 'Question and answer required'}), 400
        
        explanation = llm_service.generate_explanation(question, answer)
        
        return jsonify({
            'explanation': explanation,
            'question': question,
            'answer': answer
        })
        
    except Exception as e:
        return jsonify({'error': f'Error generating explanation: {str(e)}'}), 500

@app.route('/quiz/<attempt_id>')
def quiz_result(attempt_id):
    """View specific quiz result"""
    # This would fetch the specific attempt from database
    # For now, return a simple response
    return jsonify({
        'attempt_id': attempt_id,
        'message': 'Quiz result details would be displayed here'
    })

@app.route('/logout')
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out.'})

@app.route('/translate', methods=['POST'])
@limiter.limit("20 per hour")
def translate():
    data = request.json
    text = data.get('text', '')
    target_lang = data.get('target_language', 'en')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    try:
        # Google Translate API (free tier, for demo)
        url = 'https://translate.googleapis.com/translate_a/single'
        params = {
            'client': 'gtx',
            'sl': 'auto',
            'tl': target_lang,
            'dt': 't',
            'q': text
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        translated = ''.join([seg[0] for seg in result[0]])
        return jsonify({'translated': translated, 'target_language': target_lang})
    except Exception as e:
        return jsonify({'error': f'Translation failed: {str(e)}'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/quiz/<pdf_filename>')
def get_quiz_questions(pdf_filename):
    """Get quiz questions for a specific PDF"""
    try:
        questions = db_service.get_questions_for_pdf(pdf_filename)
        if questions:
            return jsonify({'questions': questions, 'pdf_filename': pdf_filename})
        else:
            return jsonify({'error': 'No questions found for this PDF'}), 404
    except Exception as e:
        return jsonify({'error': f'Error fetching questions: {str(e)}'}), 500

@app.route('/api/available_quizzes')
def get_available_quizzes():
    """Get list of available PDFs with questions"""
    try:
        user_id = get_user_id()
        pdfs = db_service.get_user_pdfs(user_id)
        return jsonify({'pdfs': pdfs})
    except Exception as e:
        return jsonify({'error': f'Error fetching PDFs: {str(e)}'}), 500

@app.route('/api/profile')
def get_profile():
    """Get user profile data"""
    try:
        user_id = get_user_id()
        profile = db_service.get_user_profile(user_id)
        return jsonify(profile)
    except Exception as e:
        return jsonify({'error': f'Error fetching profile: {str(e)}'}), 500

@app.route('/api/profile', methods=['PUT'])
def update_profile():
    """Update user profile"""
    try:
        user_id = get_user_id()
        data = request.json
        success = db_service.update_user_profile(user_id, data)
        if success:
            return jsonify({'success': True, 'message': 'Profile updated successfully'})
        else:
            return jsonify({'error': 'Failed to update profile'}), 500
    except Exception as e:
        return jsonify({'error': f'Error updating profile: {str(e)}'}), 500

@app.route('/api/export_progress')
def export_progress():
    """Export progress as PDF"""
    try:
        user_id = get_user_id()
        progress_data = db_service.get_user_progress(user_id)
        topic_analytics = db_service.get_topic_analytics(user_id)
        recent_attempts = db_service.get_recent_attempts(user_id, 10)
        
        # Generate PDF report (simplified for demo)
        report_data = {
            'user_id': user_id,
            'generated_at': datetime.now().isoformat(),
            'progress': progress_data,
            'analytics': topic_analytics,
            'recent_attempts': recent_attempts
        }
        
        return jsonify({
            'success': True,
            'message': 'Progress report generated',
            'data': report_data,
            'download_url': f'/api/download_report/{user_id}'
        })
    except Exception as e:
        return jsonify({'error': f'Error generating report: {str(e)}'}), 500

@app.route('/api/download_report/<user_id>')
def download_report(user_id):
    """Download progress report"""
    try:
        # For demo, return JSON data as downloadable file
        progress_data = db_service.get_user_progress(user_id)
        topic_analytics = db_service.get_topic_analytics(user_id)
        recent_attempts = db_service.get_recent_attempts(user_id, 10)
        
        report_data = {
            'user_id': user_id,
            'generated_at': datetime.now().isoformat(),
            'progress': progress_data,
            'analytics': topic_analytics,
            'recent_attempts': recent_attempts
        }
        
        from flask import Response
        import json
        
        response = Response(
            json.dumps(report_data, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename=progress_report_{user_id}.json'}
        )
        return response
    except Exception as e:
        return jsonify({'error': f'Error downloading report: {str(e)}'}), 500

@app.route('/api/set_language', methods=['POST'])
def set_language():
    """Set user's preferred language"""
    try:
        user_id = get_user_id()
        data = request.json
        language = data.get('language', 'en')
        
        # Store language preference in session
        session['preferred_language'] = language
        
        # Also save to database if needed
        db_service.update_user_profile(user_id, {'preferred_language': language})
        
        return jsonify({
            'success': True,
            'language': language,
            'message': f'Language set to {language}'
        })
    except Exception as e:
        return jsonify({'error': f'Error setting language: {str(e)}'}), 500

@app.route('/api/get_language')
def get_language():
    """Get user's preferred language"""
    try:
        user_id = get_user_id()
        language = session.get('preferred_language', 'en')
        return jsonify({'language': language})
    except Exception as e:
        return jsonify({'error': f'Error getting language: {str(e)}'}), 500

# RAG Endpoints for Student Doubts
@app.route('/api/ask_question', methods=['POST'])
@limiter.limit("20 per hour")
def ask_question():
    """Ask a question and get RAG-powered answer"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        user_id = get_user_id()
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Use the new process_question method that handles both curriculum and general knowledge
        answer_data = rag_service.process_question(question, llm_service, user_id)
        
        return jsonify({
            'success': True,
            'question': question,
            'answer': answer_data['answer'],
            'confidence': answer_data['confidence'],
            'sources': answer_data['sources'],
            'context_chunks': answer_data['context_chunks'],
            'answer_type': answer_data.get('answer_type', 'unknown')
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing question: {str(e)}'}), 500

@app.route('/api/question_history')
def get_question_history():
    """Get user's question history"""
    try:
        user_id = get_user_id()
        limit = request.args.get('limit', 10, type=int)
        history = rag_service.get_user_question_history(user_id, limit)
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': f'Error getting history: {str(e)}'}), 500

@app.route('/api/recent_questions')
def get_recent_questions():
    """Get recent questions for display"""
    try:
        user_id = get_user_id()
        limit = request.args.get('limit', 5, type=int)
        history = rag_service.get_user_question_history(user_id, limit)
        return jsonify({'questions': history})
    except Exception as e:
        return jsonify({'error': f'Error getting recent questions: {str(e)}'}), 500

@app.route('/api/related_questions', methods=['POST'])
def get_related_questions():
    """Get related questions based on current question"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # For now, return empty list - this can be enhanced with semantic search
        related_questions = []
        
        return jsonify({'questions': related_questions})
    except Exception as e:
        return jsonify({'error': f'Error getting related questions: {str(e)}'}), 500

@app.route('/api/rag_stats')
def get_rag_stats():
    """Get RAG database statistics"""
    try:
        stats = rag_service.get_database_stats()
        subject_stats = rag_service.get_subject_stats()
        stats['subject_stats'] = subject_stats
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': f'Error getting stats: {str(e)}'}), 500

# Enhanced Features API Endpoints

@app.route('/api/generate_questions_advanced', methods=['POST'])
@limiter.limit("20 per hour")
def generate_questions_advanced():
    """Generate questions with difficulty control and section selection"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        pdf_filename = data.get('pdf_filename')
        num_questions = data.get('num_questions', 5)
        question_type = data.get('question_type', 'mcq')
        difficulty = data.get('difficulty', 'medium')  # easy, medium, hard
        section_id = data.get('section_id')  # Optional: specific section
        
        if not pdf_filename:
            return jsonify({'error': 'PDF filename required'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'PDF file not found'}), 404
        
        # Extract text from specific section if provided
        if section_id:
            result = pdf_service.get_content_by_section(filepath, section_id)
            if not result['success']:
                return jsonify({'error': 'Failed to extract section content'}), 500
            text = result['content']
        else:
            # Extract full text
            result = pdf_service.extract_text_from_pdf(filepath)
            if not result['success']:
                return jsonify({'error': 'Failed to extract PDF content'}), 500
            text = result['text']
        
        # Generate questions with difficulty control
        questions = llm_service.generate_questions_from_text(
            text, num_questions, question_type, difficulty
        )
        
        return jsonify({
            'success': True,
            'questions': questions,
            'difficulty': difficulty,
            'section_id': section_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/adaptive_questions', methods=['POST'])
@limiter.limit("30 per hour")
def get_adaptive_questions():
    """Get questions adapted to student's level"""
    try:
        data = request.json
        user_id = get_user_id()
        topic = data.get('topic', 'general')
        num_questions = data.get('num_questions', 5)
        
        # Get adaptive recommendations
        adaptive_result = adaptive_learning.generate_adaptive_questions(
            user_id, topic, num_questions
        )
        
        return jsonify(adaptive_result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/record_attempt', methods=['POST'])
def record_question_attempt():
    """Record a student's attempt at a question"""
    try:
        data = request.json
        user_id = get_user_id()
        
        from services.adaptive_learning import QuestionAttempt
        from datetime import datetime
        
        attempt = QuestionAttempt(
            question_id=data.get('question_id', ''),
            topic=data.get('topic', 'general'),
            difficulty=data.get('difficulty', 'medium'),
            cognitive_level=data.get('cognitive_level', 'application'),
            correct=data.get('correct', False),
            time_taken=data.get('time_taken', 0.0),
            timestamp=datetime.now(),
            confidence=data.get('confidence', 0.5)
        )
        
        adaptive_learning.record_attempt(user_id, attempt)
        
        return jsonify({'success': True, 'message': 'Attempt recorded'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate_quiz_questions', methods=['POST'])
def generate_quiz_questions():
    """Generate quiz questions without requiring a PDF file"""
    try:
        print("🎯 Generate Quiz Questions endpoint called")
        
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        num_questions = data.get('num_questions', 10)
        question_type = data.get('question_type', 'mcq')
        difficulty = data.get('difficulty', 'medium')
        topic = data.get('topic', 'General')
        pdf_filename = data.get('pdf_filename', '')
        
        print(f"📝 Generating {num_questions} {question_type} questions (difficulty: {difficulty}, topic: {topic}, pdf: {pdf_filename})")
        
        # If PDF filename is provided, try to get cached questions from that PDF
        if pdf_filename and pdf_filename != 'quiz':
            try:
                cached_questions = db_service.get_questions_for_pdf(pdf_filename)
                if cached_questions and len(cached_questions) >= num_questions:
                    print(f"✅ Using cached questions from PDF: {pdf_filename}")
                    # Return a subset of cached questions
                    selected_questions = cached_questions[:num_questions]
                    return jsonify({'questions': selected_questions, 'source': 'pdf_cache'})
            except Exception as e:
                print(f"⚠️ Warning: Could not load cached questions for {pdf_filename}: {e}")
        
        # Generate sample questions for the quiz
        questions = []
        topics = ["Mathematics", "Science", "History", "Geography", "English", "General Knowledge"]
        
        for i in range(num_questions):
            current_topic = topics[i % len(topics)]
            question = {
                "question": f"Sample {difficulty} {current_topic} question {i+1}? This question tests your understanding of {current_topic.lower()} concepts.",
                "options": [
                    f"Option A - {current_topic} concept",
                    f"Option B - {current_topic} application", 
                    f"Option C - {current_topic} analysis",
                    f"Option D - {current_topic} synthesis"
                ],
                "answer": f"Option A - {current_topic} concept",
                "explanation": f"This is a {difficulty} level question about {current_topic}. Option A is correct because it represents the fundamental concept being tested. The other options are incorrect as they either represent misconceptions or incomplete understanding. Understanding this concept is important for building a strong foundation in {current_topic}. Practice similar questions to improve your understanding.",
                "topic": current_topic,
                "difficulty": difficulty,
                "cognitive_level": "application"
            }
            questions.append(question)
        
        print(f"✅ Generated {len(questions)} quiz questions successfully")
        return jsonify({'questions': questions, 'source': 'generated'})
        
    except Exception as e:
        print(f"❌ Error generating quiz questions: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error generating quiz questions: {str(e)}'}), 500

@app.route('/api/test_adaptive_learning', methods=['POST'])
def test_adaptive_learning():
    """Test endpoint to verify adaptive learning system is working"""
    try:
        user_id = get_user_id()
        print(f"🧪 Testing adaptive learning for user: {user_id}")
        
        # Create a test attempt
        from services.adaptive_learning import QuestionAttempt
        from datetime import datetime
        
        test_attempt = QuestionAttempt(
            question_id="test_question_1",
            topic="Mathematics",
            difficulty="medium",
            cognitive_level="application",
            correct=True,
            time_taken=30.0,
            timestamp=datetime.now(),
            confidence=0.8
        )
        
        # Record the test attempt
        adaptive_learning.record_attempt(user_id, test_attempt)
        
        # Get the analysis
        analysis = adaptive_learning.get_strength_analysis(user_id)
        
        return jsonify({
            'success': True,
            'message': 'Test attempt recorded successfully',
            'user_id': user_id,
            'analysis': analysis
        })
        
    except Exception as e:
        print(f"❌ Error in test_adaptive_learning: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error testing adaptive learning: {str(e)}'}), 500

@app.route('/api/student_analysis', methods=['GET'])
def get_student_analysis():
    """Get comprehensive student analysis"""
    try:
        user_id = get_user_id()
        print(f"🔍 Getting student analysis for user: {user_id}")
        
        # Check if adaptive_learning module is available
        if not hasattr(adaptive_learning, 'get_strength_analysis'):
            print("❌ adaptive_learning.get_strength_analysis method not found")
            return jsonify({'error': 'Adaptive learning service not available'}), 500
        
        # Check if user exists in adaptive learning system
        if user_id not in adaptive_learning.students:
            print(f"⚠️ User {user_id} not found in adaptive learning system, returning default data")
            return jsonify({
                'overall_score': 0.0,
                'total_questions': 0,
                'correct_answers': 0,
                'learning_pace': 0.0,
                'preferred_difficulty': 'medium',
                'weak_topics': [],
                'topic_performance': {},
                'cognitive_levels': {'easy': 0, 'medium': 0, 'hard': 0},
                'recommendations': ['Start taking quizzes to build your learning profile!']
            })
        
        analysis = adaptive_learning.get_strength_analysis(user_id)
        print(f"✅ Student analysis retrieved successfully: {len(analysis)} fields")
        print(f"📊 Analysis data: {analysis}")
        return jsonify(analysis)
        
    except Exception as e:
        print(f"❌ Error in get_student_analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error getting student analysis: {str(e)}'}), 500

# Teacher Mode Endpoints

@app.route('/api/teacher/create_class', methods=['POST'])
def create_class():
    """Create a new class for teacher"""
    try:
        data = request.json
        teacher_id = get_user_id()
        
        result = teacher_mode.create_class(
            teacher_id=teacher_id,
            name=data.get('name'),
            subject=data.get('subject'),
            grade=data.get('grade')
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teacher/classes', methods=['GET'])
def get_teacher_classes():
    """Get all classes for a teacher"""
    try:
        teacher_id = get_user_id()
        classes = teacher_mode.get_teacher_classes(teacher_id)
        return jsonify({'classes': classes})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/teacher/generate_paper', methods=['POST'])
def generate_question_paper():
    """Generate a question paper for a class"""
    try:
        # Check if this is a file upload or JSON request
        if request.files:
            # Handle file upload
            pdf_file = request.files.get('pdf')
            if not pdf_file:
                return jsonify({'error': 'No PDF file provided'}), 400
            
            # Validate file type
            if not pdf_file.filename.lower().endswith('.pdf'):
                return jsonify({'error': 'Only PDF files are allowed'}), 400
            
            # Save the uploaded file temporarily
            filename = secure_filename(pdf_file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"teacher_{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            pdf_file.save(filepath)
            
            # Extract text from PDF for question generation
            pdf_result = pdf_service.extract_text_from_pdf(filepath)
            if not pdf_result['success']:
                return jsonify({'error': 'Failed to process PDF file'}), 500
            
            pdf_content = pdf_result.get('text', '')
            
            # Get form data
            class_id = request.form.get('class_id')
            title = request.form.get('title')
            total_marks = int(request.form.get('total_marks', 100))
            duration_minutes = int(request.form.get('duration_minutes', 60))
            easy_count = int(request.form.get('easy_count', 2))
            medium_count = int(request.form.get('medium_count', 3))
            hard_count = int(request.form.get('hard_count', 1))
            instructions = request.form.get('instructions', '')
            
            difficulty_distribution = {
                'easy': easy_count,
                'medium': medium_count,
                'hard': hard_count
            }
            
            # Generate questions from PDF content
            result = teacher_mode.generate_question_paper_from_content(
                class_id=class_id,
                title=title,
                total_marks=total_marks,
                duration_minutes=duration_minutes,
                difficulty_distribution=difficulty_distribution,
                instructions=instructions,
                pdf_content=pdf_content,
                pdf_filename=unique_filename
            )
            
        else:
            # Handle JSON request (existing functionality)
            data = request.json
            
            result = teacher_mode.generate_question_paper(
                class_id=data.get('class_id'),
                title=data.get('title'),
                total_marks=data.get('total_marks', 100),
                duration_minutes=data.get('duration_minutes', 60),
                difficulty_distribution=data.get('difficulty_distribution', {
                    'easy': 2, 'medium': 3, 'hard': 1
                }),
                instructions=data.get('instructions', '')
            )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error generating question paper: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/teacher/export_paper/<paper_id>', methods=['GET'])
def export_question_paper(paper_id):
    """Export question paper in different formats"""
    try:
        format_type = request.args.get('format', 'html')
        result = teacher_mode.export_question_paper(paper_id, format_type)
        
        if result['success']:
            if format_type == 'html':
                return result['content'], 200, {'Content-Type': 'text/html'}
            else:
                return jsonify(result['content'])
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/multi_subject_search', methods=['POST'])
def multi_subject_search():
    """Search across multiple subjects"""
    try:
        data = request.json
        query = data.get('query')
        subjects = data.get('subjects')  # Optional: specific subjects to search
        
        if not query:
            return jsonify({'error': 'Query required'}), 400
        
        results = rag_service.search_across_subjects(query, subjects)
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pdf_structure/<filename>', methods=['GET'])
def get_pdf_structure(filename):
    """Get structured content from PDF"""
    try:
        print(f"📄 PDF Structure request for: {filename}")
        
        # Validate filename
        if not filename or not filename.endswith('.pdf'):
            print(f"❌ Invalid filename: {filename}")
            return jsonify({'error': 'Invalid PDF filename'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"📁 Looking for file at: {filepath}")
        
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            return jsonify({'error': 'PDF file not found'}), 404
        
        print(f"✅ File found, size: {os.path.getsize(filepath)} bytes")
        
        # Validate PDF first
        is_valid, message = pdf_service.validate_pdf(filepath)
        if not is_valid:
            print(f"❌ PDF validation failed: {message}")
            return jsonify({'error': f'PDF validation failed: {message}'}), 400
        
        print("✅ PDF validation passed, extracting structure...")
        
        # Extract text and structure
        result = pdf_service.extract_text_from_pdf(filepath)
        print(f"📊 Extraction result success: {result.get('success', False)}")
        
        if not result['success']:
            error_msg = result.get('error', 'Unknown error')
            print(f"❌ PDF extraction failed: {error_msg}")
            return jsonify({'error': f'Failed to extract PDF structure: {error_msg}'}), 500
        
        # Prepare response
        structure = result.get('structured_content', {})
        metadata = result.get('metadata', {})
        
        print(f"✅ Structure extracted successfully")
        print(f"📊 Structure keys: {list(structure.keys()) if structure else 'None'}")
        print(f"📊 Metadata keys: {list(metadata.keys()) if metadata else 'None'}")
        
        return jsonify({
            'success': True,
            'structure': structure,
            'metadata': metadata
        })
        
    except Exception as e:
        print(f"❌ Unexpected error in get_pdf_structure: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 Starting AI Tutor for Rural India...")
    print("📚 Features: PDF Processing, LLM Integration, Voice Features, Progress Tracking")
    print("🌐 Access at: http://localhost:5000")
    print("📊 Progress Dashboard: http://localhost:5000/progress")
    
    app.run(debug=True, host='0.0.0.0', port=5000) 