from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import uuid
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'student' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    responses = db.relationship('Response', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.name}>'

class Exam(db.Model):
    __tablename__ = 'exams'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # Duration in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    questions = db.relationship('Question', backref='exam', lazy=True, cascade='all, delete-orphan')
    responses = db.relationship('Response', backref='exam', lazy=True)
    
    def __repr__(self):
        return f'<Exam {self.title}>'

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.Text, nullable=False)
    option2 = db.Column(db.Text, nullable=False)
    option3 = db.Column(db.Text, nullable=False)
    option4 = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', or 'D'
    difficulty = db.Column(db.Integer, default=2)  # 1=Easy, 2=Medium, 3=Hard
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_options(self):
        """Return options as a dictionary"""
        return {
            'A': self.option1,
            'B': self.option2,
            'C': self.option3,
            'D': self.option4
        }
    
    def get_difficulty_name(self):
        """Get difficulty level name"""
        difficulty_map = {
            1: 'Easy',
            2: 'Medium', 
            3: 'Hard'
        }
        return difficulty_map.get(self.difficulty, 'Unknown')
    
    def get_score_weight(self):
        """Get score weight based on difficulty"""
        weight_map = {
            1: 1,  # Easy = 1 point
            2: 2,  # Medium = 2 points
            3: 3   # Hard = 3 points
        }
        return weight_map.get(self.difficulty, 2)
    
    def __repr__(self):
        return f'<Question {self.id} - {self.get_difficulty_name()}>'

class Response(db.Model):
    __tablename__ = 'responses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    answers = db.Column(db.Text, nullable=False)  # JSON string of answers
    score = db.Column(db.Integer, nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Proctoring session relationship
    proctoring_session_id = db.Column(db.Integer, db.ForeignKey('proctoring_session.id'))
    
    proctoring_session = db.relationship(
        "ProctoringSession",
        backref="responses"   # unique name
    )
    
    def get_answers(self):
        """Parse answers from JSON string"""
        return json.loads(self.answers) if self.answers else {}
    
    def set_answers(self, answers_dict):
        """Store answers as JSON string"""
        self.answers = json.dumps(answers_dict)
    
    def __repr__(self):
        return f'<Response {self.id} - User: {self.user.name} - Score: {self.score}>'

class ProctoringSession(db.Model):
    """Proctoring session for monitoring exam attempts"""
    __tablename__ = 'proctoring_session'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    
    # Trust score (0-100)
    trust_score = db.Column(db.Integer, default=100)
    initial_score = db.Column(db.Integer, default=100)
    final_score = db.Column(db.Integer)
    
    # Session status
    status = db.Column(db.String(20), default='active')  # active, completed, flagged
    
    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('proctoring_sessions', lazy=True))
    exam = db.relationship('Exam', backref=db.backref('proctoring_sessions', lazy=True))
    violations = db.relationship('ProctoringViolation', backref="parent_session")
    alerts = db.relationship('ProctoringAlert', back_populates="session")
    
    def update_trust_score(self, new_score):
        """Update trust score and log the change"""
        old_score = self.trust_score
        self.trust_score = new_score
        self.last_updated = datetime.utcnow()
        
        # Create a violation log if score decreased
        if new_score < old_score:
            violation = ProctoringViolation(
                session_id=self.id,
                user_id=self.user_id,
                violation_type='trust_score_decrease',
                severity='medium' if new_score >= 70 else 'high',
                details=f'Trust score decreased from {old_score} to {new_score}',
                trust_score_before=old_score,
                trust_score_after=new_score
            )
            db.session.add(violation)
    
    def get_status_color(self):
        """Get color code based on trust score"""
        if self.trust_score >= 80:
            return 'green'  # Safe
        elif self.trust_score >= 60:
            return 'yellow'  # Warning
        else:
            return 'red'  # Cheating

class ProctoringViolation(db.Model):
    """Record of proctoring violations"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('proctoring_session.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Violation details
    violation_type = db.Column(db.String(50), nullable=False)  # no_face, multiple_faces, tab_switch, etc.
    severity = db.Column(db.String(20), nullable=False)  # low, medium, high, critical
    
    # Description and evidence
    details = db.Column(db.Text)
    evidence_data = db.Column(db.Text)  # JSON string with additional evidence
    
    # Trust score impact
    trust_score_before = db.Column(db.Integer)
    trust_score_after = db.Column(db.Integer)
    score_penalty = db.Column(db.Integer, default=0)
    
    # Timestamps
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('proctoring_violations', lazy=True))
    alerts = db.relationship('ProctoringAlert', back_populates="violation")
    
    def get_evidence(self):
        """Get evidence data as dictionary"""
        if self.evidence_data:
            return json.loads(self.evidence_data)
        return {}
    
    def set_evidence(self, evidence_dict):
        """Set evidence data from dictionary"""
        self.evidence_data = json.dumps(evidence_dict)

class ProctoringAlert(db.Model):
    """Alerts sent to admin dashboard"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('proctoring_session.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    violation_id = db.Column(db.Integer, db.ForeignKey('proctoring_violation.id'), nullable=True)
    
    # Alert details
    alert_type = db.Column(db.String(50), nullable=False)  # violation, low_score, etc.
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # info, warning, critical
    
    # Status
    status = db.Column(db.String(20), default='unread')  # unread, read, resolved
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    session = db.relationship('ProctoringSession', back_populates="alerts")
    user = db.relationship('User', backref=db.backref('proctoring_alerts', lazy=True))
    violation = db.relationship('ProctoringViolation', back_populates="alerts")
    
    def __repr__(self):
        return f'<ProctoringAlert {self.id} - User: {self.user.name} - Severity: {self.severity}>'

class ExamSession(db.Model):
    """Exam session for fault-tolerant distributed system"""
    __tablename__ = 'exam_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    
    # Session tracking
    node_id = db.Column(db.String(20), nullable=False)  # Which node is handling this session
    current_question_index = db.Column(db.Integer, default=0)
    
    # Exam data
    answers = db.Column(db.Text, default='{}')  # JSON string of answers
    remaining_time = db.Column(db.Integer, default=1800)  # Time in seconds (30 minutes default)
    
    # Status and timestamps
    status = db.Column(db.String(20), default='active')  # active, paused, completed, failed
    last_saved = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('exam_sessions', lazy=True))
    exam = db.relationship('Exam', backref=db.backref('exam_sessions', lazy=True))
    
    def get_answers(self):
        """Get answers as dictionary"""
        try:
            return json.loads(self.answers) if self.answers else {}
        except json.JSONDecodeError:
            return {}
    
    def set_answers(self, answers_dict):
        """Set answers from dictionary"""
        self.answers = json.dumps(answers_dict)
    
    def get_answer(self, question_id):
        """Get answer for specific question"""
        answers = self.get_answers()
        return answers.get(str(question_id))
    
    def set_answer(self, question_id, answer):
        """Set answer for specific question"""
        answers = self.get_answers()
        answers[str(question_id)] = answer
        self.set_answers(answers)
        self.last_saved = datetime.utcnow()
    
    def update_progress(self, question_index, answers_dict, remaining_time):
        """Update session progress"""
        self.current_question_index = question_index
        self.set_answers(answers_dict)
        self.remaining_time = remaining_time
        self.updated_at = datetime.utcnow()
        self.last_saved = datetime.utcnow()
    
    def to_dict(self):
        """Convert session to dictionary"""
        return {
            'session_id': self.id,
            'user_id': self.user_id,
            'exam_id': self.exam_id,
            'node_id': self.node_id,
            'current_question_index': self.current_question_index,
            'answers': self.get_answers(),
            'remaining_time': self.remaining_time,
            'status': self.status,
            'last_saved': self.last_saved.isoformat() if self.last_saved else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<ExamSession {self.id} - User: {self.user_id} - Exam: {self.exam_id}>'

class Snapshot(db.Model):
    """Webcam snapshot for student monitoring"""
    __tablename__ = 'snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('exam_sessions.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    image_filename = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer)
    
    # Metadata
    violation_detected = db.Column(db.Boolean, default=False)
    violation_type = db.Column(db.String(50))
    confidence_score = db.Column(db.Float)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    session = db.relationship('ExamSession', backref=db.backref('snapshots', lazy=True, cascade='all, delete-orphan'))
    
    def to_dict(self):
        """Convert snapshot to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'image_path': self.image_path,
            'image_filename': self.image_filename,
            'file_size': self.file_size,
            'violation_detected': self.violation_detected,
            'violation_type': self.violation_type,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def get_image_url(self):
        """Get URL for accessing the image"""
        return f"/uploads/snapshots/{self.image_filename}"
    
    def __repr__(self):
        return f'<Snapshot {self.id} - Session: {self.session_id}>'

class BlockchainBlock(db.Model):
    """Database model for storing blockchain blocks"""
    __tablename__ = 'blockchain_blocks'
    
    id = db.Column(db.Integer, primary_key=True)
    block_index = db.Column(db.Integer, nullable=False, unique=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    previous_hash = db.Column(db.String(64), nullable=False)
    current_hash = db.Column(db.String(64), nullable=False, unique=True)
    block_data = db.Column(db.Text, default='{}')  # JSON string
    
    # Relationships
    user = db.relationship('User', backref=db.backref('blockchain_blocks', lazy=True))
    exam = db.relationship('Exam', backref=db.backref('blockchain_blocks', lazy=True))
    
    def get_data(self):
        """Get block data as dictionary"""
        try:
            return json.loads(self.block_data) if self.block_data else {}
        except json.JSONDecodeError:
            return {}
    
    def set_data(self, data_dict):
        """Set block data from dictionary"""
        self.block_data = json.dumps(data_dict)
    
    def to_dict(self):
        """Convert block to dictionary"""
        return {
            'id': self.id,
            'index': self.block_index,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'exam_id': self.exam_id,
            'score': self.score,
            'previous_hash': self.previous_hash,
            'current_hash': self.current_hash,
            'data': self.get_data()
        }
    
    def to_block_object(self):
        """Convert to Block object from blockchain.py"""
        from app.blockchain import Block
        return Block(
            index=self.block_index,
            timestamp=self.timestamp,
            user_id=self.user_id,
            exam_id=self.exam_id,
            score=self.score,
            previous_hash=self.previous_hash,
            data=self.get_data()
        )
    
    @staticmethod
    def from_block_object(block):
        """Create BlockchainBlock from Block object"""
        db_block = BlockchainBlock(
            block_index=block.index,
            timestamp=block.timestamp,
            user_id=block.user_id,
            exam_id=block.exam_id,
            score=block.score,
            previous_hash=block.previous_hash,
            current_hash=block.current_hash
        )
        db_block.set_data(block.data)
        return db_block
    
    def __repr__(self):
        return f'<BlockchainBlock {self.block_index} - User: {self.user_id} - Exam: {self.exam_id}>'

class SyncLog(db.Model):
    """Database model for tracking offline synchronization events"""
    __tablename__ = 'sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sync_type = db.Column(db.String(50), nullable=False)  # exam_answers, exam_metadata, exam_progress
    status = db.Column(db.String(20), default='pending')  # pending, success, error
    data_received = db.Column(db.Text)  # JSON data received from client
    error_message = db.Column(db.Text)  # Error details if sync failed
    records_processed = db.Column(db.Integer, default=0)  # Number of records processed
    client_timestamp = db.Column(db.DateTime)  # Timestamp from client
    server_timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Server timestamp
    
    # Relationships
    user = db.relationship('User', backref=db.backref('sync_logs', lazy=True))
    
    def to_dict(self):
        """Convert sync log to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'sync_type': self.sync_type,
            'status': self.status,
            'data_received': self.data_received,
            'error_message': self.error_message,
            'records_processed': self.records_processed,
            'client_timestamp': self.client_timestamp.isoformat() if self.client_timestamp else None,
            'server_timestamp': self.server_timestamp.isoformat() if self.server_timestamp else None
        }
    
    def __repr__(self):
        return f'<SyncLog {self.id} - {self.sync_type} - {self.status}>'

# Temporary in-memory storage for active exam sessions (as requested)
exam_sessions = {}
