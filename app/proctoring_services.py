"""
Proctoring Services for Distributed Exam System
Handles AI proctoring operations, database storage, and alert management
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from flask import current_app
from app.models import (
    db, User, Exam, Response, ProctoringSession, 
    ProctoringViolation, ProctoringAlert
)
from core.ai_proctor import session_manager, ViolationType, Severity

class ProctoringService:
    """Service for managing AI proctoring operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def start_proctoring_session(self, user_id: int, exam_id: int, response_id: int) -> Dict:
        """
        Start a new proctoring session
        
        Args:
            user_id: User ID
            exam_id: Exam ID
            response_id: Response ID
            
        Returns:
            Session information
        """
        try:
            # Check if user already has active session
            existing_session = self.get_active_session(user_id)
            if existing_session:
                self.logger.warning(f"User {user_id} already has active proctoring session {existing_session.id}")
                return {
                    'session_id': existing_session.id,
                    'trust_score': existing_session.trust_score,
                    'status': existing_session.status,
                    'message': 'Session already active'
                }
            
            # Create database session record
            db_session = ProctoringSession(
                user_id=user_id,
                exam_id=exam_id,
                response_id=response_id,
                trust_score=100,
                initial_score=100,
                status='active'
            )
            db.session.add(db_session)
            db.session.commit()
            
            # Create AI proctoring session
            ai_session_id = session_manager.create_session(user_id, exam_id)
            
            self.logger.info(f"Started proctoring session {db_session.id} for user {user_id}")
            
            return {
                'session_id': db_session.id,
                'ai_session_id': ai_session_id,
                'trust_score': 100,
                'status': 'active',
                'message': 'Proctoring session started'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to start proctoring session: {e}")
            return {'error': str(e)}
    
    def stop_proctoring_session(self, session_id: int) -> Dict:
        """
        Stop a proctoring session
        
        Args:
            session_id: Session ID
            
        Returns:
            Session summary
        """
        try:
            # Get database session
            db_session = ProctoringSession.query.get(session_id)
            if not db_session:
                return {'error': 'Session not found'}
            
            # Get AI session
            user_id = db_session.user_id
            ai_session = session_manager.get_user_session(user_id)
            
            if ai_session:
                # Stop AI session and get data
                ai_data = ai_session.stop_session()
                session_data = ai_session.export_session_data()
                
                # Update database session
                db_session.final_score = session_data['trust_score']
                db_session.status = 'completed'
                db_session.ended_at = datetime.utcnow()
                
                # Store violations in database
                self._store_violations(session_id, session_data['violations'])
                
                # Remove AI session
                session_manager.remove_session(ai_session.session_id)
            
            else:
                # No AI session found, just mark as completed
                db_session.status = 'completed'
                db_session.ended_at = datetime.utcnow()
                db_session.final_score = db_session.trust_score
            
            db.session.commit()
            
            # Create summary alert if trust score is low
            if db_session.final_score < 60:
                self._create_alert(
                    session_id,
                    user_id,
                    'low_score',
                    f'Low trust score: {db_session.final_score}',
                    'critical'
                )
            
            self.logger.info(f"Stopped proctoring session {session_id}")
            
            return {
                'session_id': session_id,
                'final_score': db_session.final_score,
                'violations_count': len(db_session.violations),
                'status': db_session.status
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to stop proctoring session: {e}")
            return {'error': str(e)}
    
    def process_frame(self, user_id: int, frame_data: str) -> Dict:
        """
        Process video frame for proctoring
        
        Args:
            user_id: User ID
            frame_data: Base64 encoded frame data
            
        Returns:
            Processing results
        """
        try:
            # Get user's AI session
            ai_session = session_manager.get_user_session(user_id)
            if not ai_session:
                return {'error': 'No active proctoring session'}
            
            # Process frame
            result = ai_session.process_frame(frame_data)
            
            # Update database session if trust score changed
            if 'trust_score' in result:
                db_session = self.get_active_session(user_id)
                if db_session and db_session.trust_score != result['trust_score']:
                    db_session.trust_score = result['trust_score']
                    db_session.last_updated = datetime.utcnow()
                    db.session.commit()
                    
                    # Create alert for significant score drops
                    if result['trust_score'] < 60:
                        self._create_alert(
                            db_session.id,
                            user_id,
                            'low_score',
                            f'Trust score dropped to {result["trust_score"]}',
                            'warning'
                        )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process frame: {e}")
            return {'error': str(e)}
    
    def handle_tab_switch(self, user_id: int) -> Dict:
        """
        Handle tab switching event
        
        Args:
            user_id: User ID
            
        Returns:
            Violation information
        """
        try:
            # Get user's AI session
            ai_session = session_manager.get_user_session(user_id)
            if not ai_session:
                return {'error': 'No active proctoring session'}
            
            # Handle tab switch
            result = ai_session.handle_tab_switch()
            
            # Store violation if created
            if 'violation_type' in result:
                db_session = self.get_active_session(user_id)
                if db_session:
                    self._store_single_violation(db_session.id, result)
                    
                    # Create alert
                    self._create_alert(
                        db_session.id,
                        user_id,
                        'tab_switch',
                        'Tab switching detected during exam',
                        'warning'
                    )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to handle tab switch: {e}")
            return {'error': str(e)}
    
    def handle_suspicious_activity(self, user_id: int, activity_type: str) -> Dict:
        """
        Handle suspicious activity event
        
        Args:
            user_id: User ID
            activity_type: Type of suspicious activity
            
        Returns:
            Violation information
        """
        try:
            # Get user's AI session
            ai_session = session_manager.get_user_session(user_id)
            if not ai_session:
                return {'error': 'No active proctoring session'}
            
            # Handle suspicious activity
            result = ai_session.handle_suspicious_activity(activity_type)
            
            # Store violation if created
            if 'violation_type' in result:
                db_session = self.get_active_session(user_id)
                if db_session:
                    self._store_single_violation(db_session.id, result)
                    
                    # Create alert
                    self._create_alert(
                        db_session.id,
                        user_id,
                        'suspicious_activity',
                        f'Suspicious activity: {activity_type}',
                        'warning'
                    )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to handle suspicious activity: {e}")
            return {'error': str(e)}
    
    def get_proctoring_status(self, user_id: int) -> Dict:
        """
        Get current proctoring status for user
        
        Args:
            user_id: User ID
            
        Returns:
            Proctoring status
        """
        try:
            # Get database session
            db_session = self.get_active_session(user_id)
            if not db_session:
                return {'error': 'No active proctoring session'}
            
            # Get AI session status
            ai_session = session_manager.get_user_session(user_id)
            ai_status = ai_session.get_status() if ai_session else {}
            
            # Combine status
            status = {
                'session_id': db_session.id,
                'trust_score': db_session.trust_score,
                'initial_score': db_session.initial_score,
                'status': db_session.status,
                'started_at': db_session.started_at.isoformat(),
                'last_updated': db_session.last_updated.isoformat(),
                'status_color': self._get_status_color(db_session.trust_score),
                'violations_count': len(db_session.violations),
                'alerts_count': len([a for a in db_session.alerts if a.status == 'unread'])
            }
            
            # Add AI session data
            if ai_status:
                status.update({
                    'frames_processed': ai_status.get('frames_processed', 0),
                    'tab_switch_count': ai_status.get('tab_switch_stats', {}).get('tab_switch_count', 0),
                    'suspicious_activity_count': ai_status.get('tab_switch_stats', {}).get('suspicious_activity_count', 0)
                })
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get proctoring status: {e}")
            return {'error': str(e)}
    
    def get_violations(self, session_id: int, limit: int = 50) -> List[Dict]:
        """
        Get violations for a session
        
        Args:
            session_id: Session ID
            limit: Maximum number of violations to return
            
        Returns:
            List of violations
        """
        try:
            violations = ProctoringViolation.query.filter_by(
                session_id=session_id
            ).order_by(
                ProctoringViolation.detected_at.desc()
            ).limit(limit).all()
            
            return [self._format_violation(v) for v in violations]
            
        except Exception as e:
            self.logger.error(f"Failed to get violations: {e}")
            return []
    
    def get_alerts(self, user_id: int = None, status: str = None, limit: int = 50) -> List[Dict]:
        """
        Get proctoring alerts
        
        Args:
            user_id: Filter by user ID (optional)
            status: Filter by status (optional)
            limit: Maximum number of alerts to return
            
        Returns:
            List of alerts
        """
        try:
            query = ProctoringAlert.query
            
            if user_id:
                query = query.filter_by(user_id=user_id)
            
            if status:
                query = query.filter_by(status=status)
            
            alerts = query.order_by(
                ProctoringAlert.created_at.desc()
            ).limit(limit).all()
            
            return [self._format_alert(a) for a in alerts]
            
        except Exception as e:
            self.logger.error(f"Failed to get alerts: {e}")
            return []
    
    def mark_alert_read(self, alert_id: int) -> bool:
        """
        Mark alert as read
        
        Args:
            alert_id: Alert ID
            
        Returns:
            Success status
        """
        try:
            alert = ProctoringAlert.query.get(alert_id)
            if not alert:
                return False
            
            alert.status = 'read'
            alert.read_at = datetime.utcnow()
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to mark alert as read: {e}")
            return False
    
    def resolve_alert(self, alert_id: int) -> bool:
        """
        Resolve alert
        
        Args:
            alert_id: Alert ID
            
        Returns:
            Success status
        """
        try:
            alert = ProctoringAlert.query.get(alert_id)
            if not alert:
                return False
            
            alert.status = 'resolved'
            alert.resolved_at = datetime.utcnow()
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to resolve alert: {e}")
            return False
    
    def get_proctoring_summary(self, exam_id: int = None) -> Dict:
        """
        Get proctoring summary for exam or all exams
        
        Args:
            exam_id: Exam ID (optional)
            
        Returns:
            Proctoring summary
        """
        try:
            query = ProctoringSession.query
            
            if exam_id:
                query = query.filter_by(exam_id=exam_id)
            
            sessions = query.all()
            
            total_sessions = len(sessions)
            active_sessions = len([s for s in sessions if s.status == 'active'])
            completed_sessions = len([s for s in sessions if s.status == 'completed'])
            flagged_sessions = len([s for s in sessions if s.status == 'flagged'])
            
            # Trust score distribution
            high_trust = len([s for s in sessions if s.trust_score >= 80])
            medium_trust = len([s for s in sessions if 60 <= s.trust_score < 80])
            low_trust = len([s for s in sessions if s.trust_score < 60])
            
            # Violation statistics
            total_violations = db.session.query(ProctoringViolation).join(
                ProctoringSession
            )
            if exam_id:
                total_violations = total_violations.filter(ProctoringSession.exam_id == exam_id)
            total_violations = total_violations.count()
            
            # Recent alerts
            recent_alerts = db.session.query(ProctoringAlert).join(
                ProctoringSession
            )
            if exam_id:
                recent_alerts = recent_alerts.filter(ProctoringSession.exam_id == exam_id)
            recent_alerts = recent_alerts.filter(
                ProctoringAlert.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            return {
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'completed_sessions': completed_sessions,
                'flagged_sessions': flagged_sessions,
                'trust_score_distribution': {
                    'high': high_trust,
                    'medium': medium_trust,
                    'low': low_trust
                },
                'total_violations': total_violations,
                'recent_alerts': recent_alerts,
                'exam_id': exam_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get proctoring summary: {e}")
            return {'error': str(e)}
    
    # Private helper methods
    
    def get_active_session(self, user_id: int) -> Optional[ProctoringSession]:
        """Get active proctoring session for user"""
        return ProctoringSession.query.filter_by(
            user_id=user_id,
            status='active'
        ).first()
    
    def _store_violations(self, session_id: int, violations: List[Dict]):
        """Store violations in database"""
        try:
            for violation_data in violations:
                self._store_single_violation(session_id, violation_data)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to store violations: {e}")
    
    def _store_single_violation(self, session_id: int, violation_data: Dict):
        """Store single violation in database"""
        try:
            violation = ProctoringViolation(
                session_id=session_id,
                user_id=violation_data['user_id'],
                violation_type=violation_data['violation_type'],
                severity=violation_data['severity'],
                details=violation_data['details'],
                trust_score_before=violation_data['trust_score_before'],
                trust_score_after=violation_data['trust_score_after'],
                score_penalty=violation_data['score_penalty'],
                detected_at=datetime.fromtimestamp(violation_data['timestamp'])
            )
            
            # Store evidence data if present
            if 'evidence' in violation_data:
                violation.set_evidence(violation_data['evidence'])
            
            db.session.add(violation)
            
        except Exception as e:
            self.logger.error(f"Failed to store violation: {e}")
    
    def _create_alert(self, session_id: int, user_id: int, alert_type: str, 
                     message: str, severity: str):
        """Create proctoring alert"""
        try:
            alert = ProctoringAlert(
                session_id=session_id,
                user_id=user_id,
                alert_type=alert_type,
                message=message,
                severity=severity
            )
            
            db.session.add(alert)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to create alert: {e}")
    
    def _get_status_color(self, trust_score: int) -> str:
        """Get status color based on trust score"""
        if trust_score >= 80:
            return 'green'
        elif trust_score >= 60:
            return 'yellow'
        else:
            return 'red'
    
    def _format_violation(self, violation: ProctoringViolation) -> Dict:
        """Format violation for API response"""
        return {
            'id': violation.id,
            'violation_type': violation.violation_type,
            'severity': violation.severity,
            'details': violation.details,
            'trust_score_before': violation.trust_score_before,
            'trust_score_after': violation.trust_score_after,
            'score_penalty': violation.score_penalty,
            'detected_at': violation.detected_at.isoformat(),
            'evidence': violation.get_evidence()
        }
    
    def _format_alert(self, alert: ProctoringAlert) -> Dict:
        """Format alert for API response"""
        return {
            'id': alert.id,
            'alert_type': alert.alert_type,
            'message': alert.message,
            'severity': alert.severity,
            'status': alert.status,
            'created_at': alert.created_at.isoformat(),
            'read_at': alert.read_at.isoformat() if alert.read_at else None,
            'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
        }
    
    def update_trust_score(self, user_id: int, exam_id: int, violation_type: str, score_reduction: int = None) -> Dict:
        """
        Update trust score based on violation type
        
        Args:
            user_id: User ID
            exam_id: Exam ID
            violation_type: Type of violation detected
            score_reduction: Custom score reduction (optional)
            
        Returns:
            Updated trust score and session info
        """
        try:
            # Get active session
            session = self.get_active_session(user_id)
            if not session:
                return {'error': 'No active proctoring session found'}
            
            # Define violation penalties
            violation_penalties = {
                'looking_away': -10,
                'head_turned': -15,
                'multiple_faces': -30,
                'phone_detected': -40,
                'tab_switch': -20,
                'voice_detected': -20  # Voice detection penalty
            }
            
            # Get penalty for violation type
            if score_reduction is not None:
                penalty = -abs(score_reduction)  # Ensure it's negative
            else:
                penalty = violation_penalties.get(violation_type, -5)
            
            # Update trust score
            old_score = session.trust_score
            new_score = max(0, old_score + penalty)  # Don't go below 0
            session.trust_score = new_score
            session.last_updated = datetime.utcnow()
            
            # Create violation record
            violation = ProctoringViolation(
                session_id=session.id,
                user_id=user_id,
                exam_id=exam_id,
                violation_type=violation_type,
                severity='high' if penalty <= -30 else 'medium' if penalty <= -15 else 'low',
                trust_score_before=old_score,
                trust_score_after=new_score,
                score_penalty=abs(penalty),
                details=f"Violation: {violation_type}, Penalty: {penalty} points"
            )
            db.session.add(violation)
            
            # Create alert if score is critical
            if new_score <= 30:
                alert = ProctoringAlert(
                    user_id=user_id,
                    exam_id=exam_id,
                    session_id=session.id,
                    alert_type='critical_score',
                    message=f'Critical trust score: {new_score}/100',
                    severity='critical'
                )
                db.session.add(alert)
            
            db.session.commit()
            
            # Auto-submit if trust score is 0 or below
            if new_score <= 0:
                self.auto_submit_exam(user_id, exam_id)
            
            return {
                'success': True,
                'trust_score': new_score,
                'old_score': old_score,
                'penalty': penalty,
                'violation_type': violation_type,
                'session_id': session.id,
                'auto_submitted': new_score <= 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update trust score: {e}")
            return {'error': 'Failed to update trust score'}
    
    def get_trust_score(self, user_id: int, exam_id: int) -> Dict:
        """
        Get current trust score for user's active session
        
        Args:
            user_id: User ID
            exam_id: Exam ID
            
        Returns:
            Current trust score and session info
        """
        try:
            session = self.get_active_session(user_id)
            if not session:
                return {'error': 'No active proctoring session found'}
            
            # Determine status color
            if session.trust_score >= 80:
                status_color = 'green'
                status_text = 'Excellent'
            elif session.trust_score >= 50:
                status_color = 'yellow'
                status_text = 'Warning'
            else:
                status_color = 'red'
                status_text = 'Danger'
            
            return {
                'trust_score': session.trust_score,
                'initial_score': session.initial_score,
                'status_color': status_color,
                'status_text': status_text,
                'session_id': session.id,
                'last_updated': session.last_updated.isoformat(),
                'violations_count': len(session.violations)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get trust score: {e}")
            return {'error': 'Failed to get trust score'}
    
    def auto_submit_exam(self, user_id: int, exam_id: int) -> Dict:
        """
        Auto-submit exam due to low trust score
        
        Args:
            user_id: User ID
            exam_id: Exam ID
            
        Returns:
            Submission result
        """
        try:
            session = self.get_active_session(user_id)
            if not session:
                return {'error': 'No active proctoring session found'}
            
            # Mark session as completed due to violation
            session.status = 'flagged'
            session.final_score = session.trust_score
            session.ended_at = datetime.utcnow()
            
            # Create alert for auto-submission
            alert = ProctoringAlert(
                user_id=user_id,
                exam_id=exam_id,
                session_id=session.id,
                alert_type='auto_submit',
                message='Exam auto-submitted due to trust score violation',
                severity='critical'
            )
            db.session.add(alert)
            
            db.session.commit()
            
            # Here you would typically integrate with your exam submission system
            # For now, we'll just return the session info
            return {
                'success': True,
                'message': 'Exam auto-submitted due to trust score violation',
                'session_id': session.id,
                'final_score': session.trust_score,
                'violations_count': len(session.violations)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to auto submit exam: {e}")
            return {'error': 'Failed to auto submit exam'}

# Global service instance
proctoring_service = ProctoringService()
