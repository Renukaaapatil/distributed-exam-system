"""
Adaptive Exam Service for Dynamic Difficulty Adjustment
Handles adaptive logic for exam questions based on student performance
"""

import random
import logging
from typing import Dict, List, Optional, Tuple
from flask import session
from app.models import Question, Exam, Response
from app import db

logger = logging.getLogger(__name__)

class AdaptiveExamService:
    """Service for managing adaptive exam logic and difficulty adjustment"""
    
    DIFFICULTY_LEVELS = {
        1: 'Easy',
        2: 'Medium',
        3: 'Hard'
    }
    
    SCORE_WEIGHTS = {
        1: 1,  # Easy = 1 point
        2: 2,  # Medium = 2 points
        3: 3   # Hard = 3 points
    }
    
    def __init__(self):
        self.min_difficulty = 1
        self.max_difficulty = 3
        self.start_difficulty = 2  # Start at Medium level
    
    def initialize_adaptive_session(self, exam_id: int, user_id: int) -> Dict:
        """
        Initialize adaptive exam session
        
        Args:
            exam_id: ID of the exam
            user_id: ID of the user
            
        Returns:
            Initial session state
        """
        try:
            # Initialize session state
            session_state = {
                'exam_id': exam_id,
                'user_id': user_id,
                'current_difficulty': self.start_difficulty,
                'score': 0,
                'question_index': 0,
                'total_questions': 0,
                'correct_answers': 0,
                'difficulty_history': [self.start_difficulty],
                'answer_history': [],
                'start_time': None,
                'used_questions': []  # Track used questions to avoid repetition
            }
            
            # Store in Flask session
            session['adaptive_exam'] = session_state
            
            logger.info(f"Adaptive session initialized for user {user_id}, exam {exam_id}")
            return session_state
            
        except Exception as e:
            logger.error(f"Failed to initialize adaptive session: {e}")
            raise
    
    def get_session_state(self) -> Optional[Dict]:
        """Get current adaptive session state"""
        return session.get('adaptive_exam')
    
    def update_session_state(self, updates: Dict):
        """Update adaptive session state"""
        current_state = self.get_session_state()
        if current_state:
            current_state.update(updates)
            session['adaptive_exam'] = current_state
    
    def adjust_difficulty(self, current_difficulty: int, is_correct: bool) -> int:
        """
        Adjust difficulty based on answer correctness
        
        Args:
            current_difficulty: Current difficulty level (1-3)
            is_correct: Whether the answer was correct
            
        Returns:
            New difficulty level
        """
        try:
            new_difficulty = current_difficulty
            
            if is_correct:
                # Increase difficulty if correct (max = 3)
                new_difficulty = min(current_difficulty + 1, self.max_difficulty)
                logger.debug(f"Correct answer - Difficulty increased from {current_difficulty} to {new_difficulty}")
            else:
                # Decrease difficulty if wrong (min = 1)
                new_difficulty = max(current_difficulty - 1, self.min_difficulty)
                logger.debug(f"Wrong answer - Difficulty decreased from {current_difficulty} to {new_difficulty}")
            
            return new_difficulty
            
        except Exception as e:
            logger.error(f"Error adjusting difficulty: {e}")
            return current_difficulty
    
    def get_next_question(self, exam_id: int, difficulty: int, used_questions: List[int] = None) -> Optional[Question]:
        """
        Get next question based on difficulty level
        
        Args:
            exam_id: ID of the exam
            difficulty: Difficulty level (1-3)
            used_questions: List of already used question IDs
            
        Returns:
            Next question or None if no questions available
        """
        try:
            used_questions = used_questions or []
            
            # Query for questions with specific difficulty, excluding used ones
            query = Question.query.filter(
                Question.exam_id == exam_id,
                Question.difficulty == difficulty
            )
            
            if used_questions:
                query = query.filter(~Question.id.in_(used_questions))
            
            # Get random question
            available_questions = query.all()
            
            if not available_questions:
                logger.warning(f"No questions available for difficulty {difficulty}")
                return None
            
            # Select random question
            next_question = random.choice(available_questions)
            
            logger.debug(f"Selected question {next_question.id} with difficulty {difficulty}")
            return next_question
            
        except Exception as e:
            logger.error(f"Error getting next question: {e}")
            return None
    
    def calculate_adaptive_score(self, difficulty: int, is_correct: bool) -> int:
        """
        Calculate score based on difficulty and correctness
        
        Args:
            difficulty: Difficulty level (1-3)
            is_correct: Whether the answer was correct
            
        Returns:
            Score points earned
        """
        if not is_correct:
            return 0
        
        return self.SCORE_WEIGHTS.get(difficulty, 2)
    
    def process_answer(self, question_id: int, selected_answer: str) -> Dict:
        """
        Process student answer and update adaptive state
        
        Args:
            question_id: ID of the question
            selected_answer: Selected answer ('A', 'B', 'C', 'D')
            
        Returns:
            Result dictionary with next question and updated state
        """
        try:
            session_state = self.get_session_state()
            if not session_state:
                raise ValueError("No active adaptive session")
            
            # Get question details
            question = Question.query.get(question_id)
            if not question:
                raise ValueError(f"Question {question_id} not found")
            
            # Check answer correctness
            is_correct = selected_answer == question.correct_answer
            
            # Calculate score
            points_earned = self.calculate_adaptive_score(question.difficulty, is_correct)
            
            # Update session state
            session_state['score'] += points_earned
            session_state['question_index'] += 1
            
            if is_correct:
                session_state['correct_answers'] += 1
            
            # Adjust difficulty based on performance
            current_difficulty = session_state['current_difficulty']
            new_difficulty = self.adjust_difficulty(current_difficulty, is_correct)
            session_state['current_difficulty'] = new_difficulty
            
            # Track history
            session_state['difficulty_history'].append(new_difficulty)
            session_state['answer_history'].append({
                'question_id': question_id,
                'selected_answer': selected_answer,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct,
                'difficulty': question.difficulty,
                'points_earned': points_earned,
                'timestamp': None  # Could add timestamp if needed
            })
            
            # Mark question as used
            session_state['used_questions'].append(question_id)
            
            # Get next question
            next_question = self.get_next_question(
                session_state['exam_id'],
                new_difficulty,
                session_state['used_questions']
            )
            
            # Update session
            self.update_session_state(session_state)
            
            # Prepare result
            result = {
                'success': True,
                'is_correct': is_correct,
                'points_earned': points_earned,
                'current_score': session_state['score'],
                'current_difficulty': new_difficulty,
                'difficulty_name': self.DIFFICULTY_LEVELS[new_difficulty],
                'question_index': session_state['question_index'],
                'correct_answers': session_state['correct_answers'],
                'has_next_question': next_question is not None,
                'next_question': None
            }
            
            # Include next question if available
            if next_question:
                result['next_question'] = {
                    'id': next_question.id,
                    'text': next_question.text,
                    'options': next_question.get_options(),
                    'difficulty': next_question.difficulty,
                    'difficulty_name': next_question.get_difficulty_name(),
                    'score_weight': next_question.get_score_weight()
                }
            
            logger.info(f"Answer processed - Correct: {is_correct}, New difficulty: {new_difficulty}, Score: {session_state['score']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing answer: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_first_question(self, exam_id: int) -> Dict:
        """
        Get first question for adaptive exam
        
        Args:
            exam_id: ID of the exam
            
        Returns:
            First question data
        """
        try:
            session_state = self.get_session_state()
            if not session_state:
                raise ValueError("No active adaptive session")
            
            # Get first question at starting difficulty
            first_question = self.get_next_question(
                exam_id,
                self.start_difficulty,
                session_state['used_questions']
            )
            
            if not first_question:
                raise ValueError("No questions available for this exam")
            
            # Update session with first question info
            session_state['total_questions'] = Question.query.filter_by(exam_id=exam_id).count()
            session_state['start_time'] = None  # Could set actual start time
            
            self.update_session_state(session_state)
            
            question_data = {
                'id': first_question.id,
                'text': first_question.text,
                'options': first_question.get_options(),
                'difficulty': first_question.difficulty,
                'difficulty_name': first_question.get_difficulty_name(),
                'score_weight': first_question.get_score_weight()
            }
            
            logger.info(f"First question loaded: {first_question.id} at difficulty {first_question.difficulty}")
            
            return {
                'success': True,
                'question': question_data,
                'current_difficulty': self.start_difficulty,
                'difficulty_name': self.DIFFICULTY_LEVELS[self.start_difficulty],
                'total_questions': session_state['total_questions']
            }
            
        except Exception as e:
            logger.error(f"Error getting first question: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_exam_summary(self) -> Dict:
        """
        Get summary of completed adaptive exam
        
        Returns:
            Exam summary with performance metrics
        """
        try:
            session_state = self.get_session_state()
            if not session_state:
                raise ValueError("No active adaptive session")
            
            # Calculate statistics
            total_questions = session_state['question_index']
            correct_answers = session_state['correct_answers']
            accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
            
            # Difficulty distribution
            difficulty_counts = {}
            for difficulty in session_state['difficulty_history']:
                difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
            
            # Performance by difficulty
            performance_by_difficulty = {}
            for answer in session_state['answer_history']:
                difficulty = answer['difficulty']
                if difficulty not in performance_by_difficulty:
                    performance_by_difficulty[difficulty] = {'correct': 0, 'total': 0}
                
                performance_by_difficulty[difficulty]['total'] += 1
                if answer['is_correct']:
                    performance_by_difficulty[difficulty]['correct'] += 1
            
            summary = {
                'success': True,
                'total_questions': total_questions,
                'correct_answers': correct_answers,
                'score': session_state['score'],
                'accuracy': round(accuracy, 2),
                'difficulty_history': session_state['difficulty_history'],
                'difficulty_counts': difficulty_counts,
                'performance_by_difficulty': performance_by_difficulty,
                'answer_history': session_state['answer_history']
            }
            
            logger.info(f"Exam summary generated - Score: {session_state['score']}, Accuracy: {accuracy:.2f}%")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating exam summary: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def end_adaptive_session(self) -> Dict:
        """
        End adaptive exam session and save results
        
        Returns:
            Final exam results
        """
        try:
            session_state = self.get_session_state()
            if not session_state:
                raise ValueError("No active adaptive session")
            
            # Get exam summary
            summary = self.get_exam_summary()
            
            if not summary.get('success'):
                raise ValueError("Failed to generate exam summary")
            
            # Save to database (if needed)
            # This could integrate with the existing Response model
            
            # Clear session
            session.pop('adaptive_exam', None)
            
            logger.info(f"Adaptive session ended for user {session_state['user_id']}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error ending adaptive session: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_difficulty_statistics(self, exam_id: int) -> Dict:
        """
        Get statistics about question difficulty distribution for an exam
        
        Args:
            exam_id: ID of the exam
            
        Returns:
            Difficulty distribution statistics
        """
        try:
            questions = Question.query.filter_by(exam_id=exam_id).all()
            
            if not questions:
                return {
                    'total_questions': 0,
                    'difficulty_distribution': {1: 0, 2: 0, 3: 0}
                }
            
            # Count questions by difficulty
            difficulty_counts = {1: 0, 2: 0, 3: 0}
            for question in questions:
                difficulty_counts[question.difficulty] = difficulty_counts.get(question.difficulty, 0) + 1
            
            return {
                'total_questions': len(questions),
                'difficulty_distribution': difficulty_counts,
                'difficulty_names': self.DIFFICULTY_LEVELS
            }
            
        except Exception as e:
            logger.error(f"Error getting difficulty statistics: {e}")
            return {
                'total_questions': 0,
                'difficulty_distribution': {1: 0, 2: 0, 3: 0},
                'error': str(e)
            }

# Global adaptive service instance
adaptive_service = AdaptiveExamService()
