AI Tutor for Rural India 🎓
Empowering rural students with AI-driven, curriculum-aligned education.
This web-based platform provides students in low-connectivity regions with access to personalized learning, interactive quizzes, voice-assisted content, and teacher tools for question generation.

🌟 Key Features
For Students
PDF Learning System: Upload NCERT/State Board PDFs to auto-generate study material.

AI Question Generation: Create smart, curriculum-aligned questions (using Gemini 2.5 Flash or local models).

Quiz System: Practice interactive multiple-choice quizzes with instant scoring & feedback.

Voice Support:

Text-to-Speech (TTS): Reads lessons/questions aloud.

Speech-to-Text (STT): Enables voice answers.

Multilingual: Supports 10+ Indian languages.

Progress Tracking: Personal dashboards with strengths, weaknesses, and analytics.

For Teachers
Create custom question papers from uploaded materials.

Track student performance and generate reports.

Export ready-made papers in multiple formats.

🧠 Why This Project Matters
Unlike generic e-learning apps, AI Tutor for Rural India is:

Designed for low-bandwidth areas (offline-first).

Accepts any curriculum PDF—making it adaptable to different state boards.

Provides real-time voice support for low-literacy users.

Offers analytics & adaptive learning paths instead of just static lessons.

🛠 Tech Stack
Frontend: HTML, CSS, JavaScript (Bootstrap for responsive UI)
Backend: Flask (Python)
AI/NLP: Gemini 2.5 Flash API (online), Phi-3 (local fallback), Hugging Face models
PDF Processing: PyMuPDF
Vector Search (RAG): ChromaDB
Voice: Whisper (STT), gTTS/Pyttsx3 (TTS)
Database: TinyDB (lightweight), ready to extend to SQLite/PostgreSQL
Deployment: Flask + Gunicorn (or Docker for production)

🚀1. Quick Setup
bash
Copy
Edit
git clone <repo-url>
cd ai-tutor
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python src/app.py

2. Run the App
bash
Copy
Edit
cd src
python app.py

📊 How It Works
Upload Curriculum PDFs (NCERT/State Boards)

AI extracts and chunks text → creates a knowledge base (RAG).

Students generate quizzes & take voice-enabled tests.

Teachers download question papers & view analytics.

System tracks performance → gives adaptive learning recommendations.

🎯 Why It’s Unique
✔ Works in low-bandwidth rural areas
✔ Supports offline-first design (local TTS/STT + caching)
✔ Custom curriculum upload → hyper-local relevance
✔ Multilingual + voice-first UI → helps low-literacy students

✅ Future Roadmap
 Mobile app (Flutter) for full offline use

 Preloaded NCERT library for instant access

 Gamified quizzes for engagement

 AI-powered personalized learning paths

