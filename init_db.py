#!/usr/bin/env python3
"""
Database Initialization Script
"""

import os
import sys
from app import create_app, db
from app.models import User, Exam, Question, Response, ProctoringSession, ProctoringViolation, ProctoringAlert
from app.services import UserService, ExamService

def init_database():
    """Initialize database with all tables"""
    app = create_app('development')
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")
        
        print("Initializing default data...")
        # Create default admin user
        try:
            admin_user = UserService.create_user(
                name='Admin User',
                email='admin@example.com',
                password='admin123',
                role='admin'
            )
            print(f"Created admin user: {admin_user.email}")
        except Exception as e:
            print(f"Admin user may already exist: {e}")
        
        # Initialize default exam
        try:
            ExamService.initialize_default_exam()
            print("Default exam initialized successfully!")
        except Exception as e:
            print(f"Default exam may already exist: {e}")
        
        print("Database initialization complete!")

if __name__ == '__main__':
    init_database()
