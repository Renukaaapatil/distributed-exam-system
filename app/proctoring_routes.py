"""
Proctoring Routes for Distributed Exam System
Handles AI proctoring API endpoints
"""

import json
import logging
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.proctoring_services import proctoring_service
from app import db

proctoring_bp = Blueprint('proctoring', __name__, url_prefix='/api/proctoring')

@proctoring_bp.route('/session/start', methods=['POST'])
@login_required
def start_proctoring_session():
    """Start a new proctoring session"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        exam_id = data.get('exam_id')
        response_id = data.get('response_id')
        
        if not exam_id or not response_id:
            return jsonify({'error': 'exam_id and response_id are required'}), 400
        
        # Start session
        result = proctoring_service.start_proctoring_session(
            current_user.id, exam_id, response_id
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 201
        
    except Exception as e:
        current_app.logger.error(f"Failed to start proctoring session: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/update_trust_score', methods=['POST'])
@login_required
def update_trust_score():
    """Update trust score based on violation detection"""
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        violation_type = data.get('violation_type')
        exam_id = data.get('exam_id')
        details = data.get('details')
        
        if not violation_type or not exam_id:
            return jsonify({'error': 'violation_type and exam_id are required'}), 400
        
        # Handle voice detection violations with specific penalty
        score_reduction = 0
        if violation_type == 'voice_detected':
            score_reduction = 20  # Reduce trust score by 20 for talking
            current_app.logger.info(f"Voice detection violation for user {current_user.id} in exam {exam_id}")
        else:
            score_reduction = 10  # Default reduction for other violations
        
        # Update trust score
        result = proctoring_service.update_trust_score(
            current_user.id, exam_id, violation_type, score_reduction
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        # Add violation details if provided
        if details:
            try:
                violation_details = json.loads(details) if isinstance(details, str) else details
                result['violation_details'] = violation_details
            except json.JSONDecodeError:
                pass
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Failed to update trust score: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/get_trust_score', methods=['GET'])
def get_trust_score():
    """Get current trust score for user's active session"""
    try:
        exam_id = request.args.get('exam_id', type=int)
        if not exam_id:
            return jsonify({'error': 'exam_id is required'}), 400
        
        # Get trust score (using mock user ID for testing)
        user_id = 1  # Mock user ID for testing
        result = proctoring_service.get_trust_score(user_id, exam_id)
        
        if 'error' in result:
            return jsonify(result), 404
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Failed to get trust score: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/auto_submit', methods=['POST'])
def auto_submit_exam():
    """Auto-submit exam due to low trust score"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        exam_id = data.get('exam_id')
        if not exam_id:
            return jsonify({'error': 'exam_id is required'}), 400
        
        # Auto submit exam (using mock user ID for testing)
        user_id = 1  # Mock user ID for testing
        result = proctoring_service.auto_submit_exam(user_id, exam_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Failed to auto submit exam: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/session/stop', methods=['POST'])
@login_required
def stop_proctoring_session():
    """Stop a proctoring session"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        # Stop session
        result = proctoring_service.stop_proctoring_session(session_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Failed to stop proctoring session: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/session/status', methods=['GET'])
@login_required
def get_proctoring_status():
    """Get current proctoring status"""
    try:
        result = proctoring_service.get_proctoring_status(current_user.id)
        
        if 'error' in result:
            return jsonify(result), 404
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Failed to get proctoring status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/frame/process', methods=['POST'])
@login_required
def process_frame():
    """Process video frame for proctoring"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        frame_data = data.get('frame_data')
        if not frame_data:
            return jsonify({'error': 'frame_data is required'}), 400
        
        # Process frame
        result = proctoring_service.process_frame(current_user.id, frame_data)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Failed to process frame: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/tab/switch', methods=['POST'])
@login_required
def handle_tab_switch():
    """Handle tab switching event"""
    try:
        # Handle tab switch
        result = proctoring_service.handle_tab_switch(current_user.id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Failed to handle tab switch: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/activity/suspicious', methods=['POST'])
@login_required
def handle_suspicious_activity():
    """Handle suspicious activity event"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        activity_type = data.get('activity_type')
        if not activity_type:
            return jsonify({'error': 'activity_type is required'}), 400
        
        # Handle suspicious activity
        result = proctoring_service.handle_suspicious_activity(current_user.id, activity_type)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Failed to handle suspicious activity: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/violations', methods=['GET'])
@login_required
def get_violations():
    """Get violations for current user's session"""
    try:
        session_id = request.args.get('session_id', type=int)
        limit = request.args.get('limit', 50, type=int)
        
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        violations = proctoring_service.get_violations(session_id, limit)
        
        return jsonify({
            'violations': violations,
            'count': len(violations)
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get violations: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Admin-only endpoints

@proctoring_bp.route('/admin/alerts', methods=['GET'])
@login_required
def get_admin_alerts():
    """Get proctoring alerts (admin only)"""
    try:
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        user_id = request.args.get('user_id', type=int)
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)
        
        alerts = proctoring_service.get_alerts(user_id, status, limit)
        
        return jsonify({
            'alerts': alerts,
            'count': len(alerts)
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get admin alerts: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/admin/alerts/<int:alert_id>/read', methods=['POST'])
@login_required
def mark_alert_read(alert_id):
    """Mark alert as read (admin only)"""
    try:
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        success = proctoring_service.mark_alert_read(alert_id)
        
        if success:
            return jsonify({'message': 'Alert marked as read'})
        else:
            return jsonify({'error': 'Alert not found'}), 404
        
    except Exception as e:
        current_app.logger.error(f"Failed to mark alert as read: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/admin/alerts/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    """Resolve alert (admin only)"""
    try:
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        success = proctoring_service.resolve_alert(alert_id)
        
        if success:
            return jsonify({'message': 'Alert resolved'})
        else:
            return jsonify({'error': 'Alert not found'}), 404
        
    except Exception as e:
        current_app.logger.error(f"Failed to resolve alert: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/admin/summary', methods=['GET'])
@login_required
def get_proctoring_summary():
    """Get proctoring summary (admin only)"""
    try:
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        exam_id = request.args.get('exam_id', type=int)
        
        summary = proctoring_service.get_proctoring_summary(exam_id)
        
        if 'error' in summary:
            return jsonify(summary), 400
        
        return jsonify(summary)
        
    except Exception as e:
        current_app.logger.error(f"Failed to get proctoring summary: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/admin/sessions', methods=['GET'])
@login_required
def get_proctoring_sessions():
    """Get proctoring sessions (admin only)"""
    try:
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        from app.models import ProctoringSession, User, Exam
        
        query = db.session.query(
            ProctoringSession, User, Exam
        ).join(
            User, ProctoringSession.user_id == User.id
        ).join(
            Exam, ProctoringSession.exam_id == Exam.id
        )
        
        # Apply filters
        exam_id = request.args.get('exam_id', type=int)
        if exam_id:
            query = query.filter(ProctoringSession.exam_id == exam_id)
        
        status = request.args.get('status')
        if status:
            query = query.filter(ProctoringSession.status == status)
        
        # Order by most recent
        query = query.order_by(ProctoringSession.started_at.desc())
        
        # Limit results
        limit = request.args.get('limit', 100, type=int)
        sessions = query.limit(limit).all()
        
        results = []
        for session, user, exam in sessions:
            results.append({
                'id': session.id,
                'user_id': user.id,
                'user_name': user.name,
                'user_email': user.email,
                'exam_id': exam.id,
                'exam_title': exam.title,
                'trust_score': session.trust_score,
                'initial_score': session.initial_score,
                'final_score': session.final_score,
                'status': session.status,
                'started_at': session.started_at.isoformat(),
                'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                'last_updated': session.last_updated.isoformat(),
                'violations_count': len(session.violations),
                'alerts_count': len([a for a in session.alerts if a.status == 'unread']),
                'status_color': 'green' if session.trust_score >= 80 else 'yellow' if session.trust_score >= 60 else 'red'
            })
        
        return jsonify({
            'sessions': results,
            'count': len(results)
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get proctoring sessions: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@proctoring_bp.route('/admin/violations', methods=['GET'])
@login_required
def get_admin_violations():
    """Get all violations (admin only)"""
    try:
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        from app.models import ProctoringViolation, User, ProctoringSession
        
        query = db.session.query(
            ProctoringViolation, User, ProctoringSession
        ).join(
            User, ProctoringViolation.user_id == User.id
        ).join(
            ProctoringSession, ProctoringViolation.session_id == ProctoringSession.id
        )
        
        # Apply filters
        violation_type = request.args.get('violation_type')
        if violation_type:
            query = query.filter(ProctoringViolation.violation_type == violation_type)
        
        severity = request.args.get('severity')
        if severity:
            query = query.filter(ProctoringViolation.severity == severity)
        
        user_id = request.args.get('user_id', type=int)
        if user_id:
            query = query.filter(ProctoringViolation.user_id == user_id)
        
        # Order by most recent
        query = query.order_by(ProctoringViolation.detected_at.desc())
        
        # Limit results
        limit = request.args.get('limit', 100, type=int)
        violations = query.limit(limit).all()
        
        results = []
        for violation, user, session in violations:
            results.append({
                'id': violation.id,
                'session_id': session.id,
                'user_id': user.id,
                'user_name': user.name,
                'user_email': user.email,
                'exam_id': session.exam_id,
                'violation_type': violation.violation_type,
                'severity': violation.severity,
                'details': violation.details,
                'trust_score_before': violation.trust_score_before,
                'trust_score_after': violation.trust_score_after,
                'score_penalty': violation.score_penalty,
                'detected_at': violation.detected_at.isoformat(),
                'evidence': violation.get_evidence()
            })
        
        return jsonify({
            'violations': results,
            'count': len(results)
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to get admin violations: {e}")
        return jsonify({'error': 'Internal server error'}), 500
