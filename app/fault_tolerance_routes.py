"""
Fault Tolerance Routes for Distributed Exam System
Handles session management, failover, and recovery endpoints
"""

import json
import logging
from flask import Blueprint, request, jsonify, redirect, url_for
from app.session_service import session_service
from app.fault_tolerance import fault_tolerance_manager
from app import db

logger = logging.getLogger(__name__)

fault_tolerance_bp = Blueprint('fault_tolerance', __name__, url_prefix='/api/fault_tolerance')

@fault_tolerance_bp.route('/save_progress', methods=['POST'])
def save_progress():
    """Save exam session progress"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        session_id = data.get('session_id')
        question_index = data.get('current_question_index', 0)
        answers = data.get('answers', {})
        remaining_time = data.get('remaining_time', 1800)
        
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        # Save progress
        result = session_service.save_progress(session_id, question_index, answers, remaining_time)
        
        if 'error' in result:
            return jsonify(result), 400
        
        logger.info(f"Progress saved for session {session_id}")
        
        return jsonify({
            'success': True,
            'session': result,
            'timestamp': result.get('last_saved')
        })
        
    except Exception as e:
        logger.error(f"Failed to save progress: {e}")
        return jsonify({'error': 'Failed to save progress'}), 500

@fault_tolerance_bp.route('/resume_exam/<session_id>', methods=['GET'])
def resume_exam(session_id):
    """Resume exam from saved session"""
    try:
        # Get session data
        session_data = session_service.get_session(session_id)
        
        if 'error' in session_data:
            return jsonify(session_data), 404
        
        # Check if session is active
        if session_data.get('status') != 'active':
            return jsonify({'error': 'Session is not active'}), 400
        
        logger.info(f"Resuming exam session {session_id}")
        
        return jsonify({
            'success': True,
            'session': session_data
        })
        
    except Exception as e:
        logger.error(f"Failed to resume exam: {e}")
        return jsonify({'error': 'Failed to resume exam'}), 500

@fault_tolerance_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for load balancer"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check if fault tolerance manager is running
        ft_status = fault_tolerance_manager.get_node_status()
        
        return jsonify({
            'status': 'alive',
            'timestamp': '2024-01-01T00:00:00Z',
            'database': 'connected',
            'fault_tolerance': 'active',
            'node_status': ft_status
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@fault_tolerance_bp.route('/register_session', methods=['POST'])
def register_session():
    """Register a new exam session"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        user_id = data.get('user_id', 1)  # Default user ID for testing
        exam_id = data.get('exam_id')
        node_id = data.get('node_id', 'unknown')
        
        if not exam_id:
            return jsonify({'error': 'exam_id is required'}), 400
        
        # Create session
        result = session_service.create_session(user_id, exam_id, node_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        logger.info(f"Session {result['session_id']} registered on node {node_id}")
        
        return jsonify({
            'success': True,
            'session': result
        })
        
    except Exception as e:
        logger.error(f"Failed to register session: {e}")
        return jsonify({'error': 'Failed to register session'}), 500

@fault_tolerance_bp.route('/end_session', methods=['POST'])
def end_session():
    """End an exam session"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        # Complete session
        result = session_service.complete_session(session_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        logger.info(f"Session {session_id} ended")
        
        return jsonify({
            'success': True,
            'session': result
        })
        
    except Exception as e:
        logger.error(f"Failed to end session: {e}")
        return jsonify({'error': 'Failed to end session'}), 500

@fault_tolerance_bp.route('/session_migration', methods=['POST'])
def session_migration():
    """Handle incoming session migration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        session_id = data.get('session_id')
        is_migration = data.get('migration', False)
        
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        if not is_migration:
            return jsonify({'error': 'Not a migration request'}), 400
        
        # Get session data to verify it exists
        session_data = session_service.get_session(session_id)
        
        if 'error' in session_data:
            return jsonify({'error': 'Session not found'}), 404
        
        logger.info(f"Received session migration for {session_id}")
        
        return jsonify({
            'success': True,
            'message': 'Session migration accepted',
            'session': session_data
        })
        
    except Exception as e:
        logger.error(f"Failed to handle session migration: {e}")
        return jsonify({'error': 'Failed to handle session migration'}), 500

@fault_tolerance_bp.route('/node_status', methods=['GET'])
def node_status():
    """Get node status and statistics"""
    try:
        # Get fault tolerance status
        ft_status = fault_tolerance_manager.get_node_status()
        
        # Get session statistics
        session_stats = session_service.get_session_statistics()
        
        # Get active sessions for this node
        active_sessions = session_service.get_active_sessions()
        
        return jsonify({
            'node_status': ft_status,
            'session_statistics': session_stats,
            'active_sessions': active_sessions,
            'healthy_nodes': fault_tolerance_manager.get_healthy_nodes()
        })
        
    except Exception as e:
        logger.error(f"Failed to get node status: {e}")
        return jsonify({'error': 'Failed to get node status'}), 500

@fault_tolerance_bp.route('/migrate_session', methods=['POST'])
def migrate_session():
    """Manually migrate a session to another node"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        session_id = data.get('session_id')
        target_node = data.get('target_node')
        
        if not session_id or not target_node:
            return jsonify({'error': 'session_id and target_node are required'}), 400
        
        # Check if target node is healthy
        if not fault_tolerance_manager.is_node_healthy(target_node):
            return jsonify({'error': f'Target node {target_node} is not healthy'}), 400
        
        # Get current session to find source node
        session_data = session_service.get_session(session_id)
        
        if 'error' in session_data:
            return jsonify({'error': 'Session not found'}), 404
        
        source_node = session_data.get('node_id')
        
        # Migrate session
        success = fault_tolerance_manager._migrate_session(session_id, source_node, target_node)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Session migrated from Node {source_node} to Node {target_node}'
            })
        else:
            return jsonify({'error': 'Migration failed'}), 500
        
    except Exception as e:
        logger.error(f"Failed to migrate session: {e}")
        return jsonify({'error': 'Failed to migrate session'}), 500

@fault_tolerance_bp.route('/trigger_failover', methods=['POST'])
def trigger_failover():
    """Trigger failover for testing purposes"""
    try:
        data = request.get_json()
        node_id = data.get('node_id')
        
        if not node_id:
            return jsonify({'error': 'node_id is required'}), 400
        
        # Simulate node failure
        logger.warning(f"Simulating failure for Node {node_id}")
        
        # Handle the failure
        fault_tolerance_manager._handle_node_failure(node_id)
        
        return jsonify({
            'success': True,
            'message': f'Failover triggered for Node {node_id}'
        })
        
    except Exception as e:
        logger.error(f"Failed to trigger failover: {e}")
        return jsonify({'error': 'Failed to trigger failover'}), 500
