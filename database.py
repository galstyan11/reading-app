import mysql.connector
import streamlit as st

def get_connection():
    return mysql.connector.connect(
        host='localhost',
        database='reading_app_db',
        user='root',
        password='galstyanm2311#'
    )

# Remove books table creation - we don't need it anymore
def create_tables_if_not_exist():
    """Create only user-related tables"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Only create user-related tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE,
                email VARCHAR(255) UNIQUE,
                password VARCHAR(255),
                reading_speed INT DEFAULT 2,
                daily_reading_time INT DEFAULT 30,
                preferred_genres TEXT,
                preferred_language VARCHAR(50) DEFAULT 'Հայերեն',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Keep other user-related tables but remove book_id foreign keys
        # ... [rest of your table creation without books table]
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error creating tables: {e}")
        return False
