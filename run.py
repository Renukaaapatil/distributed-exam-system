#!/usr/bin/env python3
"""
Distributed Exam System - Main Entry Point
"""

import os
import sys
from app import create_app, db
from core.node import Node, NodeCluster

def main():
    # Create the Flask app
    config_name = os.environ.get('FLASK_ENV', 'development')
    app = create_app(config_name)
    
    # Get configuration
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print("=" * 60)
    print("Distributed Exam System")
    print("=" * 60)
    print(f"Server running on: http://{host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"Environment: {config_name}")
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("=" * 60)
    print("\nDemo Credentials:")
    print("  Admin: email='admin@example.com', password='admin123'")
    print("  Student: Register a new account")
    print("\nDefault admin account and sample exam will be created automatically.")
    print("=" * 60)
    
    # Start the Flask application
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
