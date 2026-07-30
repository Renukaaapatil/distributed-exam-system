#!/usr/bin/env python3
"""
Add dummy data for testing the admin dashboard
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Exam, Question, Response, ProctoringSession, ProctoringViolation
from datetime import datetime, timedelta
import random

def add_dummy_data():
    """Add dummy data for testing"""
    app = create_app()
    
    with app.app_context():
        print("Adding dummy data for testing...")
        
        # Get or create admin user
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(
                email='admin@example.com',
                name='Admin User',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Get or create test students
        students = []
        student_emails = ['student1@example.com', 'student2@example.com', 'student3@example.com']
        student_names = ['John Doe', 'Jane Smith', 'Bob Johnson']
        
        for i, (email, name) in enumerate(zip(student_emails, student_names)):
            student = User.query.filter_by(email=email).first()
            if not student:
                student = User(
                    email=email,
                    name=name,
                    role='student'
                )
                student.set_password('password123')
                db.session.add(student)
            students.append(student)
        
        # Create test exam
        exam = Exam.query.filter_by(title='Test Exam for Dashboard').first()
        if not exam:
            exam = Exam(
                title='Test Exam for Dashboard',
                duration=60
            )
            db.session.add(exam)
        
        # Create test questions
        questions = []
        for i in range(5):
            question = Question.query.filter_by(text=f'Test Question {i+1}').first()
            if not question:
                question = Question(
                    exam_id=exam.id,
                    text=f'Test Question {i+1}',
                    option1='Option A',
                    option2='Option B',
                    option3='Option C',
                    option4='Option D',
                    correct_answer='A'
                )
                db.session.add(question)
            questions.append(question)
        
        db.session.commit()
        
        # Create active proctoring sessions (2 active sessions)
        active_sessions_data = [
            {'user': students[0], 'trust_score': 90, 'started_at': datetime.utcnow() - timedelta(minutes=30)},
            {'user': students[1], 'trust_score': 60, 'started_at': datetime.utcnow() - timedelta(minutes=45)}
        ]
        
        for session_data in active_sessions_data:
            existing_session = ProctoringSession.query.filter_by(
                user_id=session_data['user'].id,
                exam_id=exam.id,
                status='active'
            ).first()
            
            if not existing_session:
                session = ProctoringSession(
                    user_id=session_data['user'].id,
                    exam_id=exam.id,
                    status='active',
                    trust_score=session_data['trust_score'],
                    started_at=session_data['started_at']
                )
                db.session.add(session)
        
        # Create violation (1 violation)
        # First get the session to link the violation to
        session = ProctoringSession.query.filter_by(user_id=students[0].id, status='active').first()
        if session:
            violation = ProctoringViolation.query.filter_by(user_id=students[0].id).first()
            if not violation:
                violation = ProctoringViolation(
                    session_id=session.id,
                    user_id=students[0].id,
                    violation_type='face_not_visible',
                    severity='medium',
                    details='Student face was not visible for 5 seconds'
                )
            db.session.add(violation)
        
        # Create additional sessions with different trust scores (90, 60, 30)
        trust_score_sessions = [
            {'user': students[0], 'trust_score': 90, 'status': 'completed'},
            {'user': students[1], 'trust_score': 60, 'status': 'completed'},
            {'user': students[2], 'trust_score': 30, 'status': 'completed'}
        ]
        
        for session_data in trust_score_sessions:
            existing_session = ProctoringSession.query.filter_by(
                user_id=session_data['user'].id,
                trust_score=session_data['trust_score']
            ).first()
            
            if not existing_session:
                session = ProctoringSession(
                    user_id=session_data['user'].id,
                    exam_id=exam.id,
                    status=session_data['status'],
                    trust_score=session_data['trust_score'],
                    started_at=datetime.utcnow() - timedelta(hours=2),
                    ended_at=datetime.utcnow() - timedelta(hours=1)
                )
                db.session.add(session)
        
        db.session.commit()
        
        print("Dummy data added successfully!")
        print("\nSummary:")
        print(f"- Admin user: {admin.email}")
        print(f"- Students: {[s.email for s in students]}")
        print(f"- Exam: {exam.title}")
        print(f"- Questions: {len(questions)}")
        print(f"- Active sessions: {len(active_sessions_data)}")
        print(f"- Violations: 1")
        print(f"- Trust scores: 90, 60, 30")
        
        # Print current dashboard stats
        active_count = ProctoringSession.query.filter_by(status='active').count()
        violations_count = ProctoringViolation.query.count()
        high_risk_count = ProctoringSession.query.filter(
            ProctoringSession.trust_score < 40,
            ProctoringSession.trust_score.isnot(None)
        ).count()
        
        print(f"\nCurrent Dashboard Stats:")
        print(f"- Active Sessions: {active_count}")
        print(f"- Total Violations: {violations_count}")
        print(f"- High Risk Students: {high_risk_count}")

if __name__ == '__main__':
    add_dummy_data()
