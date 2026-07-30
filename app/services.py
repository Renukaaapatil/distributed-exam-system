"""
Services layer for exam system - separates business logic from routes
"""

import random
import json
from datetime import datetime, timedelta
from flask import current_app
from app.models import User, Exam, Question, Response, exam_sessions
from app import db

class UserService:
    """User-related business logic"""
    
    @staticmethod
    def create_user(name, email, password, role='student'):
        """Create a new user"""
        if User.query.filter_by(email=email).first():
            raise ValueError("Email already exists")
        
        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def authenticate_user(email, password):
        """Authenticate user credentials"""
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            return user
        return None
    
    @staticmethod
    def get_user_stats(user_id):
        """Get user statistics"""
        user = User.query.get(user_id)
        if not user:
            return None
        
        responses = Response.query.filter_by(user_id=user_id).all()
        total_exams = len(responses)
        
        if total_exams == 0:
            return {
                'total_exams': 0,
                'average_score': 0,
                'best_score': 0,
                'recent_attempts': []
            }
        
        scores = [r.score for r in responses]
        average_score = sum(scores) / total_exams
        best_score = max(scores)
        
        recent_attempts = Response.query.filter_by(user_id=user_id)\
            .order_by(Response.submitted_at.desc())\
            .limit(10).all()
        
        return {
            'total_exams': total_exams,
            'average_score': round(average_score, 1),
            'best_score': best_score,
            'recent_attempts': recent_attempts
        }

class ExamService:
    """Exam-related business logic"""
    
    @staticmethod
    def create_exam(title, duration, questions_data):
        """Create a new exam with questions"""
        exam = Exam(title=title, duration=duration)
        db.session.add(exam)
        db.session.flush()  # Get the exam ID
        
        for q_data in questions_data:
            question = Question(
                exam_id=exam.id,
                text=q_data['text'],
                option1=q_data['option1'],
                option2=q_data['option2'],
                option3=q_data['option3'],
                option4=q_data['option4'],
                correct_answer=q_data['correct_answer']
            )
            db.session.add(question)
        
        db.session.commit()
        return exam
    
    @staticmethod
    def get_active_exams():
        """Get all active exams"""
        return Exam.query.filter_by(is_active=True).all()
    
    @staticmethod
    def get_exam_with_questions(exam_id):
        """Get exam with its questions"""
        exam = Exam.query.get(exam_id)
        if not exam:
            return None
        
        questions = Question.query.filter_by(exam_id=exam_id).all()
        return exam, questions
    
    @staticmethod
    def get_randomized_questions(exam_id):
        """Get questions in random order"""
        exam, questions = ExamService.get_exam_with_questions(exam_id)
        if not exam:
            return None, None
        
        # Handle case with no questions
        if not questions:
            return exam, []
        
        # Randomize question order
        random.shuffle(questions)
        return exam, questions
    
    @staticmethod
    def start_exam_session(user_id, exam_id):
        """Start an exam session"""
        exam, questions = ExamService.get_randomized_questions(exam_id)
        if not exam:
            raise ValueError("Exam not found")
        
        # Check if user already has an active session
        session_key = f"{user_id}_{exam_id}"
        if session_key in exam_sessions:
            return exam_sessions[session_key]
        
        # Create new session
        session_data = {
            'user_id': user_id,
            'exam_id': exam_id,
            'exam_title': exam.title,
            'duration': exam.duration,
            'questions': questions,
            'started_at': datetime.utcnow(),
            'answers': {},
            'is_active': True
        }
        
        exam_sessions[session_key] = session_data
        return session_data
    
    @staticmethod
    def save_exam_answer(user_id, exam_id, question_id, answer):
        """Save answer during exam"""
        session_key = f"{user_id}_{exam_id}"
        if session_key not in exam_sessions:
            raise ValueError("No active exam session")
        
        session = exam_sessions[session_key]
        if not session['is_active']:
            raise ValueError("Exam session is not active")
        
        # Check if time is up
        elapsed = datetime.utcnow() - session['started_at']
        if elapsed.total_seconds() > session['duration'] * 60:
            session['is_active'] = False
            raise ValueError("Time is up")
        
        session['answers'][str(question_id)] = answer
        return session
    
    @staticmethod
    def submit_exam(user_id, exam_id):
        """Submit exam and calculate score"""
        session_key = f"{user_id}_{exam_id}"
        if session_key not in exam_sessions:
            raise ValueError("No active exam session")
        
        session = exam_sessions[session_key]
        
        # Calculate score
        score = 0
        total_questions = len(session['questions'])
        
        for question in session['questions']:
            question_id = str(question.id)
            user_answer = session['answers'].get(question_id)
            
            if user_answer == question.correct_answer:
                score += 1
        
        # Save to database
        response = Response(
            user_id=user_id,
            exam_id=exam_id,
            answers=json.dumps(session['answers']),
            score=score,
            started_at=session['started_at'],
            submitted_at=datetime.utcnow()
        )
        
        db.session.add(response)
        db.session.commit()
        
        # Remove from active sessions
        del exam_sessions[session_key]
        
        return {
            'score': score,
            'total_questions': total_questions,
            'percentage': round((score / total_questions) * 100, 1),
            'response_id': response.id
        }
    
    @staticmethod
    def get_exam_results(response_id):
        """Get detailed exam results"""
        response = Response.query.get(response_id)
        if not response:
            return None
        
        exam, questions = ExamService.get_exam_with_questions(response.exam_id)
        if not exam:
            return None
        
        user_answers = response.get_answers()
        results = []
        
        for question in questions:
            question_id = str(question.id)
            user_answer = user_answers.get(question_id)
            is_correct = user_answer == question.correct_answer
            
            results.append({
                'question': question,
                'user_answer': user_answer,
                'is_correct': is_correct
            })
        
        return {
            'response': response,
            'exam': exam,
            'results': results,
            'percentage': round((response.score / len(questions)) * 100, 1)
        }
    
    @staticmethod
    def get_all_responses():
        """Get all exam responses (for admin dashboard)"""
        return Response.query.order_by(Response.submitted_at.desc()).all()
    
    @staticmethod
    def initialize_default_exam():
        """Initialize default exam with sample questions"""
        if Exam.query.count() > 0:
            return
        
        exam_data = {
            'title': 'General Knowledge Test',
            'duration': 30,
            'questions': [
                {
                    'text': 'What is the capital of France?',
                    'option1': 'London',
                    'option2': 'Berlin',
                    'option3': 'Paris',
                    'option4': 'Madrid',
                    'correct_answer': 'C'
                },
                {
                    'text': 'Which programming language is known as the "language of the web"?',
                    'option1': 'Python',
                    'option2': 'JavaScript',
                    'option3': 'Java',
                    'option4': 'C++',
                    'correct_answer': 'B'
                },
                {
                    'text': 'What is 2 + 2?',
                    'option1': '3',
                    'option2': '4',
                    'option3': '5',
                    'option4': '22',
                    'correct_answer': 'B'
                },
                {
                    'text': 'Which database is most commonly used with Flask?',
                    'option1': 'MySQL',
                    'option2': 'PostgreSQL',
                    'option3': 'SQLite',
                    'option4': 'MongoDB',
                    'correct_answer': 'C'
                },
                {
                    'text': 'What does HTML stand for?',
                    'option1': 'Hyper Text Markup Language',
                    'option2': 'High Tech Modern Language',
                    'option3': 'Home Tool Markup Language',
                    'option4': 'Hyperlinks and Text Markup Language',
                    'correct_answer': 'A'
                }
            ]
        }
        
        ExamService.create_exam(
            title=exam_data['title'],
            duration=exam_data['duration'],
            questions_data=exam_data['questions']
        )
    
    @staticmethod
    def initialize_admin_user():
        """Initialize default admin user"""
        if User.query.filter_by(role='admin').first() is None:
            admin = UserService.create_user(
                name='Administrator',
                email='admin@example.com',
                password='admin123',
                role='admin'
            )
            return admin
        return None

class AntiCheatService:
    """Anti-cheating and security services"""
    
    @staticmethod
    def generate_exam_token(user_id, exam_id):
        """Generate a unique token for exam session"""
        import hashlib
        import time
        
        token_data = f"{user_id}_{exam_id}_{int(time.time())}"
        return hashlib.sha256(token_data.encode()).hexdigest()
    
    @staticmethod
    def validate_exam_session(user_id, exam_id, token):
        """Validate exam session token"""
        session_key = f"{user_id}_{exam_id}"
        if session_key not in exam_sessions:
            return False
        
        session = exam_sessions[session_key]
        return session.get('token') == token
    
    @staticmethod
    def detect_suspicious_activity(user_id, exam_id, activity_type):
        """Log suspicious activity"""
        # This could be extended to log to database or file
        current_app.logger.warning(
            f"Suspicious activity detected: User {user_id}, Exam {exam_id}, Type: {activity_type}"
        )
