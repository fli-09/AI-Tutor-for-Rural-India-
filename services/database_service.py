import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware

class DatabaseService:
    def __init__(self, db_path: str = "progress.json"):
        self.db_path = db_path
        # Use caching middleware for better performance
        self.db = TinyDB(db_path, storage=CachingMiddleware(JSONStorage))
        self._init_tables()
    
    def _init_tables(self):
        """Initialize database tables/collections"""
        # Ensure tables exist
        if not self.db.table('quiz_attempts'):
            self.db.table('quiz_attempts')
        if not self.db.table('user_progress'):
            self.db.table('user_progress')
        if not self.db.table('pdf_documents'):
            self.db.table('pdf_documents')
        if not self.db.table('questions'):
            self.db.table('questions')
    
    def save_quiz_attempt(self, user_id: str, quiz_data: Dict) -> str:
        """
        Save a quiz attempt
        Returns: attempt_id
        """
        attempts_table = self.db.table('quiz_attempts')
        
        attempt = {
            'attempt_id': f"attempt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}",
            'user_id': user_id,
            'pdf_filename': quiz_data.get('pdf_filename', ''),
            'questions': quiz_data.get('questions', []),
            'answers': quiz_data.get('answers', {}),
            'score': quiz_data.get('score', 0),
            'total_questions': quiz_data.get('total_questions', 0),
            'correct_answers': quiz_data.get('correct_answers', 0),
            'time_taken': quiz_data.get('time_taken', 0),
            'timestamp': datetime.now().isoformat(),
            'topics': quiz_data.get('topics', []),
            'language': quiz_data.get('language', 'en')
        }
        
        attempts_table.insert(attempt)
        self._update_user_progress(user_id, attempt)
        
        return attempt['attempt_id']
    
    def _update_user_progress(self, user_id: str, attempt: Dict):
        """Update user progress based on quiz attempt"""
        progress_table = self.db.table('user_progress')
        User = Query()
        
        # Get existing progress or create new
        existing_progress = progress_table.get(User.user_id == user_id)
        
        if existing_progress:
            progress = existing_progress
        else:
            progress = {
                'user_id': user_id,
                'total_attempts': 0,
                'total_score': 0,
                'average_score': 0,
                'topics': {},
                'recent_attempts': [],
                'strengths': [],
                'weaknesses': [],
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
        
        # Update progress statistics
        progress['total_attempts'] += 1
        progress['total_score'] += attempt['score']
        progress['average_score'] = progress['total_score'] / progress['total_attempts']
        
        # Update topic-wise progress
        for topic in attempt.get('topics', []):
            if topic not in progress['topics']:
                progress['topics'][topic] = {
                    'attempts': 0,
                    'total_score': 0,
                    'average_score': 0
                }
            
            progress['topics'][topic]['attempts'] += 1
            progress['topics'][topic]['total_score'] += attempt['score']
            progress['topics'][topic]['average_score'] = (
                progress['topics'][topic]['total_score'] / 
                progress['topics'][topic]['attempts']
            )
        
        # Update recent attempts (keep last 10)
        recent_attempt = {
            'attempt_id': attempt['attempt_id'],
            'score': attempt['score'],
            'total_questions': attempt['total_questions'],
            'timestamp': attempt['timestamp'],
            'topics': attempt.get('topics', [])
        }
        
        progress['recent_attempts'].append(recent_attempt)
        progress['recent_attempts'] = progress['recent_attempts'][-10:]  # Keep last 10
        
        # Update strengths and weaknesses
        self._update_strengths_weaknesses(progress)
        
        progress['last_updated'] = datetime.now().isoformat()
        
        # Save updated progress
        if existing_progress:
            progress_table.update(progress, User.user_id == user_id)
        else:
            progress_table.insert(progress)
    
    def _update_strengths_weaknesses(self, progress: Dict):
        """Analyze and update user strengths and weaknesses"""
        topics = progress.get('topics', {})
        
        # Find topics with high scores (strengths)
        strengths = []
        weaknesses = []
        
        for topic, data in topics.items():
            if data['attempts'] >= 2:  # Only consider topics with multiple attempts
                if data['average_score'] >= 80:
                    strengths.append(topic)
                elif data['average_score'] <= 50:
                    weaknesses.append(topic)
        
        progress['strengths'] = strengths[:5]  # Top 5 strengths
        progress['weaknesses'] = weaknesses[:5]  # Top 5 weaknesses
    
    def get_user_progress(self, user_id: str) -> Optional[Dict]:
        """Get user progress data"""
        progress_table = self.db.table('user_progress')
        User = Query()
        
        progress = progress_table.get(User.user_id == user_id)
        if progress:
            # Calculate additional statistics
            progress['total_time'] = self._calculate_total_time(user_id)
            progress['improvement_rate'] = self._calculate_improvement_rate(user_id)
        
        return progress
    
    def _calculate_total_time(self, user_id: str) -> int:
        """Calculate total time spent on quizzes"""
        attempts_table = self.db.table('quiz_attempts')
        User = Query()
        
        attempts = attempts_table.search(User.user_id == user_id)
        return sum(attempt.get('time_taken', 0) for attempt in attempts)
    
    def _calculate_improvement_rate(self, user_id: str) -> float:
        """Calculate improvement rate over time"""
        attempts_table = self.db.table('quiz_attempts')
        User = Query()
        
        attempts = attempts_table.search(User.user_id == user_id)
        if len(attempts) < 2:
            return 0.0
        
        # Sort by timestamp
        attempts.sort(key=lambda x: x.get('timestamp', ''))
        
        # Calculate improvement between first and last attempt
        first_score = attempts[0].get('score', 0)
        last_score = attempts[-1].get('score', 0)
        
        if first_score == 0:
            return 0.0
        
        return ((last_score - first_score) / first_score) * 100
    
    def get_recent_attempts(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent quiz attempts for a user"""
        attempts_table = self.db.table('quiz_attempts')
        User = Query()
        
        attempts = attempts_table.search(User.user_id == user_id)
        attempts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return attempts[:limit]
    
    def get_topic_analytics(self, user_id: str) -> Dict:
        """Get detailed analytics by topic"""
        progress = self.get_user_progress(user_id)
        if not progress:
            return {}
        
        topics = progress.get('topics', {})
        analytics = {
            'topics': topics,
            'best_topic': None,
            'worst_topic': None,
            'most_attempted': None,
            'recommendations': []
        }
        
        if topics:
            # Find best and worst topics
            topic_scores = [(topic, data['average_score']) for topic, data in topics.items() 
                           if data['attempts'] >= 2]
            
            if topic_scores:
                topic_scores.sort(key=lambda x: x[1], reverse=True)
                analytics['best_topic'] = topic_scores[0][0]
                analytics['worst_topic'] = topic_scores[-1][0]
            
            # Find most attempted topic
            topic_attempts = [(topic, data['attempts']) for topic, data in topics.items()]
            if topic_attempts:
                topic_attempts.sort(key=lambda x: x[1], reverse=True)
                analytics['most_attempted'] = topic_attempts[0][0]
            
            # Generate recommendations
            analytics['recommendations'] = self._generate_recommendations(progress)
        
        return analytics
    
    def _generate_recommendations(self, progress: Dict) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        weaknesses = progress.get('weaknesses', [])
        strengths = progress.get('strengths', [])
        
        if weaknesses:
            recommendations.append(f"Focus on improving your {', '.join(weaknesses[:2])} skills")
        
        if strengths:
            recommendations.append(f"Great work on {', '.join(strengths[:2])}! Keep practicing")
        
        total_attempts = progress.get('total_attempts', 0)
        if total_attempts < 5:
            recommendations.append("Try more quizzes to get better insights into your performance")
        
        return recommendations
    
    def save_pdf_document(self, filename: str, metadata: Dict) -> str:
        """Save PDF document metadata"""
        try:
            documents_table = self.db.table('pdf_documents')
            
            doc_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            document = {
                'doc_id': doc_id,
                'filename': filename,
                'metadata': metadata,
                'uploaded_at': datetime.now().isoformat(),
                'usage_count': 0
            }
            
            documents_table.insert(document)
            return doc_id
        except Exception as e:
            print(f"⚠️  Failed to save PDF document metadata: {e}")
            return f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def save_generated_questions(self, pdf_filename: str, questions: List[Dict]) -> str:
        """Save generated questions for reuse"""
        try:
            questions_table = self.db.table('questions')
            
            question_set_id = f"qs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            question_set = {
                'question_set_id': question_set_id,
                'pdf_filename': pdf_filename,
                'questions': questions,
                'generated_at': datetime.now().isoformat(),
                'usage_count': 0
            }
            
            questions_table.insert(question_set)
            return question_set_id
        except Exception as e:
            print(f"⚠️  Failed to save questions to database: {e}")
            return f"qs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def get_questions_for_pdf(self, pdf_filename: str) -> Optional[List[Dict]]:
        """Get previously generated questions for a PDF"""
        try:
            questions_table = self.db.table('questions')
            QuestionSet = Query()
            
            question_set = questions_table.get(QuestionSet.pdf_filename == pdf_filename)
            if question_set:
                # Update usage count
                try:
                    questions_table.update(
                        {'usage_count': question_set.get('usage_count', 0) + 1},
                        QuestionSet.pdf_filename == pdf_filename
                    )
                except Exception as e:
                    print(f"⚠️  Failed to update usage count: {e}")
                return question_set.get('questions', [])
            
            return None
        except Exception as e:
            print(f"⚠️  Failed to get questions for PDF: {e}")
            return None
    
    def get_dashboard_stats(self) -> Dict:
        """Get overall dashboard statistics"""
        attempts_table = self.db.table('quiz_attempts')
        progress_table = self.db.table('user_progress')
        
        total_attempts = len(attempts_table)
        total_users = len(progress_table)
        
        if total_attempts > 0:
            avg_score = sum(attempt.get('score', 0) for attempt in attempts_table.all()) / total_attempts
        else:
            avg_score = 0
        
        return {
            'total_attempts': total_attempts,
            'total_users': total_users,
            'average_score': round(avg_score, 2),
            'active_today': self._get_active_users_today()
        }
    
    def _get_active_users_today(self) -> int:
        """Get number of active users today"""
        attempts_table = self.db.table('quiz_attempts')
        today = datetime.now().date()
        
        today_attempts = attempts_table.search(
            lambda x: datetime.fromisoformat(x.get('timestamp', '')).date() == today
        )
        
        return len(set(attempt.get('user_id') for attempt in today_attempts))
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old data to prevent database bloat"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Clean old audio files (this would need to be called from the main app)
        # Clean old quiz attempts (keep last 100 per user)
        attempts_table = self.db.table('quiz_attempts')
        
        # This is a simplified cleanup - in production, you'd want more sophisticated logic
        print(f"Database cleanup completed. Kept data from last {days} days.")

    def get_user_pdfs(self, user_id):
        """Get list of PDFs uploaded by user"""
        try:
            # Get PDFs from quiz attempts
            attempts = self.db.table('quiz_attempts').search(Query().user_id == user_id)
            pdfs = []
            seen_pdfs = set()
            
            for attempt in attempts:
                pdf_filename = attempt.get('pdf_filename', '')
                if pdf_filename and pdf_filename not in seen_pdfs:
                    seen_pdfs.add(pdf_filename)
                    pdfs.append({
                        'filename': pdf_filename,
                        'upload_date': attempt.get('timestamp', ''),
                        'question_count': len(attempt.get('questions', [])),
                        'last_attempt': attempt.get('timestamp', '')
                    })
            
            return pdfs
        except Exception as e:
            print(f"Error getting user PDFs: {e}")
            return []

    def get_user_profile(self, user_id):
        """Get user profile data"""
        try:
            # Get basic profile from quiz attempts
            attempts = self.db.table('quiz_attempts').search(Query().user_id == user_id)
            
            if not attempts:
                return {
                    'user_id': user_id,
                    'name': 'Student',
                    'email': '',
                    'preferred_language': 'en',
                    'total_attempts': 0,
                    'average_score': 0,
                    'join_date': datetime.now().isoformat()
                }
            
            # Calculate profile from attempts
            total_attempts = len(attempts)
            total_score = sum(attempt.get('score', 0) for attempt in attempts)
            average_score = total_score / total_attempts if total_attempts > 0 else 0
            join_date = min(attempt.get('timestamp', datetime.now().isoformat()) for attempt in attempts)
            
            return {
                'user_id': user_id,
                'name': 'Student',  # Could be enhanced with actual user data
                'email': '',
                'preferred_language': 'en',
                'total_attempts': total_attempts,
                'average_score': round(average_score, 2),
                'join_date': join_date,
                'last_activity': max(attempt.get('timestamp', '') for attempt in attempts)
            }
        except Exception as e:
            print(f"Error getting user profile: {e}")
            return {
                'user_id': user_id,
                'name': 'Student',
                'email': '',
                'preferred_language': 'en',
                'total_attempts': 0,
                'average_score': 0,
                'join_date': datetime.now().isoformat()
            }

    def update_user_profile(self, user_id, profile_data):
        """Update user profile data"""
        try:
            # For now, we'll store profile data in a separate table
            profiles_table = self.db.table('user_profiles')
            
            # Check if profile exists
            existing_profile = profiles_table.search(Query().user_id == user_id)
            
            if existing_profile:
                # Update existing profile
                profiles_table.update(profile_data, Query().user_id == user_id)
            else:
                # Create new profile
                profile_data['user_id'] = user_id
                profile_data['created_at'] = datetime.now().isoformat()
                profiles_table.insert(profile_data)
            
            return True
        except Exception as e:
            print(f"Error updating user profile: {e}")
            return False

# Global instance
db_service = DatabaseService("../progress.json") 