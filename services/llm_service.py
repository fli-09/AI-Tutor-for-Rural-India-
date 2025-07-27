import os
import google.generativeai as genai
from typing import List, Dict, Optional
import json
import requests

class LLMService:
    def __init__(self):
        print("🤖 Initializing LLM Service...")
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.is_online = self._check_internet_connection()
        
        print(f"🔑 Gemini API Key available: {bool(self.gemini_api_key)}")
        print(f"🌐 Internet connection: {self.is_online}")
        
        if self.gemini_api_key and self.is_online:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                print("✅ Gemini model initialized successfully")
            except Exception as e:
                print(f"❌ Error initializing Gemini model: {e}")
                self.model = None
        else:
            self.model = None
            print("⚠️ Using offline mode - no Gemini API key or internet connection")
        
        print("🤖 LLM Service initialization completed")
    
    def _check_internet_connection(self) -> bool:
        """Check if internet connection is available"""
        try:
            requests.get("https://www.google.com", timeout=3)
            return True
        except:
            return False
    
    def generate_questions_from_text(self, text: str, num_questions: int = 5, 
                                   question_type: str = "mcq", difficulty: str = "medium") -> List[Dict]:
        """
        Generate questions from extracted text using Gemini or fallback
        """
        try:
            print(f"🤖 Generating {num_questions} {question_type} questions (difficulty: {difficulty})")
            print(f"📄 Text length: {len(text)} characters")
            
            if not text or len(text.strip()) < 100:
                print("❌ Text too short for question generation")
                return self._generate_offline_questions(text, num_questions, question_type, difficulty)
            
            if self.model and self.is_online:
                print("🌐 Using Gemini API for question generation")
                return self._generate_with_gemini(text, num_questions, question_type, difficulty)
            else:
                print("📚 Using offline question generation")
                return self._generate_offline_questions(text, num_questions, question_type, difficulty)
        except Exception as e:
            print(f"❌ Error generating questions: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_offline_questions(text, num_questions, question_type, difficulty)
    
    def _generate_with_gemini(self, text: str, num_questions: int, 
                            question_type: str, difficulty: str = "medium") -> List[Dict]:
        """Generate questions using Gemini API with difficulty control"""
        try:
            difficulty_instructions = {
                "easy": "Generate basic recall questions that test fundamental concepts and definitions. Focus on simple facts and basic understanding.",
                "medium": "Generate application-based questions that require students to apply concepts to new situations. Include problem-solving and analysis.",
                "hard": "Generate analytical questions that require critical thinking, synthesis of multiple concepts, and complex problem-solving."
            }
            
            difficulty_instruction = difficulty_instructions.get(difficulty, difficulty_instructions["medium"])
            
            prompt = f"""
            Generate {num_questions} {question_type.upper()} questions based on this educational content.
            Focus on NCERT/State Board curriculum standards for Indian students.
            
            DIFFICULTY LEVEL: {difficulty.upper()}
            {difficulty_instruction}
            
            Content: {text[:3000]}  # Limit text length
            
            Return ONLY a JSON array with this exact format:
            [
                {{
                    "question": "Question text here?",
                    "options": ["A", "B", "C", "D"],
                    "answer": "Correct answer",
                    "explanation": "Detailed explanation including why this answer is correct, why others are wrong, key concepts, and real-world examples",
                    "topic": "Subject topic",
                    "difficulty": "{difficulty}",
                    "cognitive_level": "recall|application|analysis"
                }}
            ]
            
            IMPORTANT REQUIREMENTS:
            1. Make questions appropriate for rural Indian students (grades 6-12)
            2. Provide detailed, educational explanations that help students learn
            3. Include real-world examples relevant to Indian context
            4. Ensure explanations are clear and encouraging
            5. Make sure the answer field matches exactly one of the options
            """
            
            response = self.model.generate_content(prompt)
            try:
                # Clean the response to remove markdown code blocks
                response_text = response.text.strip()
                
                # Remove markdown code block markers if present
                if response_text.startswith('```json'):
                    response_text = response_text[7:]  # Remove ```json
                if response_text.startswith('```'):
                    response_text = response_text[3:]  # Remove ```
                if response_text.endswith('```'):
                    response_text = response_text[:-3]  # Remove ```
                
                # Clean up any remaining whitespace
                response_text = response_text.strip()
                
                print(f"🧹 Cleaned response text: {response_text[:200]}...")
                
                questions = json.loads(response_text)
                print(f"✅ Successfully parsed {len(questions)} questions from JSON")
                return questions[:num_questions]
            except json.JSONDecodeError as json_error:
                print(f"JSON parsing error: {json_error}")
                print(f"Response text: {response.text[:200]}...")
                return self._generate_offline_questions(text, num_questions, question_type, difficulty)
            
        except Exception as e:
            print(f"Gemini API error: {e}")
            return self._generate_offline_questions(text, num_questions, question_type, difficulty)
    
    def _generate_offline_questions(self, text: str, num_questions: int, 
                                  question_type: str, difficulty: str = "medium") -> List[Dict]:
        """Fallback question generation for offline mode with difficulty levels"""
        # Simple template-based question generation
        topics = ["Mathematics", "Science", "History", "Geography", "English"]
        cognitive_levels = {
            "easy": "recall",
            "medium": "application", 
            "hard": "analysis"
        }
        
        questions = []
        
        for i in range(num_questions):
            topic = topics[i % len(topics)]
            question = {
                "question": f"Sample {difficulty} question {i+1} based on the uploaded content?",
                "options": [f"Option A", f"Option B", f"Option C", f"Option D"],
                "answer": "Option A",
                "explanation": f"This is a {difficulty} level question about {topic}. Option A is correct because it represents the fundamental concept being tested. The other options are incorrect as they either represent misconceptions or incomplete understanding. Understanding this concept is important for building a strong foundation in {topic}. Practice similar questions to improve your understanding.",
                "topic": topic,
                "difficulty": difficulty,
                "cognitive_level": cognitive_levels.get(difficulty, "application")
            }
            questions.append(question)
        
        return questions
    
    def generate_explanation(self, question: str, answer: str) -> str:
        """Generate detailed explanation for a question"""
        if self.model and self.is_online:
            try:
                prompt = f"""
                Provide a comprehensive, educational explanation for this question and answer:
                Question: {question}
                Correct Answer: {answer}
                
                Please provide a detailed explanation that includes:
                1. Why this answer is correct
                2. Why the other options are incorrect (if applicable)
                3. Key concepts and principles involved
                4. Real-world examples or applications (if relevant)
                5. Tips for remembering this concept
                
                Write in simple, clear language suitable for rural Indian students (grades 6-12).
                Use examples that are relatable to Indian context.
                IMPORTANT: Provide your explanation in plain text without any markdown formatting, 
                bullet points, asterisks (*), or special symbols.
                Keep the explanation educational and encouraging.
                """
                response = self.model.generate_content(prompt)
                
                # Clean up the response to remove any remaining markdown
                explanation = response.text
                
                # Remove markdown symbols
                explanation = explanation.replace('**', '')  # Remove bold
                explanation = explanation.replace('*', '')   # Remove italics
                explanation = explanation.replace('`', '')   # Remove code formatting
                explanation = explanation.replace('#', '')   # Remove headers
                explanation = explanation.replace('- ', '')  # Remove bullet points
                explanation = explanation.replace('• ', '')  # Remove bullet points
                
                # Clean up extra whitespace but preserve paragraph breaks
                explanation = '\n\n'.join([line.strip() for line in explanation.split('\n') if line.strip()])
                
                return explanation
            except Exception as e:
                print(f"Error generating explanation: {e}")
                return f"Explanation: {answer} is the correct answer. This question tests your understanding of the topic. Review the related concepts to improve your knowledge."
        else:
            return f"Explanation: {answer} is the correct answer. This question tests your understanding of the topic. Review the related concepts to improve your knowledge."
    
    def generate_answer(self, prompt: str) -> str:
        """Generate an answer based on a prompt"""
        if self.model and self.is_online:
            try:
                # Add instructions to avoid markdown formatting
                clean_prompt = f"""
                {prompt}
                
                IMPORTANT: Provide your answer in plain text without any markdown formatting, 
                bullet points, asterisks (*), or special symbols. Use simple, clear language 
                suitable for rural Indian students. Write in a natural, conversational style.
                """
                
                response = self.model.generate_content(clean_prompt)
                
                # Clean up the response to remove any remaining markdown
                answer = response.text
                
                # Remove markdown symbols
                answer = answer.replace('**', '')  # Remove bold
                answer = answer.replace('*', '')   # Remove italics
                answer = answer.replace('`', '')   # Remove code formatting
                answer = answer.replace('#', '')   # Remove headers
                
                # Clean up extra whitespace
                answer = ' '.join(answer.split())
                
                return answer
            except Exception as e:
                print(f"Error generating answer: {e}")
                return "I'm sorry, I couldn't generate an answer at the moment. Please try again."
        else:
            return "I'm sorry, I'm currently in offline mode and cannot generate answers. Please check your internet connection."

# Global instance
llm_service = LLMService() 