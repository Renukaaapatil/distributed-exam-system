#!/usr/bin/env python3
"""
Database Schema Update Script
Updates the database to include new columns and tables for adaptive exams, blockchain, and sync features
"""

import sqlite3
import sys
from pathlib import Path

def update_database_schema():
    """Update database schema with new columns and tables"""
    db_path = "instance/exam_system.db"
    
    if not Path(db_path).exists():
        print(f"Database file {db_path} not found")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add difficulty column to questions table
        try:
            cursor.execute("ALTER TABLE questions ADD COLUMN difficulty INTEGER DEFAULT 2")
            print("Added difficulty column to questions table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Difficulty column already exists in questions table")
            else:
                print(f"Error adding difficulty column: {e}")
        
        # Create sync_logs table
        try:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sync_type VARCHAR(50) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                data_received TEXT,
                error_message TEXT,
                records_processed INTEGER DEFAULT 0,
                client_timestamp DATETIME,
                server_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            print("Created sync_logs table")
        except sqlite3.OperationalError as e:
            print(f"Error creating sync_logs table: {e}")
        
        # Create blockchain_blocks table
        try:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS blockchain_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_index INTEGER NOT NULL UNIQUE,
                timestamp DATETIME NOT NULL,
                user_id INTEGER NOT NULL,
                exam_id INTEGER NOT NULL,
                score REAL NOT NULL,
                previous_hash VARCHAR(64) NOT NULL,
                current_hash VARCHAR(64) NOT NULL UNIQUE,
                block_data TEXT DEFAULT '{}'
            )
            ''')
            print("Created blockchain_blocks table")
        except sqlite3.OperationalError as e:
            print(f"Error creating blockchain_blocks table: {e}")
        
        # Add foreign key constraints (if not already present)
        try:
            # Note: SQLite doesn't support adding foreign key constraints to existing tables
            # The constraints are handled at the application level
            print("Foreign key constraints handled at application level")
        except sqlite3.OperationalError as e:
            print(f"Error with foreign keys: {e}")
        
        conn.commit()
        conn.close()
        
        print("Database schema updated successfully!")
        return True
        
    except Exception as e:
        print(f"Error updating database schema: {e}")
        return False

if __name__ == "__main__":
    success = update_database_schema()
    sys.exit(0 if success else 1)
