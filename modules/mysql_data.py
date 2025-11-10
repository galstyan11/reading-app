from modules.mysql_db import db
from datetime import datetime

# Reading Sessions
def add_reading_session(user_id, book_id, pages_read, session_duration, book_title):
    """Add reading session to MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = """
        INSERT INTO reading_sessions (user_id, book_id, book_title, pages_read, session_duration)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, book_id, book_title, pages_read, session_duration))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error adding reading session: {e}")
        return False

def get_user_sessions(user_id):
    """Get user's reading sessions from MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM reading_sessions WHERE user_id = %s ORDER BY created_at DESC"
        cursor.execute(query, (user_id,))
        sessions = cursor.fetchall()
        cursor.close()
        return sessions
    except Exception as e:
        print(f"Error getting user sessions: {e}")
        return []

# Book Comments
def add_book_comment(user_id, book_id, comment_text, rating, username):
    """Add book comment to MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = """
        INSERT INTO book_comments (user_id, book_id, comment_text, rating, username)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, book_id, comment_text, rating, username))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error adding book comment: {e}")
        return False

def get_book_comments(book_id):
    """Get comments for a book from MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM book_comments WHERE book_id = %s ORDER BY created_at DESC"
        cursor.execute(query, (book_id,))
        comments = cursor.fetchall()
        cursor.close()
        return comments
    except Exception as e:
        print(f"Error getting book comments: {e}")
        return []

# Creative Works
def add_creative_work(user_id, title, content_type, content, genre, description, is_public, username):
    """Add creative work to MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = """
        INSERT INTO creative_works (user_id, title, content_type, content, genre, description, is_public, username)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, title, content_type, content, genre, description, is_public, username))
        work_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        return work_id
    except Exception as e:
        print(f"Error adding creative work: {e}")
        return None

def get_creative_works(user_id=None, public_only=True):
    """Get creative works from MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        if user_id:
            query = "SELECT * FROM creative_works WHERE user_id = %s ORDER BY created_at DESC"
            cursor.execute(query, (user_id,))
        elif public_only:
            query = "SELECT * FROM creative_works WHERE is_public = TRUE ORDER BY created_at DESC"
            cursor.execute(query)
        else:
            query = "SELECT * FROM creative_works ORDER BY created_at DESC"
            cursor.execute(query)
        
        works = cursor.fetchall()
        cursor.close()
        return works
    except Exception as e:
        print(f"Error getting creative works: {e}")
        return []

def add_creative_work_comment(creative_work_id, user_id, comment_text, username):
    """Add comment to creative work in MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = """
        INSERT INTO creative_work_comments (creative_work_id, user_id, comment_text, username)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (creative_work_id, user_id, comment_text, username))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error adding creative work comment: {e}")
        return False

def get_creative_work_comments(creative_work_id):
    """Get comments for creative work from MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT * FROM creative_work_comments 
        WHERE creative_work_id = %s 
        ORDER BY created_at ASC
        """
        cursor.execute(query, (creative_work_id,))
        comments = cursor.fetchall()
        cursor.close()
        return comments
    except Exception as e:
        print(f"Error getting creative work comments: {e}")
        return []

# Reminders
def add_reminder(user_id, reminder_time, days_of_week, is_active=True):
    """Add reading reminder to MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Use INSERT ... ON DUPLICATE KEY UPDATE since user_id is unique
        query = """
        INSERT INTO reading_reminders (user_id, reminder_time, days_of_week, is_active)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        reminder_time = VALUES(reminder_time),
        days_of_week = VALUES(days_of_week),
        is_active = VALUES(is_active)
        """
        cursor.execute(query, (user_id, reminder_time, days_of_week, is_active))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error adding reminder: {e}")
        return False

def get_user_reminder(user_id):
    """Get user's reminder from MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM reading_reminders WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        reminder = cursor.fetchone()
        cursor.close()
        return reminder
    except Exception as e:
        print(f"Error getting user reminder: {e}")
        return None

def check_reminder_time(user_id):
    """Check if it's reminder time"""
    # Simplified version - you can implement proper time checking
    return False
