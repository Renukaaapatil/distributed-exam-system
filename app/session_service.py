"""
Session Service for Fault-Tolerant Distributed Exam System
Handles exam session management, persistence, and recovery
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from flask import current_app
from app.models import db, ExamSession, User, Exam

logger = logging.getLogger(__name__)

class SessionService:
    """Service for managing exam sessions with fault tolerance"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_session(self, user_id: int, exam_id: int, node_id: str) -> Dict:
        """
        Create a new exam session
        
        Args:
            user_id: User ID
            exam_id: Exam ID
            node_id: Node ID handling the session
            
        Returns:
            Session information
        """
        try:
            # Check if user already has active session for this exam
            existing_session = ExamSession.query.filter_by(
                user_id=user_id,
                exam_id=exam_id,
                status='active'
            ).first()
            
            if existing_session:
                self.logger.info(f"Found existing session {existing_session.id} for user {user_id}")
                return existing_session.to_dict()
            
            # Create new session
            session = ExamSession(
                user_id=user_id,
                exam_id=exam_id,
                node_id=node_id,
                remaining_time=1800  # 30 minutes default
            )
            
            db.session.add(session)
            db.session.commit()
            
            self.logger.info(f"Created new session {session.id} for user {user_id} on node {node_id}")
            
            return session.to_dict()
            
        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
            db.session.rollback()
            return {'error': 'Failed to create session'}
    
    def save_progress(self, session_id: str, question_index: int, answers: Dict, remaining_time: int) -> Dict:
        """
        Save session progress
        
        Args:
            session_id: Session ID
            question_index: Current question index
            answers: Dictionary of answers
            remaining_time: Remaining time in seconds
            
        Returns:
            Updated session information
        """
        try:
            session = ExamSession.query.get(session_id)
            if not session:
                return {'error': 'Session not found'}
            
            # Update session progress
            session.update_progress(question_index, answers, remaining_time)
            
            db.session.commit()
            
            self.logger.debug(f"Saved progress for session {session_id}: Q{question_index}, {len(answers)} answers")
            
            return session.to_dict()
            
        except Exception as e:
            self.logger.error(f"Failed to save progress: {e}")
            db.session.rollback()
            return {'error': 'Failed to save progress'}
    
    def get_session(self, session_id: str) -> Dict:
        """
        Get session information
        
        Args:
            session_id: Session ID
            
        Returns:
            Session information
        """
        try:
            session = ExamSession.query.get(session_id)
            if not session:
                return {'error': 'Session not found'}
            
            return session.to_dict()
            
        except Exception as e:
            self.logger.error(f"Failed to get session: {e}")
            return {'error': 'Failed to get session'}
    
    def update_node(self, session_id: str, new_node_id: str) -> Dict:
        """
        Update the node handling a session (for failover)
        
        Args:
            session_id: Session ID
            new_node_id: New node ID
            
        Returns:
            Updated session information
        """
        try:
            session = ExamSession.query.get(session_id)
            if not session:
                return {'error': 'Session not found'}
            
            old_node_id = session.node_id
            session.node_id = new_node_id
            session.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            self.logger.info(f"Migrated session {session_id} from node {old_node_id} to node {new_node_id}")
            
            return session.to_dict()
            
        except Exception as e:
            self.logger.error(f"Failed to update node: {e}")
            db.session.rollback()
            return {'error': 'Failed to update node'}
    
    def complete_session(self, session_id: str) -> Dict:
        """
        Mark session as completed
        
        Args:
            session_id: Session ID
            
        Returns:
            Updated session information
        """
        try:
            session = ExamSession.query.get(session_id)
            if not session:
                return {'error': 'Session not found'}
            
            session.status = 'completed'
            session.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            self.logger.info(f"Completed session {session_id}")
            
            return session.to_dict()
            
        except Exception as e:
            self.logger.error(f"Failed to complete session: {e}")
            db.session.rollback()
            return {'error': 'Failed to complete session'}
    
    def fail_session(self, session_id: str, reason: str = "Node failure") -> Dict:
        """
        Mark session as failed
        
        Args:
            session_id: Session ID
            reason: Reason for failure
            
        Returns:
            Updated session information
        """
        try:
            session = ExamSession.query.get(session_id)
            if not session:
                return {'error': 'Session not found'}
            
            session.status = 'failed'
            session.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            self.logger.warning(f"Failed session {session_id}: {reason}")
            
            return session.to_dict()
            
        except Exception as e:
            self.logger.error(f"Failed to fail session: {e}")
            db.session.rollback()
            return {'error': 'Failed to fail session'}
    
    def get_active_sessions(self, node_id: Optional[str] = None) -> List[Dict]:
        """
        Get all active sessions, optionally filtered by node
        
        Args:
            node_id: Optional node ID filter
            
        Returns:
            List of session information
        """
        try:
            query = ExamSession.query.filter_by(status='active')
            
            if node_id:
                query = query.filter_by(node_id=node_id)
            
            sessions = query.all()
            
            return [session.to_dict() for session in sessions]
            
        except Exception as e:
            self.logger.error(f"Failed to get active sessions: {e}")
            return []
    
    def cleanup_old_sessions(self, days: int = 7) -> int:
        """
        Clean up old completed/failed sessions
        
        Args:
            days: Number of days to keep sessions
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            old_sessions = ExamSession.query.filter(
                ExamSession.status.in_(['completed', 'failed']),
                ExamSession.updated_at < cutoff_date
            ).all()
            
            count = len(old_sessions)
            
            for session in old_sessions:
                db.session.delete(session)
            
            db.session.commit()
            
            self.logger.info(f"Cleaned up {count} old sessions")
            
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old sessions: {e}")
            db.session.rollback()
            return 0
    
    def get_session_statistics(self) -> Dict:
        """
        Get session statistics
        
        Returns:
            Dictionary with session statistics
        """
        try:
            stats = {
                'total_sessions': ExamSession.query.count(),
                'active_sessions': ExamSession.query.filter_by(status='active').count(),
                'completed_sessions': ExamSession.query.filter_by(status='completed').count(),
                'failed_sessions': ExamSession.query.filter_by(status='failed').count(),
                'node_distribution': {}
            }
            
            # Get distribution by node
            nodes = db.session.query(ExamSession.node_id, db.func.count(ExamSession.id)).filter_by(status='active').group_by(ExamSession.node_id).all()
            
            for node_id, count in nodes:
                stats['node_distribution'][node_id] = count
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get session statistics: {e}")
            return {}

# Global service instance
session_service = SessionService()
