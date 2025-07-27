#!/usr/bin/env python3
"""
Teacher Mode System
Allows teachers to manage classes, upload materials, and generate question papers
"""

import json
import os
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import random

@dataclass
class Class:
    """Represents a class managed by a teacher"""
    class_id: str
    teacher_id: str
    name: str
    subject: str
    grade: str
    students: List[str]  # List of student user IDs
    materials: List[str]  # List of uploaded PDF filenames
    created_date: datetime
    last_activity: datetime

@dataclass
class QuestionPaper:
    """Represents a generated question paper"""
    paper_id: str
    class_id: str
    title: str
    subject: str
    total_marks: int
    duration_minutes: int
    questions: List[Dict]
    difficulty_distribution: Dict[str, int]  # easy: count, medium: count, hard: count
    created_date: datetime
    instructions: str

@dataclass
class StudentAssignment:
    """Represents an assignment given to students"""
    assignment_id: str
    class_id: str
    title: str
    description: str
    due_date: datetime
    question_paper_id: str
    assigned_students: List[str]
    status: str  # 'active', 'completed', 'expired'

class TeacherMode:
    def __init__(self, db_file: str = "teacher_mode.json"):
        self.db_file = db_file
        self.classes = {}
        self.question_papers = {}
        self.assignments = {}
        self._load_data()
    
    def _load_data(self):
        """Load teacher mode data from file"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.classes = data.get('classes', {})
                    self.question_papers = data.get('question_papers', {})
                    self.assignments = data.get('assignments', {})
                    
                    # Convert timestamps back to datetime objects
                    for class_data in self.classes.values():
                        if 'created_date' in class_data:
                            class_data['created_date'] = datetime.fromisoformat(class_data['created_date'])
                        if 'last_activity' in class_data:
                            class_data['last_activity'] = datetime.fromisoformat(class_data['last_activity'])
                    
                    for paper_data in self.question_papers.values():
                        if 'created_date' in paper_data:
                            paper_data['created_date'] = datetime.fromisoformat(paper_data['created_date'])
                    
                    for assignment_data in self.assignments.values():
                        if 'due_date' in assignment_data:
                            assignment_data['due_date'] = datetime.fromisoformat(assignment_data['due_date'])
            except Exception as e:
                print(f"Error loading teacher mode data: {e}")
    
    def _save_data(self):
        """Save teacher mode data to file"""
        try:
            data_to_save = {
                'classes': self.classes,
                'question_papers': self.question_papers,
                'assignments': self.assignments
            }
            
            # Convert datetime objects to strings for JSON serialization
            for class_data in data_to_save['classes'].values():
                if 'created_date' in class_data:
                    class_data['created_date'] = class_data['created_date'].isoformat()
                if 'last_activity' in class_data:
                    class_data['last_activity'] = class_data['last_activity'].isoformat()
            
            for paper_data in data_to_save['question_papers'].values():
                if 'created_date' in paper_data:
                    paper_data['created_date'] = paper_data['created_date'].isoformat()
            
            for assignment_data in data_to_save['assignments'].values():
                if 'due_date' in assignment_data:
                    assignment_data['due_date'] = assignment_data['due_date'].isoformat()
            
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving teacher mode data: {e}")
    
    def create_class(self, teacher_id: str, name: str, subject: str, grade: str) -> Dict:
        """Create a new class"""
        class_id = f"class_{uuid.uuid4().hex[:8]}"
        
        new_class = {
            'class_id': class_id,
            'teacher_id': teacher_id,
            'name': name,
            'subject': subject,
            'grade': grade,
            'students': [],
            'materials': [],
            'created_date': datetime.now(),
            'last_activity': datetime.now()
        }
        
        self.classes[class_id] = new_class
        self._save_data()
        
        return {
            'success': True,
            'class_id': class_id,
            'message': f'Class "{name}" created successfully'
        }
    
    def add_student_to_class(self, class_id: str, student_id: str) -> Dict:
        """Add a student to a class"""
        if class_id not in self.classes:
            return {'success': False, 'error': 'Class not found'}
        
        if student_id not in self.classes[class_id]['students']:
            self.classes[class_id]['students'].append(student_id)
            self.classes[class_id]['last_activity'] = datetime.now()
            self._save_data()
            
            return {
                'success': True,
                'message': f'Student added to class successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Student already in class'
            }
    
    def upload_material(self, class_id: str, pdf_filename: str) -> Dict:
        """Upload material to a class"""
        if class_id not in self.classes:
            return {'success': False, 'error': 'Class not found'}
        
        if pdf_filename not in self.classes[class_id]['materials']:
            self.classes[class_id]['materials'].append(pdf_filename)
            self.classes[class_id]['last_activity'] = datetime.now()
            self._save_data()
            
            return {
                'success': True,
                'message': f'Material "{pdf_filename}" uploaded successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Material already uploaded'
            }
    
    def generate_question_paper(self, class_id: str, title: str, total_marks: int, 
                               duration_minutes: int, difficulty_distribution: Dict[str, int],
                               instructions: str = "") -> Dict:
        """Generate a question paper for a class"""
        if class_id not in self.classes:
            return {'success': False, 'error': 'Class not found'}
        
        class_info = self.classes[class_id]
        
        # Import services
        from .llm_service import llm_service
        from .pdf_service import pdf_service
        
        # Get content from all materials
        all_content = ""
        for material in class_info['materials']:
            filepath = os.path.join('../uploads', material)
            if os.path.exists(filepath):
                result = pdf_service.extract_text_from_pdf(filepath)
                if result.get('success'):
                    all_content += result['text'] + "\n\n"
        
        if not all_content.strip():
            return {'success': False, 'error': 'No content available from uploaded materials'}
        
        # Generate questions based on difficulty distribution
        questions = []
        total_questions = sum(difficulty_distribution.values())
        
        for difficulty, count in difficulty_distribution.items():
            if count > 0:
                difficulty_questions = llm_service.generate_questions_from_text(
                    all_content, count, "mcq", difficulty
                )
                questions.extend(difficulty_questions)
        
        # Shuffle questions
        random.shuffle(questions)
        
        # Create question paper
        paper_id = f"paper_{uuid.uuid4().hex[:8]}"
        question_paper = {
            'paper_id': paper_id,
            'class_id': class_id,
            'title': title,
            'subject': class_info['subject'],
            'total_marks': total_marks,
            'duration_minutes': duration_minutes,
            'questions': questions,
            'difficulty_distribution': difficulty_distribution,
            'created_date': datetime.now(),
            'instructions': instructions or f"Answer all questions. Total marks: {total_marks}. Time: {duration_minutes} minutes."
        }
        
        self.question_papers[paper_id] = question_paper
        self._save_data()
        
        return {
            'success': True,
            'paper_id': paper_id,
            'message': f'Question paper "{title}" generated successfully',
            'question_paper': question_paper
        }
    
    def generate_question_paper_from_content(self, class_id: str, title: str, total_marks: int, 
                                           duration_minutes: int, difficulty_distribution: Dict[str, int],
                                           instructions: str = "", pdf_content: str = "", 
                                           pdf_filename: str = "") -> Dict:
        """Generate a question paper from provided content (for uploaded PDFs)"""
        if class_id not in self.classes:
            return {'success': False, 'error': 'Class not found'}
        
        class_info = self.classes[class_id]
        
        # Import services
        from .llm_service import llm_service
        
        if not pdf_content.strip():
            return {'success': False, 'error': 'No content provided for question generation'}
        
        # Generate questions based on difficulty distribution
        questions = []
        total_questions = sum(difficulty_distribution.values())
        
        for difficulty, count in difficulty_distribution.items():
            if count > 0:
                try:
                    difficulty_questions = llm_service.generate_questions_from_text(
                        pdf_content, count, "mcq", difficulty
                    )
                    questions.extend(difficulty_questions)
                except Exception as e:
                    print(f"Error generating {difficulty} questions: {e}")
                    # Continue with other difficulties
        
        if not questions:
            return {'success': False, 'error': 'Failed to generate questions from the provided content'}
        
        # Shuffle questions
        random.shuffle(questions)
        
        # Create question paper
        paper_id = f"paper_{uuid.uuid4().hex[:8]}"
        question_paper = {
            'paper_id': paper_id,
            'class_id': class_id,
            'title': title,
            'subject': class_info['subject'],
            'total_marks': total_marks,
            'duration_minutes': duration_minutes,
            'questions': questions,
            'difficulty_distribution': difficulty_distribution,
            'created_date': datetime.now(),
            'instructions': instructions or f"Answer all questions. Total marks: {total_marks}. Time: {duration_minutes} minutes.",
            'source_pdf': pdf_filename  # Track the source PDF
        }
        
        self.question_papers[paper_id] = question_paper
        self._save_data()
        
        # Add the uploaded PDF to class materials if it's not already there
        if pdf_filename and pdf_filename not in class_info['materials']:
            class_info['materials'].append(pdf_filename)
            self._save_data()
        
        return {
            'success': True,
            'paper_id': paper_id,
            'message': f'Question paper "{title}" generated successfully from uploaded material',
            'question_paper': question_paper
        }
    
    def create_assignment(self, class_id: str, title: str, description: str, 
                         due_date: datetime, question_paper_id: str) -> Dict:
        """Create an assignment for students"""
        if class_id not in self.classes:
            return {'success': False, 'error': 'Class not found'}
        
        if question_paper_id not in self.question_papers:
            return {'success': False, 'error': 'Question paper not found'}
        
        assignment_id = f"assignment_{uuid.uuid4().hex[:8]}"
        
        assignment = {
            'assignment_id': assignment_id,
            'class_id': class_id,
            'title': title,
            'description': description,
            'due_date': due_date,
            'question_paper_id': question_paper_id,
            'assigned_students': self.classes[class_id]['students'].copy(),
            'status': 'active'
        }
        
        self.assignments[assignment_id] = assignment
        self._save_data()
        
        return {
            'success': True,
            'assignment_id': assignment_id,
            'message': f'Assignment "{title}" created successfully'
        }
    
    def get_teacher_classes(self, teacher_id: str) -> List[Dict]:
        """Get all classes for a teacher"""
        teacher_classes = []
        for class_data in self.classes.values():
            if class_data['teacher_id'] == teacher_id:
                teacher_classes.append(class_data)
        return teacher_classes
    
    def get_class_details(self, class_id: str) -> Optional[Dict]:
        """Get detailed information about a class"""
        if class_id in self.classes:
            class_data = self.classes[class_id].copy()
            
            # Add assignment information
            class_assignments = []
            for assignment in self.assignments.values():
                if assignment['class_id'] == class_id:
                    class_assignments.append(assignment)
            
            class_data['assignments'] = class_assignments
            return class_data
        
        return None
    
    def export_question_paper(self, paper_id: str, format: str = "html") -> Dict:
        """Export question paper in different formats"""
        if paper_id not in self.question_papers:
            return {'success': False, 'error': 'Question paper not found'}
        
        paper = self.question_papers[paper_id]
        
        if format == "html":
            html_content = self._generate_html_paper(paper)
            return {
                'success': True,
                'format': 'html',
                'content': html_content,
                'filename': f"{paper['title'].replace(' ', '_')}.html"
            }
        elif format == "json":
            return {
                'success': True,
                'format': 'json',
                'content': paper,
                'filename': f"{paper['title'].replace(' ', '_')}.json"
            }
        else:
            return {'success': False, 'error': 'Unsupported format'}
    
    def _generate_html_paper(self, paper: Dict) -> str:
        """Generate HTML version of question paper"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{paper['title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }}
                .instructions {{ background-color: #f5f5f5; padding: 15px; margin-bottom: 30px; border-radius: 5px; }}
                .question {{ margin-bottom: 25px; }}
                .question-number {{ font-weight: bold; color: #333; }}
                .options {{ margin-left: 20px; }}
                .option {{ margin: 5px 0; }}
                .footer {{ margin-top: 50px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{paper['title']}</h1>
                <p><strong>Subject:</strong> {paper['subject']}</p>
                <p><strong>Total Marks:</strong> {paper['total_marks']} | <strong>Duration:</strong> {paper['duration_minutes']} minutes</p>
            </div>
            
            <div class="instructions">
                <h3>Instructions:</h3>
                <p>{paper['instructions']}</p>
            </div>
            
            <div class="questions">
        """
        
        for i, question in enumerate(paper['questions'], 1):
            html += f"""
                <div class="question">
                    <div class="question-number">Q{i}. {question['question']}</div>
                    <div class="options">
            """
            
            for j, option in enumerate(question['options']):
                html += f'<div class="option">{chr(65+j)}. {option}</div>'
            
            html += """
                    </div>
                </div>
            """
        
        html += """
            </div>
            
            <div class="footer">
                <p>Generated by AI Tutor for Rural India</p>
                <p>Date: """ + datetime.now().strftime("%B %d, %Y") + """</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def get_student_assignments(self, student_id: str) -> List[Dict]:
        """Get all assignments for a student"""
        student_assignments = []
        for assignment in self.assignments.values():
            if student_id in assignment['assigned_students']:
                student_assignments.append(assignment)
        return student_assignments

# Global instance
teacher_mode = TeacherMode("../teacher_mode.json") 