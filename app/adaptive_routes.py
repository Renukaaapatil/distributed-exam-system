"""
Adaptive Exam Routes for Dynamic Difficulty Adjustment
Handles adaptive exam flow with real-time difficulty adjustment
"""

import logging
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app.models import Question, Exam, Response
from app.adaptive_service import adaptive_service

logger = logging.getLogger(__name__)

adaptive_bp = Blueprint('adaptive', __name__, url_prefix='/adaptive')

@adaptive_bp.route('/start_exam/<int:exam_id>')
@login_required
def start_adaptive_exam(exam_id):
    """Start adaptive exam for a specific exam"""
    try:
        # Check if exam exists
        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        # Check if exam has questions
        questions = Question.query.filter_by(exam_id=exam_id).all()
        if not questions:
            return jsonify({'error': 'Exam has no questions'}), 400
        
        # Initialize adaptive session
        session_state = adaptive_service.initialize_adaptive_session(exam_id, current_user.id)
        
        # Get first question
        first_question_result = adaptive_service.get_first_question(exam_id)
        
        if not first_question_result.get('success'):
            return jsonify(first_question_result), 500
        
        # Render adaptive exam page
        return render_template('adaptive_exam.html', 
                             exam=exam,
                             first_question=first_question_result['question'],
                             current_difficulty=first_question_result['current_difficulty'],
                             difficulty_name=first_question_result['difficulty_name'],
                             total_questions=first_question_result['total_questions'])
        
    except Exception as e:
        logger.error(f"Error starting adaptive exam: {e}")
        return jsonify({'error': 'Failed to start adaptive exam'}), 500

@adaptive_bp.route('/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    """Submit answer and get next question with adaptive difficulty adjustment"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        question_id = data.get('question_id')
        selected_answer = data.get('selected_answer')
        
        if not question_id or not selected_answer:
            return jsonify({'error': 'question_id and selected_answer are required'}), 400
        
        # Validate selected answer format
        if selected_answer not in ['A', 'B', 'C', 'D']:
            return jsonify({'error': 'selected_answer must be A, B, C, or D'}), 400
        
        # Process answer and get next question
        result = adaptive_service.process_answer(question_id, selected_answer)
        
        if not result.get('success'):
            return jsonify(result), 500
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error submitting answer: {e}")
        return jsonify({'error': 'Failed to submit answer'}), 500

@adaptive_bp.route('/get_question')
@login_required
def get_question():
    """Get current question (for page refresh scenarios)"""
    try:
        session_state = adaptive_service.get_session_state()
        if not session_state:
            return jsonify({'error': 'No active adaptive session'}), 400
        
        # Get current question based on session state
        exam_id = session_state['exam_id']
        current_difficulty = session_state['current_difficulty']
        used_questions = session_state['used_questions']
        
        # Get next question
        next_question = adaptive_service.get_next_question(exam_id, current_difficulty, used_questions)
        
        if not next_question:
            return jsonify({'error': 'No more questions available'}), 404
        
        question_data = {
            'id': next_question.id,
            'text': next_question.text,
            'options': next_question.get_options(),
            'difficulty': next_question.difficulty,
            'difficulty_name': next_question.get_difficulty_name(),
            'score_weight': next_question.get_score_weight()
        }
        
        return jsonify({
            'success': True,
            'question': question_data,
            'current_difficulty': current_difficulty,
            'difficulty_name': adaptive_service.DIFFICULTY_LEVELS[current_difficulty],
            'question_index': session_state['question_index'],
            'score': session_state['score']
        })
        
    except Exception as e:
        logger.error(f"Error getting question: {e}")
        return jsonify({'error': 'Failed to get question'}), 500

@adaptive_bp.route('/session_state')
@login_required
def get_session_state():
    """Get current adaptive session state"""
    try:
        session_state = adaptive_service.get_session_state()
        if not session_state:
            return jsonify({'error': 'No active adaptive session'}), 400
        
        # Remove sensitive data if needed
        safe_session_state = {
            'exam_id': session_state['exam_id'],
            'current_difficulty': session_state['current_difficulty'],
            'difficulty_name': adaptive_service.DIFFICULTY_LEVELS[session_state['current_difficulty']],
            'score': session_state['score'],
            'question_index': session_state['question_index'],
            'correct_answers': session_state['correct_answers'],
            'total_questions': session_state['total_questions'],
            'difficulty_history': session_state['difficulty_history'][-10:],  # Last 10 entries
            'accuracy': (session_state['correct_answers'] / session_state['question_index'] * 100) if session_state['question_index'] > 0 else 0
        }
        
        return jsonify({
            'success': True,
            'session_state': safe_session_state
        })
        
    except Exception as e:
        logger.error(f"Error getting session state: {e}")
        return jsonify({'error': 'Failed to get session state'}), 500

@adaptive_bp.route('/end_exam', methods=['POST'])
@login_required
def end_adaptive_exam():
    """End adaptive exam and get final results"""
    try:
        # End session and get results
        results = adaptive_service.end_adaptive_session()
        
        if not results.get('success'):
            return jsonify(results), 500
        
        # Save results to database (optional - could integrate with existing Response model)
        # This is where you would save the adaptive exam results
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error ending adaptive exam: {e}")
        return jsonify({'error': 'Failed to end adaptive exam'}), 500

@adaptive_bp.route('/exam_stats/<int:exam_id>')
@login_required
def get_exam_stats(exam_id):
    """Get statistics about question difficulty distribution for an exam"""
    try:
        # Check if exam exists
        exam = Exam.query.get(exam_id)
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        # Get difficulty statistics
        stats = adaptive_service.get_difficulty_statistics(exam_id)
        
        return jsonify({
            'success': True,
            'exam': {
                'id': exam.id,
                'title': exam.title,
                'duration': exam.duration
            },
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting exam stats: {e}")
        return jsonify({'error': 'Failed to get exam stats'}), 500

@adaptive_bp.route('/reset_session', methods=['POST'])
@login_required
def reset_session():
    """Reset adaptive session (for testing purposes)"""
    try:
        # Clear current session
        if 'adaptive_exam' in session:
            session.pop('adaptive_exam', None)
        
        return jsonify({
            'success': True,
            'message': 'Adaptive session reset successfully'
        })
        
    except Exception as e:
        logger.error(f"Error resetting session: {e}")
        return jsonify({'error': 'Failed to reset session'}), 500

@adaptive_bp.route('/dashboard')
@login_required
def adaptive_dashboard():
    """Dashboard for adaptive exams"""
    try:
        # Get all available exams
        exams = Exam.query.all()
        
        # Get statistics for each exam
        exam_stats = []
        for exam in exams:
            stats = adaptive_service.get_difficulty_statistics(exam.id)
            exam_stats.append({
                'exam': exam,
                'stats': stats
            })
        
        return render_template('adaptive_dashboard.html', 
                             exams=exams,
                             exam_stats=exam_stats)
        
    except Exception as e:
        logger.error(f"Error loading adaptive dashboard: {e}")
        return jsonify({'error': 'Failed to load dashboard'}), 500
