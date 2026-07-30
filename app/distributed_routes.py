"""
Distributed system routes for inter-node communication
"""

from flask import Blueprint, request, jsonify
from app.models import User, Exam, Question, Response
from app.services import ExamService
from app import db
from datetime import datetime
import json

distributed_bp = Blueprint('distributed', __name__)

@distributed_bp.route('/node/heartbeat', methods=['POST'])
def heartbeat():
    """Receive heartbeat from other nodes"""
    data = request.get_json()
    
    node_id = data.get('node_id')
    timestamp = data.get('timestamp')
    node_port = data.get('port')
    
    if not all([node_id, timestamp, node_port]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Store node information (simplified - in production, use proper node registry)
    from core.node_manager import NodeManager
    node_manager = NodeManager()
    node_manager.register_heartbeat(node_id, node_port, timestamp)
    
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})

@distributed_bp.route('/node/exam/start', methods=['POST'])
def broadcast_exam_start():
    """Broadcast exam start to all nodes"""
    data = request.get_json()
    
    exam_id = data.get('exam_id')
    user_id = data.get('user_id')
    node_id = data.get('node_id')
    
    if not all([exam_id, user_id, node_id]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Store exam start event
    from core.node_manager import NodeManager
    node_manager = NodeManager()
    node_manager.record_exam_start(exam_id, user_id, node_id)
    
    return jsonify({'status': 'ok', 'message': 'Exam start recorded'})

@distributed_bp.route('/node/response/sync', methods=['POST'])
def sync_response():
    """Sync student response across nodes"""
    data = request.get_json()
    
    response_id = data.get('response_id')
    user_id = data.get('user_id')
    exam_id = data.get('exam_id')
    answers = data.get('answers')
    score = data.get('score')
    node_id = data.get('node_id')
    
    if not all([response_id, user_id, exam_id, answers, score, node_id]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if response already exists
    existing_response = Response.query.filter_by(id=response_id).first()
    if existing_response:
        # Update existing response
        existing_response.answers = json.dumps(answers)
        existing_response.score = score
        existing_response.submitted_at = datetime.utcnow()
    else:
        # Create new response
        response = Response(
            id=response_id,
            user_id=user_id,
            exam_id=exam_id,
            answers=json.dumps(answers),
            score=score,
            submitted_at=datetime.utcnow()
        )
        db.session.add(response)
    
    db.session.commit()
    
    # Record sync event
    from core.node_manager import NodeManager
    node_manager = NodeManager()
    node_manager.record_response_sync(response_id, node_id)
    
    return jsonify({'status': 'ok', 'message': 'Response synchronized'})

@distributed_bp.route('/node/exams', methods=['GET'])
def get_exams():
    """Get all exams for synchronization"""
    exams = Exam.query.filter_by(is_active=True).all()
    
    exams_data = []
    for exam in exams:
        exam_data = {
            'id': exam.id,
            'title': exam.title,
            'duration': exam.duration,
            'created_at': exam.created_at.isoformat(),
            'questions': []
        }
        
        for question in exam.questions:
            question_data = {
                'id': question.id,
                'text': question.text,
                'option1': question.option1,
                'option2': question.option2,
                'option3': question.option3,
                'option4': question.option4,
                'correct_answer': question.correct_answer
            }
            exam_data['questions'].append(question_data)
        
        exams_data.append(exam_data)
    
    return jsonify({'exams': exams_data})

@distributed_bp.route('/node/responses', methods=['GET'])
def get_responses():
    """Get all responses for synchronization"""
    responses = Response.query.order_by(Response.submitted_at.desc()).limit(100).all()
    
    responses_data = []
    for response in responses:
        response_data = {
            'id': response.id,
            'user_id': response.user_id,
            'exam_id': response.exam_id,
            'answers': response.get_answers(),
            'score': response.score,
            'started_at': response.started_at.isoformat(),
            'submitted_at': response.submitted_at.isoformat()
        }
        responses_data.append(response_data)
    
    return jsonify({'responses': responses_data})

@distributed_bp.route('/node/status', methods=['GET'])
def node_status():
    """Get node status"""
    from core.node_manager import NodeManager
    node_manager = NodeManager()
    
    status = {
        'node_id': node_manager.node_id,
        'port': node_manager.port,
        'active_nodes': len(node_manager.get_active_nodes()),
        'total_exams': Exam.query.count(),
        'total_responses': Response.query.count(),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return jsonify(status)

@distributed_bp.route('/node/sync/full', methods=['POST'])
def full_sync():
    """Perform full synchronization with another node"""
    data = request.get_json()
    
    # Get all data from this node
    exams_data = []
    exams = Exam.query.all()
    for exam in exams:
        exam_dict = {
            'id': exam.id,
            'title': exam.title,
            'duration': exam.duration,
            'created_at': exam.created_at.isoformat(),
            'is_active': exam.is_active
        }
        exams_data.append(exam_dict)
    
    questions_data = []
    questions = Question.query.all()
    for question in questions:
        question_dict = {
            'id': question.id,
            'exam_id': question.exam_id,
            'text': question.text,
            'option1': question.option1,
            'option2': question.option2,
            'option3': question.option3,
            'option4': question.option4,
            'correct_answer': question.correct_answer,
            'created_at': question.created_at.isoformat()
        }
        questions_data.append(question_dict)
    
    responses_data = []
    responses = Response.query.all()
    for response in responses:
        response_dict = {
            'id': response.id,
            'user_id': response.user_id,
            'exam_id': response.exam_id,
            'answers': response.get_answers(),
            'score': response.score,
            'started_at': response.started_at.isoformat(),
            'submitted_at': response.submitted_at.isoformat()
        }
        responses_data.append(response_dict)
    
    return jsonify({
        'exams': exams_data,
        'questions': questions_data,
        'responses': responses_data,
        'timestamp': datetime.utcnow().isoformat()
    })
