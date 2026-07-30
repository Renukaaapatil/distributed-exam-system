#!/usr/bin/env python3
"""
Add sample questions to existing exam
"""

from app import create_app, db
from app.models import Exam, Question

def add_sample_questions():
    """Add sample questions to existing exam"""
    app = create_app('development')
    
    with app.app_context():
        # Get the first exam
        exam = Exam.query.first()
        if not exam:
            print("No exam found. Creating one...")
            exam = Exam(title='General Knowledge Test', duration=30)
            db.session.add(exam)
            db.session.commit()
            print(f"Created exam: {exam.title}")
        
        # Check if exam already has questions
        existing_questions = Question.query.filter_by(exam_id=exam.id).count()
        if existing_questions > 0:
            print(f"Exam already has {existing_questions} questions")
            return
        
        # Sample questions
        questions_data = [
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
                'option4': '6',
                'correct_answer': 'B'
            },
            {
                'text': 'What does HTML stand for?',
                'option1': 'Hyper Text Markup Language',
                'option2': 'High Tech Modern Language',
                'option3': 'Home Tool Markup Language',
                'option4': 'Hyperlinks and Text Markup Language',
                'correct_answer': 'A'
            },
            {
                'text': 'Which planet is known as the Red Planet?',
                'option1': 'Venus',
                'option2': 'Mars',
                'option3': 'Jupiter',
                'option4': 'Saturn',
                'correct_answer': 'B'
            }
        ]
        
        # Add questions to database
        for i, q_data in enumerate(questions_data):
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
        print(f"Added {len(questions_data)} questions to exam: {exam.title}")

if __name__ == '__main__':
    add_sample_questions()
