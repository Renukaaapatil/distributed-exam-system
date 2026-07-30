"""
AI Proctoring System for Distributed Exam System
Implements face detection, tab switching detection, and Trust Score management
"""

import cv2
import numpy as np
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import base64

class ViolationType(Enum):
    """Types of proctoring violations"""
    NO_FACE = "no_face"
    MULTIPLE_FACES = "multiple_faces"
    FACE_NOT_VISIBLE = "face_not_visible"
    TAB_SWITCH = "tab_switch"
    WINDOW_BLUR = "window_blur"
    SUSPICIOUS_MOVEMENT = "suspicious_movement"
    NO_CAMERA = "no_camera"
    CAMERA_BLOCKED = "camera_blocked"

class Severity(Enum):
    """Violation severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FaceDetector:
    """Face detection using OpenCV"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Load face cascade classifier
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            
            # Check if classifiers loaded successfully
            if self.face_cascade.empty():
                raise Exception("Failed to load face cascade classifier")
            if self.eye_cascade.empty():
                self.logger.warning("Failed to load eye cascade classifier")
                
            self.logger.info("Face detection models loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize face detector: {e}")
            self.face_cascade = None
            self.eye_cascade = None
    
    def detect_faces(self, image: np.ndarray) -> Tuple[List[Dict], bool]:
        """
        Detect faces in image
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Tuple of (faces_list, success)
        """
        if self.face_cascade is None:
            return [], False
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30)
            )
            
            # Format face data
            face_data = []
            for (x, y, w, h) in faces:
                face_info = {
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'confidence': self._calculate_face_confidence(gray, x, y, w, h)
                }
                face_data.append(face_info)
            
            return face_data, True
            
        except Exception as e:
            self.logger.error(f"Face detection error: {e}")
            return [], False
    
    def _calculate_face_confidence(self, gray: np.ndarray, x: int, y: int, w: int, h: int) -> float:
        """Calculate confidence score for detected face"""
        try:
            # Extract face region
            face_roi = gray[y:y+h, x:x+w]
            
            # Detect eyes in face region
            if self.eye_cascade is not None:
                eyes = self.eye_cascade.detectMultiScale(face_roi)
                eye_count = len(eyes)
                
                # Higher confidence if eyes are detected
                base_confidence = 0.7
                eye_bonus = min(0.3, eye_count * 0.15)
                
                return base_confidence + eye_bonus
            else:
                return 0.7  # Default confidence without eye detection
                
        except Exception:
            return 0.5  # Low confidence on error
    
    def is_face_clearly_visible(self, image: np.ndarray, face: Dict) -> bool:
        """Check if face is clearly visible and properly positioned"""
        try:
            x, y, w, h = face['x'], face['y'], face['width'], face['height']
            
            # Check face size (should be reasonable size)
            image_height, image_width = image.shape[:2]
            face_area_ratio = (w * h) / (image_width * image_height)
            
            if face_area_ratio < 0.02:  # Face too small
                return False
            if face_area_ratio > 0.8:  # Face too large (too close to camera)
                return False
            
            # Check face position (should be roughly centered)
            face_center_x = x + w // 2
            face_center_y = y + h // 2
            image_center_x = image_width // 2
            image_center_y = image_height // 2
            
            # Face should be within reasonable distance from center
            max_offset = min(image_width, image_height) // 4
            if abs(face_center_x - image_center_x) > max_offset:
                return False
            if abs(face_center_y - image_center_y) > max_offset:
                return False
            
            # Check confidence
            if face.get('confidence', 0) < 0.6:
                return False
            
            return True
            
        except Exception:
            return False

class TrustScoreManager:
    """Manages Trust Score calculations and updates"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Violation penalties
        self.violation_penalties = {
            ViolationType.NO_FACE: 15,
            ViolationType.MULTIPLE_FACES: 20,
            ViolationType.FACE_NOT_VISIBLE: 10,
            ViolationType.TAB_SWITCH: 25,
            ViolationType.WINDOW_BLUR: 5,
            ViolationType.SUSPICIOUS_MOVEMENT: 8,
            ViolationType.NO_CAMERA: 30,
            ViolationType.CAMERA_BLOCKED: 25
        }
        
        # Recovery rates (points recovered per minute of good behavior)
        self.recovery_rates = {
            Severity.LOW: 1,
            Severity.MEDIUM: 0.5,
            Severity.HIGH: 0.2,
            Severity.CRITICAL: 0.1
        }
    
    def calculate_new_score(self, current_score: int, violation_type: ViolationType, 
                          severity: Severity, context: Dict = None) -> int:
        """
        Calculate new trust score after violation
        
        Args:
            current_score: Current trust score (0-100)
            violation_type: Type of violation
            severity: Severity level
            context: Additional context for calculation
            
        Returns:
            New trust score
        """
        base_penalty = self.violation_penalties.get(violation_type, 10)
        
        # Adjust penalty based on severity
        severity_multipliers = {
            Severity.LOW: 0.5,
            Severity.MEDIUM: 1.0,
            Severity.HIGH: 1.5,
            Severity.CRITICAL: 2.0
        }
        
        adjusted_penalty = int(base_penalty * severity_multipliers.get(severity, 1.0))
        
        # Apply context-based adjustments
        if context:
            # First violation of this type - reduce penalty
            if context.get('first_occurrence', False):
                adjusted_penalty = int(adjusted_penalty * 0.7)
            
            # Repeated violations - increase penalty
            if context.get('repeat_count', 0) > 2:
                adjusted_penalty = int(adjusted_penalty * 1.5)
            
            # Time-based adjustments
            if context.get('exam_progress', 0) > 0.8:  # Late in exam
                adjusted_penalty = int(adjusted_penalty * 1.2)
        
        # Calculate new score
        new_score = max(0, current_score - adjusted_penalty)
        
        self.logger.info(f"Trust score updated: {current_score} -> {new_score} (penalty: {adjusted_penalty})")
        
        return new_score
    
    def calculate_recovery(self, current_score: int, last_violation_severity: Severity, 
                          minutes_since_violation: int) -> int:
        """
        Calculate trust score recovery for good behavior
        
        Args:
            current_score: Current trust score
            last_violation_severity: Severity of last violation
            minutes_since_violation: Minutes since last violation
            
        Returns:
            Recovered trust score
        """
        if current_score >= 100:
            return current_score  # Already at max
        
        recovery_rate = self.recovery_rates.get(last_violation_severity, 0.5)
        recovery_amount = int(recovery_rate * minutes_since_violation)
        
        new_score = min(100, current_score + recovery_amount)
        
        if recovery_amount > 0:
            self.logger.info(f"Trust score recovery: {current_score} -> {new_score} (recovered: {recovery_amount})")
        
        return new_score

class TabSwitchDetector:
    """Detects tab switching and window focus changes"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.last_focus_time = time.time()
        self.tab_switch_count = 0
        self.suspicious_activity_count = 0
        self.monitoring_active = False
    
    def start_monitoring(self):
        """Start tab switch monitoring"""
        self.monitoring_active = True
        self.last_focus_time = time.time()
        self.logger.info("Tab switch monitoring started")
    
    def stop_monitoring(self):
        """Stop tab switch monitoring"""
        self.monitoring_active = False
        self.logger.info("Tab switch monitoring stopped")
    
    def record_tab_switch(self):
        """Record a tab switch event"""
        if not self.monitoring_active:
            return
        
        current_time = time.time()
        time_since_last_switch = current_time - self.last_focus_time
        
        # Ignore rapid switches (could be accidental)
        if time_since_last_switch < 0.5:
            return
        
        self.tab_switch_count += 1
        self.last_focus_time = current_time
        
        self.logger.warning(f"Tab switch detected (total: {self.tab_switch_count})")
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'tab_switch_count': self.tab_switch_count,
            'time_since_last_switch': time_since_last_switch
        }
    
    def record_suspicious_activity(self, activity_type: str):
        """Record suspicious activity"""
        self.suspicious_activity_count += 1
        self.logger.warning(f"Suspicious activity: {activity_type} (total: {self.suspicious_activity_count})")
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': activity_type,
            'suspicious_count': self.suspicious_activity_count
        }
    
    def get_statistics(self) -> Dict:
        """Get tab switching statistics"""
        return {
            'tab_switch_count': self.tab_switch_count,
            'suspicious_activity_count': self.suspicious_activity_count,
            'monitoring_active': self.monitoring_active,
            'last_focus_time': self.last_focus_time
        }

class AIProctor:
    """Main AI Proctoring System"""
    
    def __init__(self, session_id: int, user_id: int, exam_id: int):
        self.session_id = session_id
        self.user_id = user_id
        self.exam_id = exam_id
        self.logger = logging.getLogger(f"{__name__}.AIProctor.{session_id}")
        
        # Initialize components
        self.face_detector = FaceDetector()
        self.trust_score_manager = TrustScoreManager()
        self.tab_switch_detector = TabSwitchDetector()
        
        # Session state
        self.current_trust_score = 100
        self.session_active = False
        self.violation_history = []
        self.last_frame_time = time.time()
        self.frames_processed = 0
        self.violation_counts = {}
        
        # Configuration
        self.frame_interval = 1.0  # Process 1 frame per second
        self.no_face_threshold = 3  # Seconds before no face violation
        self.multiple_faces_threshold = 1  # Instant violation for multiple faces
        
        # Timing
        self.last_violation_time = {}
        self.last_recovery_check = time.time()
        self.recovery_check_interval = 60  # Check recovery every minute
        
        self.logger.info(f"AI Proctor initialized for session {session_id}")
    
    def start_session(self):
        """Start proctoring session"""
        self.session_active = True
        self.current_trust_score = 100
        self.tab_switch_detector.start_monitoring()
        self.last_recovery_check = time.time()
        
        self.logger.info(f"Proctoring session started for user {self.user_id}")
        
        return {
            'session_id': self.session_id,
            'initial_trust_score': self.current_trust_score,
            'started_at': datetime.utcnow().isoformat()
        }
    
    def stop_session(self):
        """Stop proctoring session"""
        self.session_active = False
        self.tab_switch_detector.stop_monitoring()
        
        self.logger.info(f"Proctoring session stopped for user {self.user_id}")
        
        return {
            'session_id': self.session_id,
            'final_trust_score': self.current_trust_score,
            'violations_detected': len(self.violation_history),
            'ended_at': datetime.utcnow().isoformat()
        }
    
    def process_frame(self, frame_data: str) -> Dict:
        """
        Process video frame for proctoring
        
        Args:
            frame_data: Base64 encoded image data
            
        Returns:
            Processing results with violations and trust score
        """
        if not self.session_active:
            return {'error': 'Session not active'}
        
        current_time = time.time()
        
        # Rate limiting
        if current_time - self.last_frame_time < self.frame_interval:
            return {'status': 'rate_limited'}
        
        self.last_frame_time = current_time
        self.frames_processed += 1
        
        try:
            # Decode base64 image
            image_data = base64.b64decode(frame_data)
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return self._create_violation(ViolationType.NO_CAMERA, Severity.CRITICAL, 
                                           "Failed to decode camera frame")
            
            # Detect faces
            faces, detection_success = self.face_detector.detect_faces(image)
            
            if not detection_success:
                return self._create_violation(ViolationType.CAMERA_BLOCKED, Severity.HIGH,
                                           "Face detection failed")
            
            # Analyze face detection results
            violations = self._analyze_faces(image, faces)
            
            # Check for recovery
            self._check_recovery(current_time)
            
            # Return results
            return {
                'status': 'success',
                'faces_detected': len(faces),
                'trust_score': self.current_trust_score,
                'violations': violations,
                'session_active': self.session_active,
                'frames_processed': self.frames_processed
            }
            
        except Exception as e:
            self.logger.error(f"Frame processing error: {e}")
            return self._create_violation(ViolationType.CAMERA_BLOCKED, Severity.MEDIUM,
                                       f"Processing error: {str(e)}")
    
    def _analyze_faces(self, image: np.ndarray, faces: List[Dict]) -> List[Dict]:
        """Analyze detected faces for violations"""
        violations = []
        current_time = time.time()
        
        # Check for no faces
        if len(faces) == 0:
            violation = self._check_no_face_violation(current_time)
            if violation:
                violations.append(violation)
        
        # Check for multiple faces
        elif len(faces) > 1:
            violation = self._create_violation(ViolationType.MULTIPLE_FACES, Severity.HIGH,
                                              f"Multiple faces detected: {len(faces)}")
            violations.append(violation)
        
        # Check single face visibility
        elif len(faces) == 1:
            face = faces[0]
            if not self.face_detector.is_face_clearly_visible(image, face):
                violation = self._create_violation(ViolationType.FACE_NOT_VISIBLE, Severity.MEDIUM,
                                                  "Face not clearly visible")
                violations.append(violation)
        
        return violations
    
    def _check_no_face_violation(self, current_time: float) -> Optional[Dict]:
        """Check if no face violation should be triggered"""
        last_no_face_time = self.last_violation_time.get(ViolationType.NO_FACE, 0)
        
        if current_time - last_no_face_time > self.no_face_threshold:
            violation = self._create_violation(ViolationType.NO_FACE, Severity.HIGH,
                                              "No face detected in camera")
            self.last_violation_time[ViolationType.NO_FACE] = current_time
            return violation
        
        return None
    
    def _check_recovery(self, current_time: float):
        """Check if trust score should recover"""
        if current_time - self.last_recovery_check < self.recovery_check_interval:
            return
        
        self.last_recovery_check = current_time
        
        # Find most recent violation
        if self.violation_history:
            last_violation = self.violation_history[-1]
            minutes_since_violation = int((current_time - last_violation['timestamp']) / 60)
            
            if minutes_since_violation >= 1:  # Only recover after 1 minute of good behavior
                last_severity = Severity(last_violation['severity'])
                old_score = self.current_trust_score
                self.current_trust_score = self.trust_score_manager.calculate_recovery(
                    self.current_trust_score, last_severity, minutes_since_violation
                )
                
                if self.current_trust_score > old_score:
                    self.logger.info(f"Trust score recovered: {old_score} -> {self.current_trust_score}")
    
    def _create_violation(self, violation_type: ViolationType, severity: Severity, 
                         details: str) -> Dict:
        """Create a violation record"""
        current_time = time.time()
        
        # Calculate new trust score
        context = {
            'first_occurrence': self.violation_counts.get(violation_type, 0) == 0,
            'repeat_count': self.violation_counts.get(violation_type, 0)
        }
        
        old_score = self.current_trust_score
        self.current_trust_score = self.trust_score_manager.calculate_new_score(
            old_score, violation_type, severity, context
        )
        
        # Update violation count
        self.violation_counts[violation_type] = self.violation_counts.get(violation_type, 0) + 1
        self.last_violation_time[violation_type] = current_time
        
        # Create violation record
        violation = {
            'timestamp': current_time,
            'violation_type': violation_type.value,
            'severity': severity.value,
            'details': details,
            'trust_score_before': old_score,
            'trust_score_after': self.current_trust_score,
            'score_penalty': old_score - self.current_trust_score,
            'session_id': self.session_id,
            'user_id': self.user_id
        }
        
        self.violation_history.append(violation)
        
        self.logger.warning(f"Violation detected: {violation_type.value} - {details}")
        
        return violation
    
    def handle_tab_switch(self) -> Dict:
        """Handle tab switch event"""
        if not self.session_active:
            return {'error': 'Session not active'}
        
        switch_data = self.tab_switch_detector.record_tab_switch()
        
        if switch_data:
            # Create violation
            violation = self._create_violation(ViolationType.TAB_SWITCH, Severity.HIGH,
                                              "Tab switching detected during exam")
            violation['tab_switch_data'] = switch_data
            
            return violation
        
        return {'status': 'no_violation'}
    
    def handle_suspicious_activity(self, activity_type: str) -> Dict:
        """Handle suspicious activity event"""
        if not self.session_active:
            return {'error': 'Session not active'}
        
        activity_data = self.tab_switch_detector.record_suspicious_activity(activity_type)
        
        if activity_data:
            # Create violation
            violation = self._create_violation(ViolationType.SUSPICIOUS_MOVEMENT, Severity.MEDIUM,
                                              f"Suspicious activity: {activity_type}")
            violation['activity_data'] = activity_data
            
            return violation
        
        return {'status': 'no_violation'}
    
    def get_status(self) -> Dict:
        """Get current proctoring status"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'exam_id': self.exam_id,
            'session_active': self.session_active,
            'trust_score': self.current_trust_score,
            'status_color': self._get_status_color(),
            'frames_processed': self.frames_processed,
            'violations_detected': len(self.violation_history),
            'violation_counts': dict(self.violation_counts),
            'tab_switch_stats': self.tab_switch_detector.get_statistics(),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def _get_status_color(self) -> str:
        """Get status color based on trust score"""
        if self.current_trust_score >= 80:
            return 'green'
        elif self.current_trust_score >= 60:
            return 'yellow'
        else:
            return 'red'
    
    def get_violation_history(self, limit: int = 50) -> List[Dict]:
        """Get violation history"""
        return self.violation_history[-limit:]
    
    def export_session_data(self) -> Dict:
        """Export complete session data for database storage"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'exam_id': self.exam_id,
            'trust_score': self.current_trust_score,
            'initial_score': 100,
            'final_score': self.current_trust_score,
            'violations': self.violation_history,
            'tab_switch_count': self.tab_switch_detector.tab_switch_count,
            'suspicious_activity_count': self.tab_switch_detector.suspicious_activity_count,
            'frames_processed': self.frames_processed,
            'session_duration': time.time() - self.last_frame_time if self.frames_processed > 0 else 0,
            'exported_at': datetime.utcnow().isoformat()
        }

# Global proctoring session manager
class ProctoringSessionManager:
    """Manages multiple proctoring sessions"""
    
    def __init__(self):
        self.sessions = {}  # {session_id: AIProctor}
        self.logger = logging.getLogger(__name__)
    
    def create_session(self, user_id: int, exam_id: int) -> int:
        """Create new proctoring session"""
        session_id = int(time.time() * 1000)  # Use timestamp as ID
        
        proctor = AIProctor(session_id, user_id, exam_id)
        self.sessions[session_id] = proctor
        
        self.logger.info(f"Created proctoring session {session_id} for user {user_id}")
        
        return session_id
    
    def get_session(self, session_id: int) -> Optional[AIProctor]:
        """Get proctoring session by ID"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: int) -> bool:
        """Remove proctoring session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.logger.info(f"Removed proctoring session {session_id}")
            return True
        return False
    
    def get_all_sessions(self) -> Dict[int, AIProctor]:
        """Get all active sessions"""
        return self.sessions.copy()
    
    def get_user_session(self, user_id: int) -> Optional[AIProctor]:
        """Get session for specific user"""
        for session in self.sessions.values():
            if session.user_id == user_id and session.session_active:
                return session
        return None

# Global session manager instance
session_manager = ProctoringSessionManager()
