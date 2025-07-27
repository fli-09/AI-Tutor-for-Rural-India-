📘 AI Tutor for Rural India
Empowering every rural student with AI-driven, curriculum-aligned education.
This web-based platform provides students in low-connectivity regions with access to personalized learning, interactive quizzes, voice-assisted content, and powerful teacher tools for question generation. It's designed to bridge the urban-rural education gap by making quality learning accessible to all.

🌟 Key Features
For Students
📚 PDF Learning System: Upload any NCERT or State Board PDF to instantly generate study materials and notes.

🤖 AI-Powered Q&A: Ask questions about your curriculum in plain language and get instant, accurate answers.

✍️ Interactive Quizzes: Practice with smart, multiple-choice quizzes that provide instant scoring and feedback to help you master topics.

🗣️ Full Voice Support:

Text-to-Speech (TTS): Have lessons and questions read aloud to you.

Speech-to-Text (STT): Answer questions and interact with the platform using just your voice.

🌐 Multilingual Interface: Access content and interact with the tutor in 10+ Indian languages.

📈 Personal Progress Dashboard: Track your performance, identify strengths and weaknesses, and get personalized learning recommendations.

For Teachers
📝 Custom Question Paper Generator: Create high-quality question papers from uploaded materials in seconds.

📊 Student Performance Analytics: Monitor class progress, track individual student performance, and generate insightful reports.

📤 Multiple Export Formats: Download question papers and reports in PDF, DOCX, or plain text.

🧠 Why This Project Matters
Unlike generic e-learning apps, our AI Tutor is built from the ground up to solve the unique challenges of rural education in India.

Feature

Generic Apps

AI Tutor for Rural India

Connectivity

Requires stable, high-speed internet.

Designed for low-bandwidth areas with an offline-first architecture.

Curriculum

Limited to a fixed, often urban-centric curriculum.

Accepts any curriculum PDF, making it hyper-relevant to any state board.

Accessibility

Primarily text-based and in English/Hindi.

Provides real-time voice support in local languages for low-literacy users.

Learning Model

Static, one-size-fits-all video lessons.

Offers adaptive learning paths and personalized analytics.

🛠️ Tech Stack
Component

Technology / Library

Frontend

HTML, CSS, JavaScript (Bootstrap for responsive UI)

Backend

Flask (Python)

AI/NLP

Gemini API (online), Phi-3 (local fallback), Hugging Face Transformers

PDF Processing

PyMuPDF

Vector Search (RAG)

ChromaDB

Voice I/O

Whisper (STT), gTTS / Pyttsx3 (TTS)

Database

TinyDB (lightweight, easily extendable to SQLite/PostgreSQL)

Deployment

Flask + Gunicorn (or Docker for production)

🚀 Getting Started
1. Prerequisites
Python 3.9+

pip and venv

2. Quick Setup
Clone the repository and set up the virtual environment.

# Clone the repository
git clone https://github.com/your-username/ai-tutor.git
cd ai-tutor

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate

# Install the required packages
pip install -r requirements.txt

3. Run the Application
Start the Flask development server.

python src/app.py

Navigate to http://127.0.0.1:5000 in your web browser.

📊 How It Works
Upload: A teacher or student uploads a curriculum PDF (e.g., NCERT, State Board textbook).

Process: The AI backend extracts and chunks the text, creating a vector-based knowledge base using a Retrieval-Augmented Generation (RAG) pipeline.

Interact: Students can now generate quizzes, ask questions, and take voice-enabled tests based on the uploaded content.

Analyze: Teachers can create question papers and view a dashboard with detailed analytics of student performance.

Adapt: The system tracks performance data to provide adaptive learning recommendations, helping students focus on their weak points.

✅ Future Roadmap
[ ] Mobile App: Develop a Flutter-based mobile application with full offline capabilities.

[ ] Preloaded Library: Integrate a pre-loaded NCERT library for instant access without uploads.

[ ] Gamification: Introduce points, badges, and leaderboards to make learning more engaging.

[ ] Personalized Learning Paths: Implement an AI-powered recommendation engine to create fully adaptive learning journeys for each student.

🤝 Contributing
Contributions are welcome! Whether it's bug fixes, new features, or documentation improvements, please feel free to open an issue or submit a pull request.

Fork the repository.

Create your feature branch (git checkout -b feature/AmazingFeature).

Commit your changes (git commit -m 'Add some AmazingFeature').

Push to the branch (git push origin feature/AmazingFeature).

Open a Pull Request.

📄 License
This project is licensed under the MIT License. See the LICENSE file for details.
