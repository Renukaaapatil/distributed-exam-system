"""
RPC Handlers for Distributed Exam System
Handles incoming RPC requests and executes remote function calls
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.models import User, Exam, Question, Response
from app.services import UserService, ExamService
from app import db

rpc_bp = Blueprint('rpc', __name__)

class RPCHandler:
    """Base RPC Handler class"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.logger = logging.getLogger(f"{__name__}.{node_id}")
        self.methods = {}
        self._register_methods()
    
    def _register_methods(self):
        """Register all available RPC methods"""
        self.methods = {
            'exam.get_data': self.get_exam_data,
            'exam.create': self.create_exam,
            'exam.start': self.start_exam,
            'exam.submit': self.submit_exam,
            'user.get_data': self.get_user_data,
            'user.create': self.create_user,
            'response.sync': self.sync_response,
            'node.status': self.get_node_status,
            'node.ping': self.ping,
            'node.handle_election': self.handle_election,
            'node.handle_ok': self.handle_ok,
            'node.handle_leader_announcement': self.handle_leader_announcement,
            'node.get_leader_info': self.get_leader_info,
            'node.get_fault_tolerance_status': self.get_fault_tolerance_status,
            'data.backup': self.backup_data,
            'data.restore': self.restore_data
        }
    
    def handle_request(self, request_data: dict) -> dict:
        """
        Handle incoming RPC request
        
        Args:
            request_data: RPC request data
            
        Returns:
            RPC response data
        """
        method = request_data.get('method')
        params = request_data.get('params', {})
        request_id = request_data.get('id')
        
        self.logger.info(f"RPC Request: {method} (ID: {request_id})")
        
        try:
            if method not in self.methods:
                raise ValueError(f"Unknown method: {method}")
            
            # Execute the method
            result = self.methods[method](params)
            
            self.logger.info(f"RPC Success: {method} (ID: {request_id})")
            
            return {
                'jsonrpc': '2.0',
                'result': result,
                'id': request_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"RPC Error: {method} (ID: {request_id}) - {str(e)}")
            
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': -32603,
                    'message': str(e),
                    'data': {
                        'method': method,
                        'params': params,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                },
                'id': request_id,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    # RPC Method Implementations
    
    def get_exam_data(self, params: dict) -> dict:
        """Get exam data"""
        exam_id = params.get('exam_id')
        
        if exam_id:
            exam, questions = ExamService.get_exam_with_questions(exam_id)
            if not exam:
                raise ValueError(f"Exam {exam_id} not found")
            
            return {
                'exam': {
                    'id': exam.id,
                    'title': exam.title,
                    'duration': exam.duration,
                    'created_at': exam.created_at.isoformat()
                },
                'questions': [
                    {
                        'id': q.id,
                        'text': q.text,
                        'options': q.get_options(),
                        'correct_answer': q.correct_answer
                    }
                    for q in questions
                ]
            }
        else:
            # Get all exams
            exams = ExamService.get_active_exams()
            return {
                'exams': [
                    {
                        'id': exam.id,
                        'title': exam.title,
                        'duration': exam.duration,
                        'question_count': len(exam.questions)
                    }
                    for exam in exams
                ]
            }
    
    def create_exam(self, params: dict) -> dict:
        """Create a new exam"""
        title = params.get('title')
        duration = params.get('duration')
        questions_data = params.get('questions', [])
        
        if not title or not duration:
            raise ValueError("Title and duration are required")
        
        exam = ExamService.create_exam(title, duration, questions_data)
        
        return {
            'exam_id': exam.id,
            'title': exam.title,
            'duration': exam.duration,
            'question_count': len(questions_data)
        }
    
    def start_exam(self, params: dict) -> dict:
        """Start an exam session"""
        user_id = params.get('user_id')
        exam_id = params.get('exam_id')
        
        if not user_id or not exam_id:
            raise ValueError("User ID and exam ID are required")
        
        session_data = ExamService.start_exam_session(user_id, exam_id)
        
        return {
            'session_id': f"{user_id}_{exam_id}",
            'exam_title': session_data['exam_title'],
            'duration': session_data['duration'],
            'question_count': len(session_data['questions']),
            'started_at': session_data['started_at'].isoformat()
        }
    
    def submit_exam(self, params: dict) -> dict:
        """Submit exam and calculate score"""
        user_id = params.get('user_id')
        exam_id = params.get('exam_id')
        answers = params.get('answers', {})
        
        if not user_id or not exam_id:
            raise ValueError("User ID and exam ID are required")
        
        # Save answers and submit
        for question_id, answer in answers.items():
            ExamService.save_exam_answer(user_id, exam_id, question_id, answer)
        
        result = ExamService.submit_exam(user_id, exam_id)
        
        return {
            'response_id': result['response_id'],
            'score': result['score'],
            'total_questions': result['total_questions'],
            'percentage': result['percentage']
        }
    
    def get_user_data(self, params: dict) -> dict:
        """Get user data"""
        user_id = params.get('user_id')
        email = params.get('email')
        
        if user_id:
            user = User.query.get(user_id)
        elif email:
            user = User.query.filter_by(email=email).first()
        else:
            raise ValueError("User ID or email is required")
        
        if not user:
            raise ValueError("User not found")
        
        stats = UserService.get_user_stats(user_id)
        
        return {
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role,
                'created_at': user.created_at.isoformat()
            },
            'stats': stats
        }
    
    def create_user(self, params: dict) -> dict:
        """Create a new user"""
        name = params.get('name')
        email = params.get('email')
        password = params.get('password')
        role = params.get('role', 'student')
        
        if not name or not email or not password:
            raise ValueError("Name, email, and password are required")
        
        user = UserService.create_user(name, email, password, role)
        
        return {
            'user_id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role
        }
    
    def sync_response(self, params: dict) -> dict:
        """Sync response data"""
        response_id = params.get('response_id')
        user_id = params.get('user_id')
        exam_id = params.get('exam_id')
        answers = params.get('answers', {})
        score = params.get('score')
        submitted_at = params.get('submitted_at')
        
        if not all([response_id, user_id, exam_id]):
            raise ValueError("Response ID, user ID, and exam ID are required")
        
        # Check if response exists
        existing_response = Response.query.filter_by(id=response_id).first()
        
        if existing_response:
            # Update existing response
            existing_response.answers = json.dumps(answers)
            existing_response.score = score
            if submitted_at:
                existing_response.submitted_at = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
        else:
            # Create new response
            response = Response(
                id=response_id,
                user_id=user_id,
                exam_id=exam_id,
                answers=json.dumps(answers),
                score=score,
                submitted_at=datetime.fromisoformat(submitted_at.replace('Z', '+00:00')) if submitted_at else datetime.utcnow()
            )
            db.session.add(response)
        
        db.session.commit()
        
        return {
            'response_id': response_id,
            'synced_at': datetime.utcnow().isoformat(),
            'action': 'updated' if existing_response else 'created'
        }
    
    def get_node_status(self, params: dict) -> dict:
        """Get node status"""
        return {
            'node_id': self.node_id,
            'status': 'active',
            'total_users': User.query.count(),
            'total_exams': Exam.query.count(),
            'total_responses': Response.query.count(),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def ping(self, params: dict) -> dict:
        """Ping node"""
        return {
            'pong': True,
            'node_id': self.node_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def backup_data(self, params: dict) -> dict:
        """Backup all data"""
        backup_data = {
            'users': [
                {
                    'id': u.id,
                    'name': u.name,
                    'email': u.email,
                    'role': u.role,
                    'created_at': u.created_at.isoformat()
                }
                for u in User.query.all()
            ],
            'exams': [
                {
                    'id': e.id,
                    'title': e.title,
                    'duration': e.duration,
                    'created_at': e.created_at.isoformat()
                }
                for e in Exam.query.all()
            ],
            'questions': [
                {
                    'id': q.id,
                    'exam_id': q.exam_id,
                    'text': q.text,
                    'options': q.get_options(),
                    'correct_answer': q.correct_answer
                }
                for q in Question.query.all()
            ],
            'responses': [
                {
                    'id': r.id,
                    'user_id': r.user_id,
                    'exam_id': r.exam_id,
                    'answers': r.get_answers(),
                    'score': r.score,
                    'started_at': r.started_at.isoformat(),
                    'submitted_at': r.submitted_at.isoformat()
                }
                for r in Response.query.all()
            ],
            'backup_timestamp': datetime.utcnow().isoformat()
        }
        
        return {
            'backup_size': len(json.dumps(backup_data)),
            'backup_timestamp': backup_data['backup_timestamp'],
            'counts': {
                'users': len(backup_data['users']),
                'exams': len(backup_data['exams']),
                'questions': len(backup_data['questions']),
                'responses': len(backup_data['responses'])
            }
        }
    
    def restore_data(self, params: dict) -> dict:
        """Restore data from backup"""
        backup_data = params.get('backup_data')
        
        if not backup_data:
            raise ValueError("Backup data is required")
        
        # This is a simplified restore - in production, you'd want more sophisticated logic
        restored_counts = {'users': 0, 'exams': 0, 'questions': 0, 'responses': 0}
        
        try:
            # Restore users
            for user_data in backup_data.get('users', []):
                if not User.query.filter_by(id=user_data['id']).first():
                    user = User(
                        id=user_data['id'],
                        name=user_data['name'],
                        email=user_data['email'],
                        role=user_data['role'],
                        created_at=datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00'))
                    )
                    db.session.add(user)
                    restored_counts['users'] += 1
            
            # Restore exams
            for exam_data in backup_data.get('exams', []):
                if not Exam.query.filter_by(id=exam_data['id']).first():
                    exam = Exam(
                        id=exam_data['id'],
                        title=exam_data['title'],
                        duration=exam_data['duration'],
                        created_at=datetime.fromisoformat(exam_data['created_at'].replace('Z', '+00:00'))
                    )
                    db.session.add(exam)
                    restored_counts['exams'] += 1
            
            db.session.commit()
            
            return {
                'restored': True,
                'counts': restored_counts,
                'restore_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Restore failed: {str(e)}")
    
    def handle_election(self, params: dict) -> dict:
        """Handle leader election message"""
        candidate_id = params.get('candidate_id')
        priority = params.get('priority')
        
        if not candidate_id:
            raise ValueError("Candidate ID is required")
        
        # Get fault tolerance manager from app context
        from flask import current_app
        if hasattr(current_app, 'fault_tolerance_manager'):
            current_app.fault_tolerance_manager.leader_election.handle_election_message(candidate_id)
        
        return {
            'message': 'Election message received',
            'candidate_id': candidate_id,
            'handled_by': self.node_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def handle_ok(self, params: dict) -> dict:
        """Handle OK message during election"""
        from_node_id = params.get('from_node_id')
        
        if not from_node_id:
            raise ValueError("From node ID is required")
        
        # Get fault tolerance manager from app context
        from flask import current_app
        if hasattr(current_app, 'fault_tolerance_manager'):
            current_app.fault_tolerance_manager.leader_election.handle_ok_message(from_node_id)
        
        return {
            'message': 'OK message received',
            'from_node_id': from_node_id,
            'handled_by': self.node_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def handle_leader_announcement(self, params: dict) -> dict:
        """Handle leader announcement"""
        leader_id = params.get('leader_id')
        priority = params.get('priority')
        
        if not leader_id:
            raise ValueError("Leader ID is required")
        
        # Get fault tolerance manager from app context
        from flask import current_app
        if hasattr(current_app, 'fault_tolerance_manager'):
            current_app.fault_tolerance_manager.leader_election.handle_leader_announcement(leader_id)
        
        return {
            'message': 'Leader announcement received',
            'leader_id': leader_id,
            'acknowledged_by': self.node_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_leader_info(self, params: dict = None) -> dict:
        """Get current leader information"""
        # Get fault tolerance manager from app context
        from flask import current_app
        if hasattr(current_app, 'fault_tolerance_manager'):
            return current_app.fault_tolerance_manager.leader_election.get_leader_info()
        else:
            return {
                'current_leader': None,
                'node_state': 'follower',
                'node_priority': 0,
                'election_in_progress': False
            }
    
    def get_fault_tolerance_status(self, params: dict = None) -> dict:
        """Get comprehensive fault tolerance status"""
        # Get fault tolerance manager from app context
        from flask import current_app
        if hasattr(current_app, 'fault_tolerance_manager'):
            return current_app.fault_tolerance_manager.get_fault_tolerance_status()
        else:
            return {
                'node_id': self.node_id,
                'status': 'fault_tolerance_not_initialized',
                'timestamp': datetime.utcnow().isoformat()
            }

# Global RPC handler instance
_rpc_handler = None

def init_rpc_handler(node_id: str):
    """Initialize RPC handler"""
    global _rpc_handler
    _rpc_handler = RPCHandler(node_id)

@rpc_bp.route('/rpc/call', methods=['POST'])
def handle_rpc_call():
    """Handle incoming RPC call"""
    if not _rpc_handler:
        return jsonify({'error': 'RPC handler not initialized'}), 500
    
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'Invalid JSON request'}), 400
        
        response_data = _rpc_handler.handle_request(request_data)
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'jsonrpc': '2.0',
            'error': {
                'code': -32603,
                'message': f'Internal error: {str(e)}'
            },
            'id': request_data.get('id') if request_data else None,
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@rpc_bp.route('/rpc/methods', methods=['GET'])
def list_methods():
    """List available RPC methods"""
    if not _rpc_handler:
        return jsonify({'error': 'RPC handler not initialized'}), 500
    
    return jsonify({
        'methods': list(_rpc_handler.methods.keys()),
        'node_id': _rpc_handler.node_id,
        'timestamp': datetime.utcnow().isoformat()
    })
