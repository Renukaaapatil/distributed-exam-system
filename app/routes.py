from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db, login_manager, csrf
from app.models import User, Exam, Question, Response, exam_sessions
from app.services import UserService, ExamService, AntiCheatService
from datetime import datetime
import json
import random

main_bp = Blueprint('main', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            user = UserService.authenticate_user(email, password)
            if user:
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('main.dashboard'))
            else:
                flash('Invalid email or password', 'error')
        except Exception as e:
            flash('Login error. Please try again.', 'error')
    
    return render_template('login.html')

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'student')
        
        # SECURITY: Force role to student and validate
        if role != 'student':
            # Log security violation attempt
            import logging
            logging.warning(f"Security violation: User attempted to register with role '{role}' - Email: {email}")
            role = 'student'  # Force to student
        
        # Additional security validation
        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')
        
        try:
            # Always create as student regardless of what was submitted
            user = UserService.create_user(name=name, email=email, password=password, role='student')
            flash('Registration successful! Your student account has been created.', 'success')
            return redirect(url_for('main.login'))
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash('Registration error. Please try again.', 'error')
    
    return render_template('register.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        # Admin dashboard - show comprehensive statistics
        from app.models import ProctoringSession, ProctoringAlert, ProctoringViolation
        
        # Get basic statistics
        users_count = User.query.filter_by(role='student').count()
        exams_count = Exam.query.count()
        questions_count = Question.query.count()
        
        # Get all students for student management
        students = User.query.filter_by(role='student').all()
        
        # Get recent exam attempts
        attempts = Response.query.order_by(Response.started_at.desc()).all()
        
        # Get proctoring data with enhanced metrics
        proctoring_sessions = []
        proctoring_alerts = []
        
        # Initialize metrics with safe defaults
        active_sessions = 0
        violations_count = 0
        avg_trust_score = 100
        high_risk_students = 0
        
        try:
            # Get active sessions (status='active')
            active_sessions_data = db.session.query(
                ProctoringSession, User, Exam
            ).join(
                User, ProctoringSession.user_id == User.id
            ).join(
                Exam, ProctoringSession.exam_id == Exam.id
            ).filter(
                ProctoringSession.status == 'active'
            ).all()
            
            active_sessions = len(active_sessions_data)
            proctoring_sessions = active_sessions_data
            
            # Count all violations
            violations_count = ProctoringViolation.query.count()
            
            # Calculate average trust score safely
            all_sessions_data = ProctoringSession.query.filter(
                ProctoringSession.trust_score.isnot(None)
            ).all()
            
            if all_sessions_data:
                valid_scores = [s.trust_score for s in all_sessions_data if s.trust_score is not None]
                if valid_scores:
                    avg_trust_score = sum(valid_scores) // len(valid_scores)
            
            # Count high risk students (trust_score < 40)
            high_risk_students = ProctoringSession.query.filter(
                ProctoringSession.trust_score < 40,
                ProctoringSession.trust_score.isnot(None)
            ).count()
            
            # Get proctoring alerts
            proctoring_alerts = db.session.query(
                ProctoringAlert, User
            ).join(
                User, ProctoringAlert.user_id == User.id
            ).order_by(
                ProctoringAlert.created_at.desc()
            ).limit(20).all()
            
        except Exception as e:
            current_app.logger.error(f"Error loading proctoring data: {e}")
            # Keep default values if there's an error
        
        return render_template('admin_dashboard.html', 
                             users_count=users_count,
                             exams_count=exams_count,
                             questions_count=questions_count,
                             attempts=attempts,
                             students=students,
                             proctoring_sessions=proctoring_sessions,
                             proctoring_alerts=proctoring_alerts,
                             active_sessions=active_sessions,
                             violations_count=violations_count,
                             avg_trust_score=avg_trust_score,
                             high_risk_students=high_risk_students,
                             current_time=datetime.now())
    else:
        # Student dashboard - show their statistics
        stats = UserService.get_user_stats(current_user.id)
        return render_template('student_dashboard.html', stats=stats)

@main_bp.route('/exams')
@login_required
def exams():
    """List available exams"""
    if current_user.is_admin():
        flash('Admins cannot take exams.', 'error')
        return redirect(url_for('main.dashboard'))
    
    exams = ExamService.get_active_exams()
    return render_template('exams.html', exams=exams)

@main_bp.route('/exam/<int:exam_id>', methods=['GET'])
@csrf.exempt
@login_required
def take_exam(exam_id):
    """Take an exam"""
    if current_user.is_admin():
        flash('Admins cannot take exams.', 'error')
        return redirect(url_for('main.dashboard'))
    
    exam = Exam.query.get_or_404(exam_id)
    
    # Check if user has already taken this exam
    existing_response = Response.query.filter_by(
        user_id=current_user.id, 
        exam_id=exam_id
    ).first()
    
    if existing_response:
        flash('You have already taken this exam.', 'warning')
        return redirect(url_for('main.results', response_id=existing_response.id))
    
    # Randomize questions
    questions = exam.questions[:]
    random.shuffle(questions)
    
        
    # Check if proctoring is enabled for this exam
    enable_proctoring = exam.enable_proctoring if hasattr(exam, 'enable_proctoring') else True
    
    # Validate exam exists
    if not exam:
        flash('Exam not found.', 'error')
        return redirect(url_for('main.exams'))
    
    # Validate exam has questions
    if not exam.questions:
        flash('Exam has no questions available.', 'error')
        return redirect(url_for('main.exams'))
    
    try:
        # Start exam session
        session_data = ExamService.start_exam_session(current_user.id, exam_id)
        
        # Generate anti-cheat token
        token = AntiCheatService.generate_exam_token(current_user.id, exam_id)
        session_data['token'] = token
        
        return render_template('exam.html', 
                             exam=exam, 
                             questions=questions,
                             duration=session_data['duration'],
                             token=token,
                             started_at=session_data['started_at'],
                             enable_proctoring=enable_proctoring,
                             response_id=session_data.get('response_id'),
                             current_time=datetime.now())
    
    except ValueError as e:
        print("ERROR (ValueError):", e)
        flash(str(e), 'error')
        return redirect(url_for('main.exams'))
    except Exception as e:
        print("ERROR (Exception):", e)
        flash(f'Error starting exam: {str(e)}', 'error')
        return redirect(url_for('main.exams'))

@main_bp.route('/save_answer', methods=['POST'])
@login_required
def save_answer():
    """Save answer during exam (AJAX endpoint)"""
    if current_user.is_admin():
        return jsonify({'error': 'Admins cannot take exams'}), 403
    
    exam_id = request.json.get('exam_id')
    question_id = request.json.get('question_id')
    answer = request.json.get('answer')
    token = request.json.get('token')
    
    # Validate token
    if not AntiCheatService.validate_exam_session(current_user.id, exam_id, token):
        AntiCheatService.detect_suspicious_activity(current_user.id, exam_id, 'invalid_token')
        return jsonify({'error': 'Invalid session'}), 403
    
    try:
        session_data = ExamService.save_exam_answer(current_user.id, exam_id, question_id, answer)
        return jsonify({'success': True, 'answers_saved': len(session_data['answers'])})
    
    except ValueError as e:
        if 'Time is up' in str(e):
            return jsonify({'error': 'time_up', 'message': str(e)}), 400
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Error saving answer'}), 500

@main_bp.route('/submit_exam', methods=['POST'])
@csrf.exempt
@login_required
def submit_exam():
    """Submit exam and calculate score"""
    print("FORM DATA:", request.form)
    if current_user.is_admin():
        flash('Admins cannot submit exams', 'error')
        return redirect(url_for('main.exams'))
    
    exam_id = request.form.get('exam_id')
    
    # Validate exam exists
    if not exam_id:
        flash('Exam ID is required', 'error')
        return redirect(url_for('main.exams'))
    
    exam = Exam.query.get(exam_id)
    if not exam:
        flash('Exam not found', 'error')
        return redirect(url_for('main.exams'))
    
    try:
        # Collect answers from form
        answers = {}
        for key in request.form:
            if key.startswith('question_'):
                question_id = key.replace('question_', '')
                answers[question_id] = request.form[key]
        
        # Simple score calculation
        score = 0
        total_questions = 0
        correct_answers = {}
        
        for question in exam.questions:
            total_questions += 1
            question_id = str(question.id)
            user_answer = answers.get(question_id)
            
            if user_answer == str(question.correct_answer):
                score += 1
                correct_answers[question_id] = True
            else:
                correct_answers[question_id] = False
        
        # Save to database
        response = Response(
            user_id=current_user.id,
            exam_id=exam_id,
            answers=json.dumps(answers),
            score=score,
            started_at=datetime.now(),
            submitted_at=datetime.now()
        )
        db.session.add(response)
        db.session.commit()
        
        # Add result to blockchain for tamper-proof storage
        try:
            from app.blockchain_routes import add_exam_result_to_blockchain
            
            additional_data = {
                'total_questions': total_questions,
                'correct_answers': score,
                'percentage': round((score / total_questions) * 100, 1) if total_questions > 0 else 0,
                'exam_duration': exam.duration,
                'response_id': response.id,
                'submission_time': datetime.now().isoformat()
            }
            
            blockchain_success = add_exam_result_to_blockchain(
                current_user.id, 
                exam_id, 
                score, 
                additional_data
            )
            
            if blockchain_success:
                print("Block added successfully - Exam result stored in blockchain")
            else:
                print("Warning: Failed to store exam result in blockchain")
                
        except Exception as e:
            print(f"Blockchain integration error: {e}")
        
        # Flash success message
        percentage = round((score / total_questions) * 100, 1) if total_questions > 0 else 0
        flash(f'Exam submitted successfully! Your score: {score}/{total_questions} ({percentage}%)', 'success')
        
        # Redirect to results page
        return redirect(url_for('main.results', response_id=response.id))
    
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('main.exams'))
    except Exception as e:
        flash(f'Error submitting exam: {str(e)}', 'error')
        return redirect(url_for('main.exams'))

@main_bp.route('/results/<int:response_id>')
@login_required
def results(response_id):
    """View exam results"""
    result_data = ExamService.get_exam_results(response_id)
    
    if not result_data:
        flash('Results not found.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check permissions
    response = result_data['response']
    if not current_user.is_admin() and response.user_id != current_user.id:
        flash('You do not have permission to view these results.', 'error')
        return redirect(url_for('main.dashboard'))
    
    return render_template('results.html', **result_data)

@main_bp.route('/api/live_dashboard_data')
@login_required
def live_dashboard_data():
    """API endpoint for live dashboard data"""
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Get active proctoring sessions
        active_sessions = ProctoringSession.query.filter_by(status='active').all()
        
        # Get recent violations
        violations = ProctoringViolation.query.order_by(ProctoringViolation.created_at.desc()).limit(10).all()
        
        # Get student data
        students = []
        node_distribution = {'A': 0, 'B': 0, 'C': 0}
        
        for session in active_sessions:
            user = User.query.get(session.user_id)
            if user:
                # Calculate progress based on responses
                total_questions = Question.query.filter_by(exam_id=session.exam_id).count()
                answered_questions = Response.query.filter_by(
                    user_id=session.user_id, 
                    exam_id=session.exam_id
                ).count()
                progress = (answered_questions / total_questions * 100) if total_questions > 0 else 0
                
                # Determine status based on trust score and violations
                status = 'active'
                if session.trust_score < 50:
                    status = 'cheating'
                elif session.trust_score < 80:
                    status = 'suspicious'
                
                # Get node assignment (simplified - in real system, this would come from cluster manager)
                node = chr(65 + (session.user_id % 3))  # A, B, or C
                node_distribution[node] += 1
                
                students.append({
                    'id': session.user_id,
                    'name': user.name,
                    'email': user.email,
                    'trust_score': session.trust_score,
                    'node': node,
                    'status': status,
                    'progress': round(progress, 1),
                    'session_id': session.id,
                    'exam_id': session.exam_id,
                    'last_activity': session.last_updated.isoformat() if session.last_updated else None
                })
        
        # Get webcam snapshots (latest from each active session)
        webcam_snapshots = []
        for session in active_sessions[:6]:  # Limit to 6 recent snapshots
            snapshots = ProctoringSnapshot.query.filter_by(
                session_id=session.id
            ).order_by(ProctoringSnapshot.created_at.desc()).limit(1).first()
            
            if snapshots:
                user = User.query.get(session.user_id)
                webcam_snapshots.append({
                    'student_id': session.user_id,
                    'student_name': user.name if user else 'Unknown',
                    'image_url': snapshots.get_image_url(),
                    'timestamp': snapshots.created_at.isoformat(),
                    'status': 'active'
                })
        
        return jsonify({
            'active_sessions': len(active_sessions),
            'violations': [
                {
                    'id': v.id,
                    'student_id': v.session.user_id if v.session else None,
                    'student_name': v.session.user.name if v.session and v.session.user else 'Unknown',
                    'violation_type': v.violation_type,
                    'severity': v.severity,
                    'timestamp': v.created_at.isoformat(),
                    'details': v.details
                } for v in violations
            ],
            'students': students,
            'node_distribution': node_distribution,
            'webcam_snapshots': webcam_snapshots,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching live dashboard data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/sessions')
@login_required
def sessions():
    """Show active exam sessions"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    from app.models import ProctoringSession
    
    try:
        # Get active sessions with related data
        active_sessions_data = db.session.query(
            ProctoringSession, User, Exam
        ).join(
            User, ProctoringSession.user_id == User.id
        ).join(
            Exam, ProctoringSession.exam_id == Exam.id
        ).filter(
            ProctoringSession.status == 'active'
        ).order_by(
            ProctoringSession.started_at.desc()
        ).all()
        
        return render_template('sessions.html', sessions=active_sessions_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading sessions: {e}")
        flash('Error loading session data.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/violations')
@login_required
def violations():
    """Show all cheating violations"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    from app.models import ProctoringViolation
    
    try:
        # Get all violations with related data
        violations_data = db.session.query(
            ProctoringViolation, User, Exam, ProctoringSession
        ).join(
            ProctoringSession, ProctoringViolation.session_id == ProctoringSession.id
        ).join(
            User, ProctoringViolation.user_id == User.id
        ).join(
            Exam, ProctoringSession.exam_id == Exam.id
        ).order_by(
            ProctoringViolation.detected_at.desc()
        ).all()
        
        return render_template('violations.html', violations=violations_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading violations: {e}")
        flash('Error loading violation data.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/high_risk')
@login_required
def high_risk():
    """Show students with trust score < 40"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    from app.models import ProctoringSession
    
    try:
        # Get high risk students (trust_score < 40)
        high_risk_data = db.session.query(
            ProctoringSession, User, Exam
        ).join(
            User, ProctoringSession.user_id == User.id
        ).join(
            Exam, ProctoringSession.exam_id == Exam.id
        ).filter(
            ProctoringSession.trust_score < 40,
            ProctoringSession.trust_score.isnot(None)
        ).order_by(
            ProctoringSession.trust_score.asc()
        ).all()
        
        return render_template('high_risk.html', high_risk_students=high_risk_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading high risk students: {e}")
        flash('Error loading high risk data.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/trust_scores')
@login_required
def trust_scores():
    """Show all student trust scores"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    from app.models import ProctoringSession
    
    try:
        # Get all trust scores with related data
        trust_scores_data = db.session.query(
            ProctoringSession, User, Exam
        ).join(
            User, ProctoringSession.user_id == User.id
        ).join(
            Exam, ProctoringSession.exam_id == Exam.id
        ).filter(
            ProctoringSession.trust_score.isnot(None)
        ).order_by(
            ProctoringSession.trust_score.desc()
        ).all()
        
        return render_template('trust_scores.html', trust_scores=trust_scores_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading trust scores: {e}")
        flash('Error loading trust score data.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/detect_voice_violation', methods=['POST'])
@login_required
def detect_voice_violation():
    """Handle voice violation detection from frontend"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        user_id = data.get('user_id')
        exam_id = data.get('exam_id')
        volume_level = data.get('volume_level')
        timestamp = data.get('timestamp')
        
        if not all([user_id, exam_id, volume_level is not None]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Get or create proctoring session
        from app.models import ProctoringSession, ProctoringViolation
        
        session = ProctoringSession.query.filter_by(
            user_id=current_user.id,
            exam_id=exam_id,
            status='active'
        ).first()
        
        if not session:
            return jsonify({'error': 'No active session found'}), 404
        
        # Reduce trust score
        trust_score_penalty = 10
        old_score = session.trust_score or 100
        new_score = max(0, old_score - trust_score_penalty)
        
        session.trust_score = new_score
        session.last_updated = datetime.utcnow()
        
        # Create violation record
        violation = ProctoringViolation(
            session_id=session.id,
            user_id=current_user.id,
            violation_type='voice_detected',
            severity='medium',
            details=f'Student speaking detected - Volume level: {volume_level:.2f}',
            trust_score_before=old_score,
            trust_score_after=new_score,
            score_penalty=trust_score_penalty
        )
        
        db.session.add(violation)
        db.session.commit()
        
        # Check if user becomes high risk
        is_high_risk = new_score < 40
        
        return jsonify({
            'success': True,
            'old_trust_score': old_score,
            'new_trust_score': new_score,
            'is_high_risk': is_high_risk,
            'violation_id': violation.id,
            'message': 'Voice violation recorded successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error processing voice violation: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/questions')
@login_required
def questions():
    """Question management page for admins"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    from app.models import Question, Exam
    
    # Get filter parameters
    exam_filter = request.args.get('exam_filter', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = Question.query
    
    if exam_filter:
        query = query.filter(Question.exam_id == exam_filter)
    
    if search:
        query = query.filter(Question.text.contains(search))
    
    # Paginate results
    questions = query.order_by(Question.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get all exams for filter dropdown
    exams = Exam.query.all()
    
    return render_template('questions.html', 
                     questions=questions, 
                     exams=exams,
                     current_filter=exam_filter,
                     search_term=search)

@main_bp.route('/questions/create', methods=['GET', 'POST'])
@login_required
def create_question():
    """Create a new question"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    from app.models import Question, Exam
    
    if request.method == 'POST':
        try:
            question = Question(
                text=request.form.get('text'),
                option1=request.form.get('option1'),
                option2=request.form.get('option2'),
                option3=request.form.get('option3'),
                option4=request.form.get('option4'),
                correct_answer=int(request.form.get('correct_answer')),
                exam_id=int(request.form.get('exam_id'))
            )
            
            db.session.add(question)
            db.session.commit()
            
            flash('Question created successfully!', 'success')
            return redirect(url_for('main.questions'))
            
        except Exception as e:
            current_app.logger.error(f"Error creating question: {e}")
            flash('Error creating question. Please check your input.', 'error')
    
    exams = Exam.query.all()
    return render_template('create_question.html', exams=exams)

@main_bp.route('/questions/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    """Edit an existing question"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    from app.models import Question, Exam
    
    question = Question.query.get_or_404(question_id)
    exams = Exam.query.all()
    
    if request.method == 'POST':
        try:
            question.text = request.form.get('text')
            question.option1 = request.form.get('option1')
            question.option2 = request.form.get('option2')
            question.option3 = request.form.get('option3')
            question.option4 = request.form.get('option4')
            question.correct_answer = int(request.form.get('correct_answer'))
            question.exam_id = int(request.form.get('exam_id'))
            
            db.session.commit()
            
            flash('Question updated successfully!', 'success')
            return redirect(url_for('main.questions'))
            
        except Exception as e:
            current_app.logger.error(f"Error updating question: {e}")
            flash('Error updating question. Please check your input.', 'error')
    
    return render_template('edit_question.html', question=question, exams=exams)

@main_bp.route('/questions/<int:question_id>/delete', methods=['POST'])
@login_required
def delete_question(question_id):
    """Delete a question"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    from app.models import Question
    
    question = Question.query.get_or_404(question_id)
    
    try:
        db.session.delete(question)
        db.session.commit()
        flash('Question deleted successfully!', 'success')
    except Exception as e:
        current_app.logger.error(f"Error deleting question: {e}")
        flash('Error deleting question.', 'error')
    
    return redirect(url_for('main.questions'))

@main_bp.route('/log_violation', methods=['POST'])
@login_required
def log_violation():
    """Log violation attempts from frontend"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        violation_type = data.get('violation_type')
        details = data.get('details')
        exam_id = data.get('exam_id')
        
        if not all([violation_type, exam_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Log violation for monitoring
        current_app.logger.warning(f"Violation detected: {violation_type} - User: {current_user.id} - Exam: {exam_id} - Details: {details}")
        
        # You can optionally store violations in database here
        # For now, just log and return success
        
        return jsonify({
            'success': True,
            'message': 'Violation logged successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error logging violation: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/questions/generate-test', methods=['POST'])
@login_required
def generate_test_questions():
    """Generate test questions for demo purposes"""
    if not current_user.is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from app.models import Question, Exam
        import random
        
        # Get or create a default exam for test questions
        exam = Exam.query.filter_by(title='Test Questions').first()
        if not exam:
            exam = Exam(
                title='Test Questions',
                duration=30,
                is_active=True
            )
            db.session.add(exam)
            db.session.commit()
        
        # Sample test questions
        test_questions = [
            {
                'text': 'What is the capital of France?',
                'options': ['London', 'Berlin', 'Paris', 'Madrid'],
                'correct': 2
            },
            {
                'text': 'What is 2 + 2?',
                'options': ['3', '4', '5', '6'],
                'correct': 1
            },
            {
                'text': 'Which programming language is known as the "language of the web"?',
                'options': ['Python', 'JavaScript', 'Java', 'C++'],
                'correct': 1
            },
            {
                'text': 'What does HTML stand for?',
                'options': [
                    'Hyper Text Markup Language',
                    'High Tech Modern Language',
                    'Home Tool Markup Language',
                    'Hyperlinks and Text Markup Language'
                ],
                'correct': 0
            },
            {
                'text': 'What is the largest planet in our solar system?',
                'options': ['Earth', 'Mars', 'Jupiter', 'Saturn'],
                'correct': 2
            }
        ]
        
        created_count = 0
        for q_data in test_questions:
            # Check if question already exists
            existing = Question.query.filter_by(text=q_data['text']).first()
            if not existing:
                question = Question(
                    text=q_data['text'],
                    option1=q_data['options'][0],
                    option2=q_data['options'][1],
                    option3=q_data['options'][2],
                    option4=q_data['options'][3],
                    correct_answer=q_data['correct'],
                    exam_id=exam.id
                )
                db.session.add(question)
                created_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Generated {created_count} test questions successfully',
            'created_count': created_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating test questions: {e}")
        return jsonify({'error': 'Failed to generate test questions'}), 500

@main_bp.route('/api/terminate_all_exams', methods=['POST'])
@login_required
def terminate_all_exams():
    """Terminate all active exam sessions"""
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Terminate all active sessions
        active_sessions = ProctoringSession.query.filter_by(status='active').all()
        for session in active_sessions:
            session.status = 'terminated'
            session.ended_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Terminated {len(active_sessions)} active sessions'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error terminating all exams: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/api/mark_suspicious', methods=['POST'])
@login_required
def mark_suspicious():
    """Mark student as suspicious"""
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        
        if student_id:
            session = ProctoringSession.query.filter_by(
                user_id=student_id, 
                status='active'
            ).first()
            
            if session:
                # Reduce trust score for suspicious activity
                session.trust_score = max(0, session.trust_score - 15)
                session.last_updated = datetime.utcnow()
                
                # Create violation record
                violation = ProctoringViolation(
                    session_id=session.id,
                    violation_type='admin_flagged',
                    severity='medium',
                    details='Flagged as suspicious by admin'
                )
                db.session.add(violation)
                db.session.commit()
                
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Active session not found'}), 404
        else:
            return jsonify({'error': 'Student ID required'}), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking student as suspicious: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/api/reassign_node', methods=['POST'])
@login_required
def reassign_node():
    """Reassign student to different node"""
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        new_node = data.get('new_node')
        
        if student_id and new_node and new_node in ['A', 'B', 'C']:
            session = ProctoringSession.query.filter_by(
                user_id=student_id, 
                status='active'
            ).first()
            
            if session:
                # In a real system, this would communicate with the cluster manager
                # For now, we'll just update a metadata field
                if not hasattr(session, 'metadata'):
                    session.metadata = '{}'
                
                import json
                metadata = json.loads(session.metadata) if session.metadata else {}
                metadata['assigned_node'] = new_node
                session.metadata = json.dumps(metadata)
                session.last_updated = datetime.utcnow()
                
                db.session.commit()
                
                return jsonify({'success': True, 'new_node': new_node})
            else:
                return jsonify({'error': 'Active session not found'}), 404
        else:
            return jsonify({'error': 'Student ID and valid node required'}), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error reassigning node: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/api/terminate_student', methods=['POST'])
@login_required
def terminate_student():
    """Terminate specific student's exam"""
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        
        if student_id:
            session = ProctoringSession.query.filter_by(
                user_id=student_id, 
                status='active'
            ).first()
            
            if session:
                session.status = 'terminated'
                session.ended_at = datetime.utcnow()
                
                # Create violation record
                violation = ProctoringViolation(
                    session_id=session.id,
                    violation_type='exam_terminated',
                    severity='high',
                    details='Exam terminated by administrator'
                )
                db.session.add(violation)
                db.session.commit()
                
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Active session not found'}), 404
        else:
            return jsonify({'error': 'Student ID required'}), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error terminating student exam: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Initialize default data
def init_default_data():
    """Initialize default exam and admin user"""
    ExamService.initialize_default_exam()
    ExamService.initialize_admin_user()
