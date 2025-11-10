import mysql.connector
from mysql.connector import Error
import os
import streamlit as st
from datetime import datetime

class MySQLDatabase:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', ''),
                database=os.getenv('DB_NAME', 'reading_tracker'),
                port=os.getenv('DB_PORT', 3306)
            )
            print("Connected to MySQL database")
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            # Fallback to SQLite for development
            self.connection = None
    
    def get_connection(self):
        """Get database connection, reconnect if needed"""
        if self.connection is None or not self.connection.is_connected():
            self.connect()
        return self.connection

# Create global instance
db = MySQLDatabase()

def init_database():
    """Initialize database tables"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            reading_speed INT DEFAULT 2,
            daily_reading_time INT DEFAULT 30,
            preferred_genres TEXT,
            preferred_language VARCHAR(50) DEFAULT 'Հայերեն',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Reading sessions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            book_id VARCHAR(255) NOT NULL,
            book_title VARCHAR(500) NOT NULL,
            pages_read INT NOT NULL,
            session_duration INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        
        # Book comments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_comments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            username VARCHAR(255) NOT NULL,
            book_id VARCHAR(255) NOT NULL,
            comment_text TEXT NOT NULL,
            rating INT CHECK (rating >= 1 AND rating <= 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        
        # Creative works table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS creative_works (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            username VARCHAR(255) NOT NULL,
            title VARCHAR(500) NOT NULL,
            content_type VARCHAR(100) NOT NULL,
            content TEXT NOT NULL,
            genre VARCHAR(255),
            description TEXT,
            is_public BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        
        # Creative work comments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS creative_work_comments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            creative_work_id INT NOT NULL,
            user_id INT NOT NULL,
            username VARCHAR(255) NOT NULL,
            comment_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (creative_work_id) REFERENCES creative_works(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        
        # Reading reminders table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_reminders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT UNIQUE NOT NULL,
            reminder_time TIME NOT NULL,
            days_of_week VARCHAR(100) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        
        conn.commit()
        cursor.close()
        print("Database tables initialized successfully")
        
    except Error as e:
        print(f"Error initializing database: {e}")
