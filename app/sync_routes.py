"""
Sync Routes for Offline Mode + Sync System
Handles synchronization of offline exam data with server
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import User, Exam, Response, SyncLog
from app import db

logger = logging.getLogger(__name__)

sync_bp = Blueprint('sync', __name__, url_prefix='')

@sync_bp.route('/sync_exam', methods=['POST'])
@login_required
def sync_exam_data():
    """
    Sync offline exam data to server
    Handles exam answers, metadata, and progress synchronization
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        sync_type = data.get('type')
        sync_data = data.get('data')
        timestamp = data.get('timestamp')
        
        if not sync_type or not sync_data:
            return jsonify({'error': 'Missing required fields: type and data'}), 400
        
        # Log sync attempt
        sync_log = SyncLog(
            user_id=current_user.id,
            sync_type=sync_type,
            data_received=str(sync_data)[:1000],  # Limit stored data size
            client_timestamp=timestamp,
            server_timestamp=datetime.utcnow()
        )
        
        if sync_type == 'exam_answers':
            result = sync_exam_answers(sync_data, sync_log)
        elif sync_type == 'exam_metadata':
            result = sync_exam_metadata(sync_data, sync_log)
        elif sync_type == 'exam_progress':
            result = sync_exam_progress(sync_data, sync_log)
        else:
            sync_log.status = 'error'
            sync_log.error_message = f'Unknown sync type: {sync_type}'
            db.session.add(sync_log)
            db.session.commit()
            
            return jsonify({'error': f'Unknown sync type: {sync_type}'}), 400
        
        # Save sync log
        db.session.add(sync_log)
        db.session.commit()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error during exam sync: {e}")
        return jsonify({'error': 'Internal server error during sync'}), 500

def sync_exam_answers(data, sync_log):
    """Sync exam answers to server"""
    try:
        exam_id = data.get('examId')
        answers = data.get('answers', {})
        
        if not exam_id or not answers:
            sync_log.status = 'error'
            sync_log.error_message = 'Missing examId or answers'
            return {'success': False, 'error': 'Missing examId or answers'}
        
        # Validate exam exists
        exam = Exam.query.get(exam_id)
        if not exam:
            sync_log.status = 'error'
            sync_log.error_message = f'Exam {exam_id} not found'
            return {'success': False, 'error': 'Exam not found'}
        
        # Check if user has an existing response for this exam
        existing_response = Response.query.filter_by(
            user_id=current_user.id,
            exam_id=exam_id
        ).first()
        
        if existing_response:
            # Update existing response with new answers
            existing_response.answers = str(answers)  # Store as string
            existing_response.updated_at = datetime.utcnow()
            
            # Recalculate score
            score = calculate_exam_score(exam, answers)
            existing_response.score = score
            
            logger.info(f"Updated existing response for user {current_user.id}, exam {exam_id}")
        else:
            # Create new response
            score = calculate_exam_score(exam, answers)
            
            new_response = Response(
                user_id=current_user.id,
                exam_id=exam_id,
                answers=str(answers),
                score=score,
                started_at=datetime.utcnow(),
                submitted_at=datetime.utcnow() if score > 0 else datetime.utcnow()
            )
            
            db.session.add(new_response)
            logger.info(f"Created new response for user {current_user.id}, exam {exam_id}")
        
        db.session.commit()
        
        sync_log.status = 'success'
        sync_log.records_processed = len(answers)
        
        return {
            'success': True,
            'message': 'Answers synced successfully',
            'exam_id': exam_id,
            'answers_count': len(answers),
            'score': score
        }
        
    except Exception as e:
        logger.error(f"Error syncing exam answers: {e}")
        sync_log.status = 'error'
        sync_log.error_message = str(e)
        return {'success': False, 'error': 'Failed to sync answers'}

def sync_exam_metadata(data, sync_log):
    """Sync exam metadata to server"""
    try:
        exam_id = data.get('examId')
        metadata = data.get('metadata', {})
        
        if not exam_id or not metadata:
            sync_log.status = 'error'
            sync_log.error_message = 'Missing examId or metadata'
            return {'success': False, 'error': 'Missing examId or metadata'}
        
        # Store metadata (could be in a separate table or as JSON)
        # For now, just log it
        logger.info(f"Received metadata for exam {exam_id}: {metadata}")
        
        sync_log.status = 'success'
        sync_log.records_processed = 1
        
        return {
            'success': True,
            'message': 'Metadata synced successfully',
            'exam_id': exam_id
        }
        
    except Exception as e:
        logger.error(f"Error syncing exam metadata: {e}")
        sync_log.status = 'error'
        sync_log.error_message = str(e)
        return {'success': False, 'error': 'Failed to sync metadata'}

def sync_exam_progress(data, sync_log):
    """Sync exam progress to server"""
    try:
        exam_id = data.get('examId')
        progress = data.get('progress', {})
        
        if not exam_id:
            sync_log.status = 'error'
            sync_log.error_message = 'Missing examId'
            return {'success': False, 'error': 'Missing examId'}
        
        # Store progress (could be in session or database)
        logger.info(f"Received progress for exam {exam_id}: {progress}")
        
        sync_log.status = 'success'
        sync_log.records_processed = 1
        
        return {
            'success': True,
            'message': 'Progress synced successfully',
            'exam_id': exam_id
        }
        
    except Exception as e:
        logger.error(f"Error syncing exam progress: {e}")
        sync_log.status = 'error'
        sync_log.error_message = str(e)
        return {'success': False, 'error': 'Failed to sync progress'}

def calculate_exam_score(exam, answers):
    """Calculate exam score based on answers"""
    try:
        score = 0
        total_questions = 0
        
        for question in exam.questions:
            question_id = str(question.id)
            total_questions += 1
            
            if question_id in answers:
                user_answer = answers[question_id]
                if user_answer == question.correct_answer:
                    score += 1
        
        return score
        
    except Exception as e:
        logger.error(f"Error calculating exam score: {e}")
        return 0

@sync_bp.route('/sync_status')
@login_required
def get_sync_status():
    """Get current sync status for the user"""
    try:
        # Get recent sync logs
        recent_syncs = SyncLog.query.filter_by(user_id=current_user.id)\
            .order_by(SyncLog.server_timestamp.desc())\
            .limit(10).all()
        
        # Get pending sync count (from client-side, this is approximate)
        pending_count = request.args.get('pending_count', 0)
        
        sync_info = {
            'last_sync': None,
            'recent_syncs': [],
            'pending_count': int(pending_count),
            'sync_enabled': True
        }
        
        if recent_syncs:
            last_sync = recent_syncs[0]
            sync_info['last_sync'] = {
                'timestamp': last_sync.server_timestamp.isoformat(),
                'type': last_sync.sync_type,
                'status': last_sync.status,
                'records_processed': last_sync.records_processed
            }
            
            sync_info['recent_syncs'] = [
                {
                    'timestamp': sync.server_timestamp.isoformat(),
                    'type': sync.sync_type,
                    'status': sync.status,
                    'records_processed': sync.records_processed
                }
                for sync in recent_syncs[1:5]  # Last 5 excluding the most recent
            ]
        
        return jsonify({
            'success': True,
            'sync_info': sync_info
        })
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return jsonify({'error': 'Failed to get sync status'}), 500

@sync_bp.route('/force_sync', methods=['POST'])
@login_required
def force_sync():
    """Force synchronization of all pending data"""
    try:
        # This would trigger the client to sync all pending data
        # The actual sync logic is handled by the client-side JavaScript
        
        logger.info(f"Force sync requested by user {current_user.id}")
        
        return jsonify({
            'success': True,
            'message': 'Force sync initiated',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error during force sync: {e}")
        return jsonify({'error': 'Failed to force sync'}), 500

@sync_bp.route('/clear_offline_data', methods=['POST'])
@login_required
def clear_offline_data():
    """Clear offline data for the user"""
    try:
        # Clear sync logs for this user
        SyncLog.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        logger.info(f"Cleared offline data for user {current_user.id}")
        
        return jsonify({
            'success': True,
            'message': 'Offline data cleared successfully'
        })
        
    except Exception as e:
        logger.error(f"Error clearing offline data: {e}")
        return jsonify({'error': 'Failed to clear offline data'}), 500

@sync_bp.route('/sync_health')
def sync_health_check():
    """Health check for sync system"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check sync table
        sync_count = SyncLog.query.count()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'sync_records_count': sync_count,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Sync health check failed: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500
