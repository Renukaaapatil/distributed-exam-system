#!/usr/bin/env python3
"""
Database migration script for Flask-Migrate
"""

import os
import sys
from app import create_app, db
from flask_migrate import init, migrate, upgrade

def init_migrations():
    """Initialize Flask-Migrate"""
    app = create_app()
    with app.app_context():
        init()

def create_migration():
    """Create a new migration"""
    app = create_app()
    with app.app_context():
        migrate()

def apply_migrations():
    """Apply all migrations"""
    app = create_app()
    with app.app_context():
        upgrade()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python migrate.py [init|migration|upgrade]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'init':
        init_migrations()
        print("Flask-Migrate initialized")
    elif command == 'migration':
        create_migration()
        print("Migration created")
    elif command == 'upgrade':
        apply_migrations()
        print("Migrations applied")
    else:
        print("Unknown command. Use: init, migration, or upgrade")
        sys.exit(1)
