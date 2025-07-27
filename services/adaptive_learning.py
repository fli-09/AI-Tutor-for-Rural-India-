#!/usr/bin/env python3
"""
Adaptive Learning System
Tracks student performance and adjusts question difficulty automatically
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import statistics

@dataclass
class QuestionAttempt:
    """Represents a student's attempt at a question"""
    question_id: str
    topic: str
    difficulty: str
    cognitive_level: str
    correct: bool
    time_taken: float  # seconds
    timestamp: datetime
    confidence: float  # 0-1, how confident the student was

@dataclass
class StudentProfile:
    """Represents a student's learning profile"""
    user_id: str
    topic_performance: Dict[str, Dict]  # topic -> {easy: score, medium: score, hard: score}
    cognitive_levels: Dict[str, float]  # cognitive_level -> average_score
    learning_pace: float  # questions per minute
    preferred_difficulty: str  # auto-calculated
    last_activity: datetime
    total_questions: int
    correct_answers: int

class AdaptiveLearningSystem:
    def __init__(self, db_file: str = "adaptive_learning.json"):
        self.db_file = db_file
        print(f"🤖 Initializing AdaptiveLearningSystem with db_file: {db_file}")
        try:
            self.students = self._load_data()
            print(f"✅ AdaptiveLearningSystem initialized successfully with {len(self.students)} students")
        except Exception as e:
            print(f"❌ Error initializing AdaptiveLearningSystem: {e}")
            self.students = {}
        
    def _load_data(self) -> Dict:
        """Load student data from file"""
        print(f"📁 Loading adaptive learning data from: {self.db_file}")
        print(f"📁 File exists: {os.path.exists(self.db_file)}")
        
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"📊 Loaded {len(data)} student profiles from file")
                    
                    # Convert timestamps back to datetime objects and recreate StudentProfile objects
                    loaded_data = {}
                    for user_id, profile_data in data.items():
                        try:
                            # Convert last_activity back to datetime
                            if 'last_activity' in profile_data:
                                try:
                                    profile_data['last_activity'] = datetime.fromisoformat(profile_data['last_activity'])
                                except Exception as e:
                                    print(f"⚠️ Warning: Could not parse timestamp for user {user_id}: {e}")
                                    profile_data['last_activity'] = datetime.now()
                            
                            # Recreate StudentProfile object
                            profile = StudentProfile(
                                user_id=profile_data.get('user_id', user_id),
                                topic_performance=profile_data.get('topic_performance', {}),
                                cognitive_levels=profile_data.get('cognitive_levels', {}),
                                learning_pace=profile_data.get('learning_pace', 0.0),
                                preferred_difficulty=profile_data.get('preferred_difficulty', 'medium'),
                                last_activity=profile_data.get('last_activity', datetime.now()),
                                total_questions=profile_data.get('total_questions', 0),
                                correct_answers=profile_data.get('correct_answers', 0)
                            )
                            
                            # Restore recent_times if it exists
                            if 'recent_times' in profile_data:
                                profile.recent_times = profile_data.get('recent_times', [])
                            
                            loaded_data[user_id] = profile
                            
                        except Exception as e:
                            print(f"⚠️ Warning: Could not load profile for user {user_id}: {e}")
                            continue
                    
                    print(f"✅ Successfully loaded {len(loaded_data)} student profiles")
                    return loaded_data
                    
            except Exception as e:
                print(f"❌ Error loading adaptive learning data: {e}")
                import traceback
                traceback.print_exc()
                return {}
        else:
            print(f"📁 Adaptive learning data file not found: {self.db_file}")
            print(f"📁 Creating new empty database")
            return {}
    
    def _save_data(self):
        """Save student data to file"""
        try:
            print(f"💾 Saving adaptive learning data to: {self.db_file}")
            
            # Convert datetime objects to strings for JSON serialization
            data_to_save = {}
            for user_id, profile_data in self.students.items():
                # Convert to dictionary
                if hasattr(profile_data, '__dict__'):
                    data_to_save[user_id] = asdict(profile_data)
                else:
                    data_to_save[user_id] = profile_data
                
                # Convert datetime to string
                if 'last_activity' in data_to_save[user_id]:
                    data_to_save[user_id]['last_activity'] = data_to_save[user_id]['last_activity'].isoformat()
                
                # Add recent_times if it exists
                if hasattr(profile_data, 'recent_times') and profile_data.recent_times:
                    data_to_save[user_id]['recent_times'] = profile_data.recent_times
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
            
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Successfully saved adaptive learning data for {len(data_to_save)} users")
            
        except Exception as e:
            print(f"❌ Error saving adaptive learning data: {e}")
            import traceback
            traceback.print_exc()
    
    def record_attempt(self, user_id: str, attempt: QuestionAttempt):
        """Record a student's attempt at a question"""
        if user_id not in self.students:
            self.students[user_id] = StudentProfile(
                user_id=user_id,
                topic_performance={},
                cognitive_levels={},
                learning_pace=0.0,
                preferred_difficulty="medium",
                last_activity=datetime.now(),
                total_questions=0,
                correct_answers=0
            )
        
        profile = self.students[user_id]
        
        # Update basic stats
        profile.total_questions += 1
        if attempt.correct:
            profile.correct_answers += 1
        profile.last_activity = datetime.now()
        
        # Update topic performance
        if attempt.topic not in profile.topic_performance:
            profile.topic_performance[attempt.topic] = {
                'easy': {'correct': 0, 'total': 0},
                'medium': {'correct': 0, 'total': 0},
                'hard': {'correct': 0, 'total': 0}
            }
        
        topic_stats = profile.topic_performance[attempt.topic][attempt.difficulty]
        topic_stats['total'] += 1
        if attempt.correct:
            topic_stats['correct'] += 1
        
        # Update cognitive level performance
        if attempt.cognitive_level not in profile.cognitive_levels:
            profile.cognitive_levels[attempt.cognitive_level] = {'correct': 0, 'total': 0}
        
        profile.cognitive_levels[attempt.cognitive_level]['total'] += 1
        if attempt.correct:
            profile.cognitive_levels[attempt.cognitive_level]['correct'] += 1
        
        # Update learning pace (questions per minute)
        self._update_learning_pace(profile, attempt)
        
        # Update preferred difficulty
        self._update_preferred_difficulty(profile)
        
        self._save_data()
    
    def _update_learning_pace(self, profile: StudentProfile, attempt: QuestionAttempt):
        """Update student's learning pace"""
        # Simple moving average of time taken
        if not hasattr(profile, 'recent_times'):
            profile.recent_times = []
        
        profile.recent_times.append(attempt.time_taken)
        if len(profile.recent_times) > 20:  # Keep last 20 attempts
            profile.recent_times = profile.recent_times[-20:]
        
        avg_time = statistics.mean(profile.recent_times)
        profile.learning_pace = 60.0 / avg_time if avg_time > 0 else 0.0
    
    def _update_preferred_difficulty(self, profile: StudentProfile):
        """Update student's preferred difficulty based on performance"""
        # Calculate overall performance by difficulty
        difficulty_scores = {'easy': 0.0, 'medium': 0.0, 'hard': 0.0}
        difficulty_counts = {'easy': 0, 'medium': 0, 'hard': 0}
        
        for topic_stats in profile.topic_performance.values():
            for difficulty, stats in topic_stats.items():
                if stats['total'] > 0:
                    score = stats['correct'] / stats['total']
                    difficulty_scores[difficulty] += score
                    difficulty_counts[difficulty] += 1
        
        # Calculate average scores
        avg_scores = {}
        for difficulty in difficulty_scores:
            if difficulty_counts[difficulty] > 0:
                avg_scores[difficulty] = difficulty_scores[difficulty] / difficulty_counts[difficulty]
            else:
                avg_scores[difficulty] = 0.0
        
        # Determine preferred difficulty
        if avg_scores['hard'] >= 0.7:
            profile.preferred_difficulty = "hard"
        elif avg_scores['medium'] >= 0.6:
            profile.preferred_difficulty = "medium"
        else:
            profile.preferred_difficulty = "easy"
    
    def get_recommended_difficulty(self, user_id: str, topic: str = None) -> str:
        """Get recommended difficulty for a student"""
        if user_id not in self.students:
            return "medium"  # Default for new students
        
        profile = self.students[user_id]
        
        # If topic-specific recommendation is requested
        if topic and topic in profile.topic_performance:
            topic_stats = profile.topic_performance[topic]
            
            # Calculate topic-specific scores
            scores = {}
            for difficulty, stats in topic_stats.items():
                if stats['total'] >= 3:  # Need at least 3 attempts
                    scores[difficulty] = stats['correct'] / stats['total']
                else:
                    scores[difficulty] = 0.0
            
            # Recommend based on topic performance
            if scores.get('hard', 0) >= 0.7:
                return "hard"
            elif scores.get('medium', 0) >= 0.6:
                return "medium"
            else:
                return "easy"
        
        # Return general preferred difficulty
        return profile.preferred_difficulty
    
    def get_weak_topics(self, user_id: str, limit: int = 5) -> List[Tuple[str, float]]:
        """Get student's weakest topics"""
        if user_id not in self.students:
            return []
        
        profile = self.students[user_id]
        topic_scores = []
        
        for topic, stats in profile.topic_performance.items():
            total_correct = 0
            total_questions = 0
            
            for difficulty_stats in stats.values():
                total_correct += difficulty_stats['correct']
                total_questions += difficulty_stats['total']
            
            if total_questions >= 5:  # Need at least 5 questions
                score = total_correct / total_questions
                topic_scores.append((topic, score))
        
        # Sort by score (ascending) and return weakest topics
        topic_scores.sort(key=lambda x: x[1])
        return topic_scores[:limit]
    
    def get_strength_analysis(self, user_id: str) -> Dict:
        """Get comprehensive strength analysis for a student"""
        if user_id not in self.students:
            return {
                'overall_score': 0.0,
                'total_questions': 0,
                'correct_answers': 0,
                'learning_pace': 0.0,
                'preferred_difficulty': 'medium',
                'weak_topics': [],
                'topic_performance': {},
                'cognitive_levels': {'easy': 0, 'medium': 0, 'hard': 0},
                'recommendations': []
            }
        
        profile = self.students[user_id]
        
        # Calculate overall score
        overall_score = profile.correct_answers / profile.total_questions if profile.total_questions > 0 else 0.0
        
        # Calculate topic performance (average score per topic)
        topic_performance = {}
        for topic, stats in profile.topic_performance.items():
            total_correct = 0
            total_questions = 0
            
            for difficulty_stats in stats.values():
                total_correct += difficulty_stats['correct']
                total_questions += difficulty_stats['total']
            
            if total_questions > 0:
                topic_performance[topic] = total_correct / total_questions
            else:
                topic_performance[topic] = 0.0
        
        # Calculate cognitive level counts
        cognitive_levels = {'easy': 0, 'medium': 0, 'hard': 0}
        for cognitive_level, stats in profile.cognitive_levels.items():
            if cognitive_level in cognitive_levels:
                cognitive_levels[cognitive_level] = stats['total']
        
        # Generate recommendations
        recommendations = []
        
        if overall_score < 0.5:
            recommendations.append("Focus on fundamental concepts and basic recall questions")
        elif overall_score < 0.7:
            recommendations.append("Practice application-based questions to improve understanding")
        else:
            recommendations.append("Challenge yourself with analytical and complex problem-solving questions")
        
        weak_topics = self.get_weak_topics(user_id, 3)
        if weak_topics:
            recommendations.append(f"Focus on improving: {', '.join([topic for topic, _ in weak_topics])}")
        
        return {
            'overall_score': overall_score,
            'total_questions': profile.total_questions,
            'correct_answers': profile.correct_answers,
            'learning_pace': profile.learning_pace,
            'preferred_difficulty': profile.preferred_difficulty,
            'weak_topics': weak_topics,
            'topic_performance': topic_performance,
            'cognitive_levels': cognitive_levels,
            'recommendations': recommendations
        }
    
    def generate_adaptive_questions(self, user_id: str, topic: str, num_questions: int = 5) -> Dict:
        """Generate questions adapted to student's level"""
        recommended_difficulty = self.get_recommended_difficulty(user_id, topic)
        
        # Adjust difficulty based on recent performance
        if user_id in self.students:
            profile = self.students[user_id]
            
            # Check recent performance (last 10 questions)
            recent_attempts = [a for a in getattr(profile, 'recent_attempts', [])[-10:]]
            if recent_attempts:
                recent_score = sum(1 for a in recent_attempts if a.correct) / len(recent_attempts)
                
                # Adjust difficulty based on recent performance
                if recent_score > 0.8 and recommended_difficulty != "hard":
                    recommended_difficulty = "hard"
                elif recent_score < 0.4 and recommended_difficulty != "easy":
                    recommended_difficulty = "easy"
        
        return {
            'recommended_difficulty': recommended_difficulty,
            'num_questions': num_questions,
            'topic': topic,
            'adaptive_reasoning': f"Based on your performance in {topic}, we recommend {recommended_difficulty} level questions"
        }
    
    def get_student_history(self, user_id: str) -> Dict:
        """Get detailed student history and progress over time"""
        if user_id not in self.students:
            return {
                'total_questions': 0,
                'correct_answers': 0,
                'overall_score': 0.0,
                'topics_attempted': [],
                'difficulty_progression': {},
                'learning_pace_history': [],
                'recent_activity': []
            }
        
        profile = self.students[user_id]
        
        # Calculate topic progression
        topics_attempted = list(profile.topic_performance.keys())
        
        # Calculate difficulty progression
        difficulty_progression = {}
        for topic, stats in profile.topic_performance.items():
            difficulty_progression[topic] = {}
            for difficulty, difficulty_stats in stats.items():
                if difficulty_stats['total'] > 0:
                    difficulty_progression[topic][difficulty] = {
                        'total': difficulty_stats['total'],
                        'correct': difficulty_stats['correct'],
                        'score': difficulty_stats['correct'] / difficulty_stats['total']
                    }
        
        # Get learning pace history
        learning_pace_history = []
        if hasattr(profile, 'recent_times') and profile.recent_times:
            # Calculate moving average of learning pace
            for i in range(len(profile.recent_times)):
                window = profile.recent_times[max(0, i-4):i+1]  # 5-point moving average
                avg_time = statistics.mean(window)
                pace = 60.0 / avg_time if avg_time > 0 else 0.0
                learning_pace_history.append({
                    'attempt': i + 1,
                    'pace': round(pace, 2),
                    'time_taken': round(avg_time, 2)
                })
        
        # Generate recent activity summary
        recent_activity = []
        if hasattr(profile, 'recent_times') and profile.recent_times:
            recent_activity.append({
                'type': 'quiz_completion',
                'description': f'Completed {len(profile.recent_times)} questions',
                'time': profile.last_activity.strftime('%Y-%m-%d %H:%M'),
                'score': f"{profile.correct_answers}/{profile.total_questions} correct"
            })
        
        return {
            'total_questions': profile.total_questions,
            'correct_answers': profile.correct_answers,
            'overall_score': profile.correct_answers / profile.total_questions if profile.total_questions > 0 else 0.0,
            'topics_attempted': topics_attempted,
            'difficulty_progression': difficulty_progression,
            'learning_pace_history': learning_pace_history,
            'recent_activity': recent_activity,
            'last_activity': profile.last_activity.isoformat() if profile.last_activity else None
        }

# Global instance - use absolute path to project root
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_file_path = os.path.join(project_root, "adaptive_learning.json")
adaptive_learning = AdaptiveLearningSystem(db_file_path) 