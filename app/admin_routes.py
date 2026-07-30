"""
Admin Routes for Live Exam Monitoring Dashboard
Handles real-time monitoring of students, violations, and snapshots
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import User, Exam, ProctoringSession, ProctoringViolation, Snapshot, ExamSession

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Allowed file extensions for snapshots
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Main admin dashboard"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    return render_template('admin_dashboard.html')

@admin_bp.route('/live_sessions')
@login_required
def live_sessions():
    """Get all active exam sessions with trust scores and node assignments"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Get all active exam sessions
        active_sessions = ExamSession.query.filter_by(status='active').all()
        
        sessions_data = []
        for session in active_sessions:
            # Get user information
            user = User.query.get(session.user_id)
            if not user:
                continue
            
            # Get exam information
            exam = Exam.query.get(session.exam_id)
            if not exam:
                continue
            
            # Get proctoring session for trust score
            proctoring_session = ProctoringSession.query.filter_by(
                user_id=session.user_id,
                exam_id=session.exam_id,
                status='active'
            ).first()
            
            trust_score = proctoring_session.trust_score if proctoring_session else 100
            
            # Get recent violations count (last 10 minutes)
            recent_violations = ProctoringViolation.query.filter_by(
                session_id=proctoring_session.id if proctoring_session else None
            ).filter(
                ProctoringViolation.created_at >= datetime.utcnow() - timedelta(minutes=10)
            ).count() if proctoring_session else 0
            
            # Determine status color based on trust score
            if trust_score >= 80:
                status_color = 'success'
                status_text = 'Safe'
            elif trust_score >= 50:
                status_color = 'warning'
                status_text = 'Warning'
            else:
                status_color = 'danger'
                status_text = 'High Risk'
            
            session_data = {
                'session_id': session.id,
                'user_id': session.user_id,
                'user_name': user.name,
                'user_email': user.email,
                'exam_id': session.exam_id,
                'exam_title': exam.title,
                'node_id': session.node_id,
                'trust_score': trust_score,
                'status_color': status_color,
                'status_text': status_text,
                'recent_violations': recent_violations,
                'current_question': session.current_question_index + 1,
                'answers_count': len(session.get_answers()),
                'remaining_time': session.remaining_time,
                'last_activity': session.last_updated.isoformat() if session.last_updated else None,
                'session_duration': (datetime.utcnow() - session.created_at).total_seconds()
            }
            
            sessions_data.append(session_data)
        
        # Sort by trust score (lowest first) and then by recent violations
        sessions_data.sort(key=lambda x: (x['trust_score'], -x['recent_violations']))
        
        return jsonify({
            'success': True,
            'sessions': sessions_data,
            'total_active': len(sessions_data),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get live sessions: {e}")
        return jsonify({'error': 'Failed to get live sessions'}), 500

@admin_bp.route('/violations')
@login_required
def violations():
    """Get recent violations across all sessions"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Get time range (last 30 minutes by default)
        time_range = request.args.get('time_range', '30')
        try:
            time_range = int(time_range)
        except ValueError:
            time_range = 30
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_range)
        
        # Get recent violations
        recent_violations = ProctoringViolation.query.filter(
            ProctoringViolation.created_at >= cutoff_time
        ).order_by(ProctoringViolation.created_at.desc()).limit(50).all()
        
        violations_data = []
        for violation in recent_violations:
            # Get user information
            user = User.query.get(violation.user_id)
            if not user:
                continue
            
            # Get exam information
            exam = Exam.query.get(violation.exam_id)
            if not exam:
                continue
            
            violation_data = {
                'id': violation.id,
                'user_id': violation.user_id,
                'user_name': user.name,
                'exam_id': violation.exam_id,
                'exam_title': exam.title,
                'violation_type': violation.violation_type,
                'severity': violation.severity,
                'trust_score_before': violation.trust_score_before,
                'trust_score_after': violation.trust_score_after,
                'score_penalty': violation.score_penalty,
                'details': violation.details,
                'timestamp': violation.created_at.isoformat(),
                'time_ago': _time_ago(violation.created_at)
            }
            
            violations_data.append(violation_data)
        
        return jsonify({
            'success': True,
            'violations': violations_data,
            'total_violations': len(violations_data),
            'time_range': time_range,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get violations: {e}")
        return jsonify({'error': 'Failed to get violations'}), 500

@admin_bp.route('/snapshots/<session_id>')
@login_required
def snapshots(session_id):
    """Get latest webcam snapshots for a session"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Get limit parameter (default 10)
        limit = request.args.get('limit', 10)
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
        
        # Get recent snapshots for the session
        recent_snapshots = Snapshot.query.filter_by(session_id=session_id).order_by(
            Snapshot.created_at.desc()
        ).limit(limit).all()
        
        snapshots_data = []
        for snapshot in recent_snapshots:
            snapshot_data = {
                'id': snapshot.id,
                'session_id': snapshot.session_id,
                'image_url': snapshot.get_image_url(),
                'image_filename': snapshot.image_filename,
                'file_size': snapshot.file_size,
                'violation_detected': snapshot.violation_detected,
                'violation_type': snapshot.violation_type,
                'confidence_score': snapshot.confidence_score,
                'timestamp': snapshot.created_at.isoformat(),
                'time_ago': _time_ago(snapshot.created_at)
            }
            
            snapshots_data.append(snapshot_data)
        
        return jsonify({
            'success': True,
            'snapshots': snapshots_data,
            'total_snapshots': len(snapshots_data),
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get snapshots: {e}")
        return jsonify({'error': 'Failed to get snapshots'}), 500

@admin_bp.route('/upload_snapshot', methods=['POST'])
@login_required
def upload_snapshot():
    """Upload webcam snapshot from student side"""
    try:
        # Check if session_id is provided
        session_id = request.form.get('session_id')
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        # Check if file is provided
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Verify session exists
        session = ExamSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(current_app.instance_path, 'uploads', 'snapshots')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        filename = f"snapshot_{session_id}_{timestamp}.jpg"
        filename = secure_filename(filename)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Get violation data if provided
        violation_detected = request.form.get('violation_detected', 'false').lower() == 'true'
        violation_type = request.form.get('violation_type')
        confidence_score = request.form.get('confidence_score')
        
        if confidence_score:
            try:
                confidence_score = float(confidence_score)
            except ValueError:
                confidence_score = None
        
        # Create snapshot record
        snapshot = Snapshot(
            session_id=session_id,
            image_path=file_path,
            image_filename=filename,
            file_size=file_size,
            violation_detected=violation_detected,
            violation_type=violation_type,
            confidence_score=confidence_score
        )
        
        db.session.add(snapshot)
        db.session.commit()
        
        logger.info(f"Snapshot uploaded for session {session_id}: {filename}")
        
        return jsonify({
            'success': True,
            'snapshot_id': snapshot.id,
            'filename': filename,
            'file_size': file_size,
            'violation_detected': violation_detected,
            'timestamp': snapshot.created_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to upload snapshot: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to upload snapshot'}), 500

@admin_bp.route('/uploads/snapshots/<filename>')
@login_required
def serve_snapshot(filename):
    """Serve snapshot images"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        upload_dir = os.path.join(current_app.instance_path, 'uploads', 'snapshots')
        file_path = os.path.join(upload_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Snapshot not found'}), 404
        
        return send_file(file_path, mimetype='image/jpeg')
        
    except Exception as e:
        logger.error(f"Failed to serve snapshot: {e}")
        return jsonify({'error': 'Failed to serve snapshot'}), 500

@admin_bp.route('/statistics')
@login_required
def statistics():
    """Get overall monitoring statistics"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Get active sessions count
        active_sessions = ExamSession.query.filter_by(status='active').count()
        
        # Get total violations in last hour
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_violations = ProctoringViolation.query.filter(
            ProctoringViolation.created_at >= hour_ago
        ).count()
        
        # Get trust score distribution
        trust_scores = []
        active_proctoring_sessions = ProctoringSession.query.filter_by(status='active').all()
        
        for session in active_proctoring_sessions:
            trust_scores.append(session.trust_score)
        
        # Calculate distribution
        safe_count = len([s for s in trust_scores if s >= 80])
        warning_count = len([s for s in trust_scores if 50 <= s < 80])
        risk_count = len([s for s in trust_scores if s < 50])
        
        # Get node distribution
        node_distribution = {}
        for session in active_proctoring_sessions:
            exam_session = ExamSession.query.filter_by(
                user_id=session.user_id,
                exam_id=session.exam_id,
                status='active'
            ).first()
            
            if exam_session:
                node_id = exam_session.node_id
                node_distribution[node_id] = node_distribution.get(node_id, 0) + 1
        
        # Get top violations
        top_violations = db.session.query(
            ProctoringViolation.violation_type,
            db.func.count(ProctoringViolation.id).label('count')
        ).filter(
            ProctoringViolation.created_at >= hour_ago
        ).group_by(ProctoringViolation.violation_type).order_by(
            db.func.count(ProctoringViolation.id).desc()
        ).limit(5).all()
        
        statistics = {
            'active_sessions': active_sessions,
            'recent_violations': recent_violations,
            'trust_score_distribution': {
                'safe': safe_count,
                'warning': warning_count,
                'risk': risk_count
            },
            'node_distribution': node_distribution,
            'top_violations': [
                {'type': v[0], 'count': v[1]} for v in top_violations
            ],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'statistics': statistics
        })
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500

@admin_bp.route('/cleanup_snapshots', methods=['POST'])
@login_required
def cleanup_snapshots():
    """Clean up old snapshots to save disk space"""
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        # Get age limit (default 24 hours)
        hours = request.form.get('hours', 24)
        try:
            hours = int(hours)
        except ValueError:
            hours = 24
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get old snapshots
        old_snapshots = Snapshot.query.filter(
            Snapshot.created_at < cutoff_time
        ).all()
        
        deleted_count = 0
        total_size_freed = 0
        
        for snapshot in old_snapshots:
            try:
                # Delete file
                if os.path.exists(snapshot.image_path):
                    file_size = os.path.getsize(snapshot.image_path)
                    os.remove(snapshot.image_path)
                    total_size_freed += file_size
                
                # Delete database record
                db.session.delete(snapshot)
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Failed to delete snapshot {snapshot.id}: {e}")
        
        db.session.commit()
        
        logger.info(f"Cleaned up {deleted_count} old snapshots, freed {total_size_freed} bytes")
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'size_freed': total_size_freed,
            'hours': hours
        })
        
    except Exception as e:
        logger.error(f"Failed to cleanup snapshots: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to cleanup snapshots'}), 500

def _time_ago(timestamp):
    """Calculate time ago in human readable format"""
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        days = diff.days
        return f"{days} day{'s' if days > 1 else ''} ago"
