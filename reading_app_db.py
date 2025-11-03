import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta
import json
import requests
import base64
import hashlib
import time
import threading

def create_tables_if_not_exist():
    """Ավտոմատ ստեղծել աղյուսակները, եթե չկան"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Ստեղծել users աղյուսակը with password and preferred_language
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
        
        # Ստեղծել reading_sessions աղյուսակը
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reading_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                book_id INT,
                start_time DATETIME,
                end_time DATETIME,
                pages_read INT,
                session_duration INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ստեղծել book_comments աղյուսակը
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS book_comments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                book_id INT,
                comment_text TEXT,
                rating INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        """)
        
        # Ստեղծել creative_works աղյուսակը
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creative_works (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                title VARCHAR(255),
                content_type VARCHAR(50),
                content TEXT,
                genre VARCHAR(100),
                description TEXT,
                is_public BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Ստեղծել creative_work_comments աղյուսակը
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creative_work_comments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                creative_work_id INT,
                user_id INT,
                comment_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creative_work_id) REFERENCES creative_works(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Ստեղծել reminders աղյուսակը
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reading_reminders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                reminder_time TIME,
                is_active BOOLEAN DEFAULT TRUE,
                days_of_week VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error creating tables: {e}")
        return False

# Database connection
def get_connection():
    return mysql.connector.connect(
        host='localhost',
        database='reading_app_db',
        user='root',
        password='galstyanm2311#'
    )

def hash_password(password):
    """Hash password for security"""
    return hashlib.sha256(password.encode()).hexdigest()

# Reminder Functions
def add_reminder(user_id, reminder_time, days_of_week, is_active=True):
    """Ավելացնել նոր հիշեցում"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Delete existing reminders for this user
        cursor.execute("DELETE FROM reading_reminders WHERE user_id = %s", (user_id,))
        
        # Insert new reminder
        cursor.execute("""
            INSERT INTO reading_reminders (user_id, reminder_time, days_of_week, is_active)
            VALUES (%s, %s, %s, %s)
        """, (user_id, reminder_time, json.dumps(days_of_week), is_active))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error adding reminder: {e}")
        return False

def get_user_reminder(user_id):
    """Ստանալ օգտատիրոջ հիշեցումը"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM reading_reminders WHERE user_id = %s", (user_id,))
        reminder = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if reminder and reminder['days_of_week']:
            try:
                reminder['days_of_week'] = json.loads(reminder['days_of_week'])
            except:
                reminder['days_of_week'] = []
        
        return reminder
    except Exception as e:
        st.error(f"Error getting reminder: {e}")
        return None

def check_reminder_time(user_id):
    """Ստուգել հիշեցման ժամանակը"""
    try:
        reminder = get_user_reminder(user_id)
        if not reminder or not reminder['is_active']:
            return False
        
        current_time = datetime.now().time()
        reminder_time = reminder['reminder_time']
        
        # Check if current time is within 5 minutes of reminder time
        current_minutes = current_time.hour * 60 + current_time.minute
        reminder_minutes = reminder_time.hour * 60 + reminder_time.minute
        
        return abs(current_minutes - reminder_minutes) <= 5
    except Exception as e:
        st.error(f"Error checking reminder: {e}")
        return False

def get_reading_time_recommendation(genre):
    """Ստանալ ընթերցման ժամանակի առաջարկ ըստ ժանրի"""
    genre_recommendations = {
        'Բանաստեղծություններ': {
            'time': 'ճանապարհին կամ ավտոբուսում',
            'icon': '🚌',
            'reason': 'Բանաստեղծությունները կարճ են և հեշտ է կարդալ դրանք ճանապարհորդության ընթացքում'
        },
        'Դրամա': {
            'time': 'երեկոյան',
            'icon': '🌙',
            'reason': 'Դրամատիկ գրքերը հարուստ են զգացմունքներով և հարմար են երեկոյան հանգստի ժամանակ'
        },
        'Մոտիվացիոն': {
            'time': 'առավոտյան',
            'icon': '☀️',
            'reason': 'Մոտիվացիոն գրքերը կօգնեն ձեզ դրական տրամադրվածությամբ սկսել օրը'
        },
        'Գիտական': {
            'time': 'առավոտյան',
            'icon': '🔬',
            'reason': 'Գիտական գրքերը պահանջում են կենտրոնացում, ինչը ավելի հեշտ է թարմ ու պայծառ առավոտյան'
        },
        'Սիրավեպ': {
            'time': 'երեկոյան',
            'icon': '❤️',
            'reason': 'Սիրային վեպերը հարմար են հանգստանալու և ռոմանտիկ տրամադրվածության համար'
        },
        'Գիտաֆանտաստիկա': {
            'time': 'երեկոյան',
            'icon': '🚀',
            'reason': 'Ֆանտաստիկան հարմար է երեկոյան, երբ կարող եք ամբողջությամբ ընկղմվել երևակայության աշխարհ'
        }
    }
    
    return genre_recommendations.get(genre, {
        'time': 'ցանկացած ժամանակ',
        'icon': '📚',
        'reason': 'Այս գիրքը հարմար է ընթերցման ցանկացած ժամանակ'
    })

# User authentication
def create_user(username, email, password, reading_speed=2, daily_reading_time=30, preferred_genres=None, preferred_language='Հայերեն'):
    """Ստեղծել նոր օգտատիրոջ"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Handle empty genres
        if preferred_genres is None or len(preferred_genres) == 0:
            genres_value = None
        else:
            genres_value = json.dumps(preferred_genres)
        
        # Hash password
        hashed_password = hash_password(password)
        
        cursor.execute("""
            INSERT INTO users (username, email, password, reading_speed, daily_reading_time, preferred_genres, preferred_language)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, email, hashed_password, reading_speed, daily_reading_time, genres_value, preferred_language))
        
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return user_id
    except mysql.connector.IntegrityError:
        st.error("❌ Այս օգտանունն արդեն գոյություն ունի")
        return None
    except Exception as e:
        st.error(f"❌ Սխալ օգտատիրոջ ստեղծման ընթացքում: {e}")
        return None

def verify_user(username, password):
    """Verify user credentials with proper handling for existing users"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if user:
            # If user exists but has no password (old user)
            if user['password'] is None:
                st.error("❌ Այս օգտանունով օգտատերը գոյություն ունի, բայց գաղտնաբառ չի սահմանված։ Խնդրում եմ կապնվադ ադմինիստրատորի հետ։")
                return None
            
            # Normal password verification for users with passwords
            hashed_password = hash_password(password)
            if user['password'] == hashed_password:
                # Parse JSON back to list
                if user['preferred_genres']:
                    try:
                        user['preferred_genres'] = json.loads(user['preferred_genres'])
                    except:
                        user['preferred_genres'] = []
                else:
                    user['preferred_genres'] = []
                return user
        
        return None
    except Exception as e:
        st.error(f"Error verifying user: {e}")
        return None

def get_user(username):
    """Ստանալ օգտատիրոջ տվյալները"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        # Parse JSON back to list
        if user and user['preferred_genres']:
            try:
                user['preferred_genres'] = json.loads(user['preferred_genres'])
            except:
                user['preferred_genres'] = []
        elif user:
            user['preferred_genres'] = []
        
        return user
    except Exception as e:
        st.error(f"Error getting user: {e}")
        return None

# Load books from MySQL
@st.cache_data
def load_books():
    try:
        conn = get_connection()
        query = "SELECT id, title, author, genre, pages, language, publication_year, link, description FROM books"
        books_df = pd.read_sql(query, conn)
        conn.close()
        return books_df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

def check_link_availability(url):
    """Ստուգել հղումի հասանելիությունը"""
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except:
        return False

# Reading sessions tracking
def add_reading_session(user_id, book_id, pages_read, session_duration):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO reading_sessions (user_id, book_id, pages_read, session_duration)
            VALUES (%s, %s, %s, %s)
        """, (user_id, book_id, pages_read, session_duration))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error adding reading session: {e}")
        return False

def get_user_sessions(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT rs.*, b.title, b.author 
            FROM reading_sessions rs 
            JOIN books b ON rs.book_id = b.id 
            WHERE rs.user_id = %s 
            ORDER BY rs.created_at DESC
        """, (user_id,))
        
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return sessions
    except Exception as e:
        st.error(f"Error getting sessions: {e}")
        return []

# Book Comments Functions
def add_book_comment(user_id, book_id, comment_text, rating=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO book_comments (user_id, book_id, comment_text, rating)
            VALUES (%s, %s, %s, %s)
        """, (user_id, book_id, comment_text, rating))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error adding comment: {e}")
        return False

def get_book_comments(book_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT bc.*, u.username 
            FROM book_comments bc 
            JOIN users u ON bc.user_id = u.id 
            WHERE bc.book_id = %s 
            ORDER BY bc.created_at DESC
        """, (book_id,))
        
        comments = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return comments
    except Exception as e:
        st.error(f"Error getting comments: {e}")
        return []

# Creative Works Functions
def add_creative_work(user_id, title, content_type, content, genre, description, is_public=True):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO creative_works (user_id, title, content_type, content, genre, description, is_public)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, title, content_type, content, genre, description, is_public))
        
        conn.commit()
        work_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return work_id
    except Exception as e:
        st.error(f"Error adding creative work: {e}")
        return None

def get_creative_works(user_id=None, public_only=True):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        if user_id:
            cursor.execute("""
                SELECT cw.*, u.username 
                FROM creative_works cw 
                JOIN users u ON cw.user_id = u.id 
                WHERE cw.user_id = %s 
                ORDER BY cw.created_at DESC
            """, (user_id,))
        else:
            if public_only:
                cursor.execute("""
                    SELECT cw.*, u.username 
                    FROM creative_works cw 
                    JOIN users u ON cw.user_id = u.id 
                    WHERE cw.is_public = TRUE 
                    ORDER BY cw.created_at DESC
                """)
            else:
                cursor.execute("""
                    SELECT cw.*, u.username 
                    FROM creative_works cw 
                    JOIN users u ON cw.user_id = u.id 
                    ORDER BY cw.created_at DESC
                """)
        
        works = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return works
    except Exception as e:
        st.error(f"Error getting creative works: {e}")
        return []

def add_creative_work_comment(creative_work_id, user_id, comment_text):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO creative_work_comments (creative_work_id, user_id, comment_text)
            VALUES (%s, %s, %s)
        """, (creative_work_id, user_id, comment_text))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error adding creative work comment: {e}")
        return False

def get_creative_work_comments(creative_work_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT cwc.*, u.username 
            FROM creative_work_comments cwc 
            JOIN users u ON cwc.user_id = u.id 
            WHERE cwc.creative_work_id = %s 
            ORDER BY cwc.created_at DESC
        """, (creative_work_id,))
        
        comments = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return comments
    except Exception as e:
        st.error(f"Error getting creative work comments: {e}")
        return []

# Reading plan calculator
def calculate_reading_plan(pages, reading_speed, daily_time, target_days):
    if pages <= 0 or reading_speed <= 0 or target_days <= 0:
        return 0, 0
    daily_pages = pages // target_days
    daily_minutes = daily_pages // reading_speed
    return daily_pages, daily_minutes

def get_advanced_recommendations(books_df, user_preferences):
    if books_df.empty:
        return books_df
    
    recommendations = []
    
    for _, book in books_df.iterrows():
        score = 0
        
        # Genre match (40%)
        preferred_genres = user_preferences.get('preferred_genres', [])
        if book['genre'] in preferred_genres:
            score += 40
        
        # Page count suitability (20%)
        preferred_pages = user_preferences.get('preferred_page_range', [100, 300])
        if preferred_pages[0] <= book['pages'] <= preferred_pages[1]:
            score += 20
        
        # Language preference (15%)
        if book['language'] == user_preferences.get('preferred_language', 'Հայերեն'):
            score += 15
        
        # Reading time feasibility (25%)
        reading_speed = user_preferences.get('reading_speed', 2)
        daily_time = user_preferences.get('daily_reading_time', 30)
        estimated_time = book['pages'] / reading_speed
        
        if estimated_time <= daily_time * 7:  # 1 week
            score += 25
        
        recommendations.append((book, score))
    
    # Sort by score and return top recommendations
    recommendations.sort(key=lambda x: x[1], reverse=True)
    return [book for book, score in recommendations[:5]]

def show_all_books(books_df, user):
    st.subheader("📚 Գրքերի Ամբողջական Ցանկ")
    
    # Ստուգել հղումները
    if 'link_status' not in st.session_state:
        st.session_state.link_status = {}
    
    # Search and filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search_title = st.text_input("🔍 Որոնել ըստ վերնագրի")
    with col2:
        search_author = st.text_input("🔍 Որոնել ըստ հեղինակի")
    with col3:
        selected_genre = st.selectbox("Ընտրել ժանր", ["Բոլորը"] + books_df['genre'].unique().tolist())
    
    # Filter books
    filtered_books = books_df.copy()
    if search_title:
        filtered_books = filtered_books[filtered_books['title'].str.contains(search_title, case=False, na=False)]
    if search_author:
        filtered_books = filtered_books[filtered_books['author'].str.contains(search_author, case=False, na=False)]
    if selected_genre != "Բոլորը":
        filtered_books = filtered_books[filtered_books['genre'] == selected_genre]
    
    # Display books with PDF links
    for idx, (_, book) in enumerate(filtered_books.iterrows()):
        with st.expander(f"📗 {book['title']} - {book['author']}"):
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.write(f"**ժանր:** {book['genre']}")
                st.write(f"**Էջեր:** {book['pages']}")
                st.write(f"**Լեզու:** {book['language']}")
                
                if pd.notna(book['description']) and book['description']:
                    st.write(f"**Նկարագրություն:** {book['description']}")
                
                # PDF Link Section - ALWAYS SHOW IF LINK EXISTS IN DATABASE
                st.write("---")
                st.write("**📖 Կարդալ Գիրքը**")
                
                if pd.notna(book['link']) and book['link']:
                    # Check link status if not already checked
                    if book['id'] not in st.session_state.link_status:
                        st.session_state.link_status[book['id']] = check_link_availability(book['link'])
                    
                    link_status = st.session_state.link_status[book['id']]
                    
                    if link_status:
                        # Simple clickable link
                        st.markdown(f"""
                        <div style='background-color: #e8f5e8; padding: 10px; border-radius: 5px; border: 1px solid #4CAF50;'>
                        <h4 style='color: #2E7D32; margin: 0;'>📚 Գիրքը Հասանելի է Առցանց</h4>
                        <a href='{book['link']}' target='_blank' style='
                            display: inline-block;
                            background-color: #4CAF50;
                            color: white;
                            padding: 10px 20px;
                            text-align: center;
                            text-decoration: none;
                            border-radius: 5px;
                            margin: 10px 0;
                            font-weight: bold;
                        '>📖 Բացել Գիրքը</a>
                        <p style='margin: 5px 0; color: #555;'>Կարդալու համար սեղմեք <<Բացել գիրքը>> </p>
                        <p style='margin: 5px 0; color: #777; font-size: 0.9em;'>Հղում: {book['link'][:50]}...</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("❌ PDF հղումը չի աշխատում")
                        st.markdown(f"[🔗 Փորձել արտաքին հղումը]({book['link']})")
                else:
                    st.warning("⚠️ Այս գրքի համար PDF հղում չկա")
                
                # Reading session tracking
                st.write("---")
                st.write("📖 Ընթերցման Հետևում")
                pages_read = st.number_input(
                    "Կարդացած էջեր",
                    min_value=0,
                    max_value=book['pages'],
                    value=0,
                    key=f"pages_{book['id']}_{idx}"
                )
                reading_time = st.number_input(
                    "Ընթերցման ժամանակ (րոպե)",
                    min_value=0,
                    max_value=480,
                    value=0,
                    key=f"time_{book['id']}_{idx}"
                )
                
                if st.button("💾 Պահպանել Ընթերցումը", key=f"save_{book['id']}_{idx}"):
                    if pages_read > 0 and reading_time > 0:
                        success = add_reading_session(user['id'], book['id'], pages_read, reading_time)
                        if success:
                            st.success("Տվյալները պահպանված են!")
            
            with col2:
                # Book metrics and info
                st.write("**📊 Գրքի Մասին**")
                
                # Reading time estimation
                total_minutes = book['pages'] // user['reading_speed']
                hours = total_minutes // 60
                minutes = total_minutes % 60
                
                if hours > 0:
                    st.metric("⏱️ Ընդհանուր Ժամանակ", f"{hours}ժ {minutes}ր")
                else:
                    st.metric("⏱️ Ընդհանուր Ժամանակ", f"{minutes} րոպե")
                
                # Daily reading plan
                daily_pages, daily_minutes = calculate_reading_plan(
                    book['pages'], user['reading_speed'], user['daily_reading_time'], 30
                )
                st.metric("📅 Օրական Պլան", f"{daily_pages} էջ")
                
                # Reading time recommendation based on genre
                recommendation = get_reading_time_recommendation(book['genre'])
                st.info(f"{recommendation['icon']} **Առաջարկվող ընթերցման ժամանակ:** {recommendation['time']}")
                
                # Additional book info
                if pd.notna(book['publication_year']):
                    st.write(f"**📅 Հրատարակման Տարի:** {int(book['publication_year'])}")
            
            # Comments Section for the book
            st.write("---")
            show_book_comments_section(book['id'], user, f"all_books_{book['id']}_{idx}")

def show_book_comments_section(book_id, user, unique_suffix=""):
    """Show comments section for a specific book"""
    st.subheader("💬 Մեկնաբանություններ")
    
    # Get existing comments
    comments = get_book_comments(book_id)
    
    # Display existing comments
    if comments:
        st.write("### 📝 Գրքի Մասին Մեկնաբանություններ")
        for comment in comments:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**👤 {comment['username']}**")
                    st.write(comment['comment_text'])
                    if comment['rating']:
                        st.write(f"⭐ Վարկանիշ: {comment['rating']}/5")
                with col2:
                    st.write(f"_{comment['created_at'].strftime('%Y-%m-%d %H:%M')}_")
                st.markdown("---")
    else:
        st.info("📝 Մեկնաբանություններ դեռ չկան։ Դուք կարող եք լինել առաջինը։")
    
    # Add new comment form
    st.write("### ✍️ Ավելացնել Նոր Մեկնաբանություն")
    with st.form(key=f"comment_form_{book_id}_{unique_suffix}"):
        new_comment = st.text_area("Ձեր մեկնաբանությունը", height=100, 
                                 placeholder="Կիսեք ձեր կարծիքը գրքի, հերոսների կամ սյուժեի վերաբերյալ...",
                                 key=f"comment_text_{book_id}_{unique_suffix}")
        rating = st.slider("Վարկանիշ", 1, 5, 3, 
                          help="1 - Շատ թույլ, 5 - Գերազանց",
                          key=f"rating_{book_id}_{unique_suffix}")
        
        submit_comment = st.form_submit_button("📤 Ուղարկել")
        
        if submit_comment and new_comment.strip():
            success = add_book_comment(user['id'], book_id, new_comment.strip(), rating)
            if success:
                st.success("✅ Ձեր մեկնաբանությունը հաջողությամբ ավելացվել է!")
                st.rerun()
            else:
                st.error("❌ Չհաջողվեց ավելացնել մեկնաբանությունը")

def show_recommendations(books_df, user):
    st.subheader("💡 Անհատականացված Առաջարկներ")
    
    # User preferences for recommendations
    user_preferences = {
        'preferred_genres': user['preferred_genres'] if user['preferred_genres'] else [],
        'reading_speed': user['reading_speed'],
        'daily_reading_time': user['daily_reading_time'],
        'preferred_language': user.get('preferred_language', 'Հայերեն'),
        'preferred_page_range': [50, 400]
    }
    
    recommendations = get_advanced_recommendations(books_df, user_preferences)
    
    if recommendations:
        st.success(f"✅ Գտնվել է {len(recommendations)} առաջարկվող գիրք")
        
        for idx, book in enumerate(recommendations):
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"### {book['title']}")
                    st.write(f"**Հեղինակ:** {book['author']}")
                    st.write(f"**ժանր:** {book['genre']} • **Էջեր:** {book['pages']}")
                    st.write(f"**Լեզու:** {book['language']}")
                    
                    # Reading time recommendation
                    recommendation = get_reading_time_recommendation(book['genre'])
                    st.success(f"**⏰ Ընթերցման առաջարկ:** {recommendation['icon']} {recommendation['time']}")
                    st.write(f"*{recommendation['reason']}*")
                    
                    if pd.notna(book['description']) and book['description']:
                        with st.expander("📖 Նկարագրություն"):
                            st.write(book['description'])
                    
                    # PDF Link in recommendations too
                    if pd.notna(book['link']) and book['link']:
                        # Check link status if not already checked
                        if book['id'] not in st.session_state.link_status:
                            st.session_state.link_status[book['id']] = check_link_availability(book['link'])
                        
                        link_status = st.session_state.link_status[book['id']]
                        
                        if link_status:
                            st.markdown(f"""
                            <a href='{book['link']}' target='_blank' style='
                                display: inline-block;
                                background-color: #2196F3;
                                color: white;
                                padding: 8px 16px;
                                text-align: center;
                                text-decoration: none;
                                border-radius: 4px;
                                margin: 5px 0;
                                font-weight: bold;
                            '>📖 Կարդալ Այս Գիրքը</a>
                            """, unsafe_allow_html=True)
                
                with col2:
                    # Reading time estimation
                    total_minutes = book['pages'] // user['reading_speed']
                    hours = total_minutes // 60
                    minutes = total_minutes % 60
                    
                    if hours > 0:
                        st.metric("⏱️ Ընդհանուր ժամանակ", f"{hours}ժ {minutes}ր")
                    else:
                        st.metric("⏱️ Ընդհանուր ժամանակ", f"{minutes} րոպե")
                    
                    daily_pages, daily_minutes = calculate_reading_plan(
                        book['pages'], user['reading_speed'], user['daily_reading_time'], 30
                    )
                    st.metric("📅 Օրական պլան", f"{daily_pages} էջ")
                
                # Comments section for recommended books too
                show_book_comments_section(book['id'], user, f"rec_{book['id']}_{idx}")
                
                st.markdown("---")
    else:
        st.info("ℹ️ Չգտնվեցին առաջարկվող գրքեր։ Ստուգեք ձեր նախընտրությունները կարգավորումներում։")

def show_reading_plan(books_df, user):
    st.subheader("📅 Ընթերցման Պլանավորում")
    
    if not books_df.empty:
        selected_book = st.selectbox(
            "Ընտրեք գիրք պլանավորման համար",
            options=books_df['title'].tolist(),
            index=0
        )
        
        book_info = books_df[books_df['title'] == selected_book].iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Գիրք:** {book_info['title']}")
            st.write(f"**Հեղինակ:** {book_info['author']}")
            st.write(f"**Էջեր:** {book_info['pages']}")
            st.write(f"**ժանր:** {book_info['genre']}")
            
            # Reading time recommendation
            recommendation = get_reading_time_recommendation(book_info['genre'])
            st.info(f"**⏰ Ընթերցման առաջարկ:** {recommendation['icon']} {recommendation['time']}")
            st.write(f"*{recommendation['reason']}*")
            
            # PDF Link in reading plan section too
            if pd.notna(book_info['link']) and book_info['link']:
                # Check link status if not already checked
                if book_info['id'] not in st.session_state.link_status:
                    st.session_state.link_status[book_info['id']] = check_link_availability(book_info['link'])
                
                link_status = st.session_state.link_status[book_info['id']]
                
                if link_status:
                    st.markdown(f"""
                    <a href='{book_info['link']}' target='_blank' style='
                        display: inline-block;
                        background-color: #FF9800;
                        color: white;
                        padding: 8px 16px;
                        text-align: center;
                        text-decoration: none;
                        border-radius: 4px;
                        margin: 10px 0;
                        font-weight: bold;
                    '>📖 Բացել Գիրքը Պլանավորման համար</a>
                    """, unsafe_allow_html=True)
        
        with col2:
            target_days = st.number_input(
                "🎯 Քանի օրում ցանկանում եք ավարտել գիրքը?",
                min_value=1,
                max_value=365,
                value=min(30, max(1, book_info['pages'] // (user['reading_speed'] * user['daily_reading_time'])))
            )
            
            if book_info['pages'] > 0:
                daily_pages, daily_minutes = calculate_reading_plan(
                    book_info['pages'], user['reading_speed'], user['daily_reading_time'], target_days
                )
                
                if daily_pages > 0:
                    st.success(f"**📅 Օրական պլան:** {daily_pages} էջ")
                    st.success(f"**⏰ Օրական ժամանակ:** {daily_minutes} րոպե")
                    
                    # Progress tracking
                    total_reading_time = book_info['pages'] // user['reading_speed']
                    st.info(f"**Ընդհանուր ընթերցման ժամանակ:** {total_reading_time} րոպե")
                    
                    # Weekly plan
                    st.subheader("📅 Շաբաթական Պլան")
                    weekly_pages = daily_pages * 7
                    st.write(f"**Շաբաթական ընթերցում:** {weekly_pages} էջ")
                    st.write(f"**Շաբաթական ժամանակ:** {daily_minutes * 7} րոպե")
                    
                    # Check feasibility
                    if daily_minutes > user['daily_reading_time']:
                        st.warning("⚠️ Օրական պլանը գերազանցում է ձեր նախընտրած ժամանակը")
                    else:
                        st.success("✅ Պլանը իրագործելի է ձեր նախընտրած ժամանակում")
                else:
                    st.error("❌ Չհաջողվեց հաշվարկել պլանը")
            else:
                st.warning("⚠️ Գրքի էջերի քանակը վավեր չէ")

def show_statistics(user):
    st.subheader("📊 Իմ Ընթերցման Վիճակագրությունը")
    
    sessions = get_user_sessions(user['id'])
    
    if sessions:
        # Convert to DataFrame for easier analysis
        sessions_df = pd.DataFrame(sessions)
        
        # Basic statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_sessions = len(sessions_df)
            st.metric("📖 Ընդհանուր Ընթերցումներ", total_sessions)
        
        with col2:
            total_pages = sessions_df['pages_read'].sum()
            st.metric("📄 Ընդհանուր Էջեր", total_pages)
        
        with col3:
            total_time = sessions_df['session_duration'].sum()
            hours = total_time // 60
            minutes = total_time % 60
            st.metric("⏱️ Ընդհանուր Ժամանակ", f"{hours}ժ {minutes}ր")
        
        with col4:
            avg_speed = total_pages / (total_time / 60) if total_time > 0 else 0
            st.metric("🚀 Միջին Արագություն", f"{avg_speed:.1f} էջ/ժամ")
        
        # Recent sessions
        st.subheader("🕒 Վերջին Ընթերցումները")
        for session in sessions[:5]:
            st.write(f"- **{session['title']}** - {session['pages_read']} էջ ({session['session_duration']} րոպե)")
    
    else:
        st.info("📝 Դեռ չունեք ընթերցման տվյալներ։ Սկսեք ընթերցել և ավելացրեք ձեր առաջին ընթերցումը։")

def show_reminders(user):
    st.subheader("⏰ Ընթերցման Հիշեցումներ")
    
    st.info("""
    **📖 Ընթերցման հիշեցումներ** - Սահմանեք ձեր ամենօրյա ընթերցման ժամանակը, և մենք կհիշեցնենք ձեզ 5 րոպե առաջ։
    """)
    
    # Get existing reminder
    existing_reminder = get_user_reminder(user['id'])
    
    with st.form("reminder_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Apple-style time picker CSS
            st.markdown("""
            <style>
            input[type=time] {
                border: 1px solid #d1d1d1;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 16px;
                width: 100%;
                background-color: #ffffff;
                color: #333333;
                box-shadow: 0 0 4px rgba(0,0,0,0.1);
            }
            input[type=time]:focus {
                border-color: #007aff; /* Apple blue */
                outline: none;
                box-shadow: 0 0 6px rgba(0,122,255,0.4);
            }
            </style>
            """, unsafe_allow_html=True)

            default_time = existing_reminder['reminder_time'] if existing_reminder else datetime.now().time()
            reminder_time_str = st.text_input(
                "🕐 Ընթերցման ժամանակ",
                value=default_time.strftime("%H:%M"),
                help="Ընտրեք ժամանակ, երբ ցանկանում եք ընթերցել",
                placeholder="00:00"
            )

            # Convert string to Python time object
            try:
                reminder_time = datetime.strptime(reminder_time_str, "%H:%M").time()
            except ValueError:
                reminder_time = default_time


        
        with col2:
            # Days of week selection
            days_options = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ", "Շաբաթ", "Կիրակի"]
            default_days = existing_reminder['days_of_week'] if existing_reminder else days_options
            selected_days = st.multiselect(
                "📅 Օրեր",
                options=days_options,
                default=default_days,
                help="Ընտրեք օրերը, երբ ցանկանում եք ստանալ հիշեցումներ"
            )
        
        # Active status
        is_active = st.checkbox(
            "Ակտիվացնել հիշեցումները",
            value=existing_reminder['is_active'] if existing_reminder else True,
            help="Հիշեցումները կաշխատեն միայն այն դեպքում, եթե ակտիվացված են"
        )
        
        submitted = st.form_submit_button("💾 Պահպանել Հիշեցումը")
        
        if submitted:
            if not selected_days:
                st.error("❌ Խնդրում եմ ընտրել առնվազն մեկ օր")
            else:
                success = add_reminder(user['id'], reminder_time, selected_days, is_active)
                if success:
                    st.success("✅ Հիշեցումը հաջողությամբ պահպանված է!")
                    
                    # Show reminder summary
                    days_str = ", ".join(selected_days)
                    st.info(f"""
                    **📋 Ձեր հիշեցման կարգավորումները:**
                    - **⏰ Ժամանակ:** {reminder_time.strftime('%H:%M')}
                    - **📅 Օրեր:** {days_str}
                    - **🔔 Կարգավիճակ:** {'Ակտիվ' if is_active else 'Անջատված'}
                    - **⏱️ Հիշեցում:** 5 րոպե առաջ
                    """)
                    
                    if is_active:
                        st.balloons()
                else:
                    st.error("❌ Չհաջողվեց պահպանել հիշեցումը")
    
    # Current reminder status
    st.subheader("🔔 Ընթացիկ Հիշեցում")
    current_reminder = get_user_reminder(user['id'])
    
    if current_reminder and current_reminder['is_active']:
        days_str = ", ".join(current_reminder['days_of_week'])
        st.success(f"""
        **✅ Ակտիվ հիշեցում**
        - **⏰ Ժամանակ:** {current_reminder['reminder_time'].strftime('%H:%M')}
        - **📅 Օրեր:** {days_str}
        - **⏱️ Հիշեցում:** 5 րոպե առաջ
        """)
        
        # Check if reminder should be shown now
        if check_reminder_time(user['id']):
            st.warning("""
            **🔔 Ընթերցման Ժամանակն է!**
            
            Մոտենում է ձեր ընթերցման ժամանակը: 
            Պատրաստվեք ընթերցել և վայելել ձեր ընտրված գիրքը:
            """)
            st.balloons()
    elif current_reminder and not current_reminder['is_active']:
        st.warning("""
        **🔕 Հիշեցումները անջատված են**
        
        Ձեր հիշեցումը պահպանված է, բայց այս պահին անջատված է:
        Ակտիվացրեք այն վերևի ձևում, եթե ցանկանում եք ստանալ հիշեցումներ:
        """)
    else:
        st.info("""
        **ℹ️ Դեռ չունեք ակտիվ հիշեցումներ**
        
        Սահմանեք ձեր առաջին հիշեցումը վերևի ձևում՝ 
        կանոնավոր ընթերցման սովորություն ձևավորելու համար:
        """)

def show_creative_works(user):
    st.subheader("🎨 Քո Ստեղծագործությունները")
    
    tab1, tab2, tab3 = st.tabs(["➕ Նոր Ստեղծագործություն", "📂 Իմ Ստեղծագործությունները", "🌍 Համայնքի Ստեղծագործությունները"])
    
    with tab1:
        st.write("### ✍️ Ստեղծել Նոր Ստեղծագործություն")
        
        with st.form("creative_work_form", clear_on_submit=True):
            work_title = st.text_input("🎭 Վերնագիր *", placeholder="Ձեր ստեղծագործության վերնագիրը...")
            
            content_type = st.selectbox("📝 Տեսակ *", 
                                      ["Պոեմ", "Պատմվածք", "Վեպ", "Էսսե", "Հոդված", "Բանաստեղծություն", "Այլ"])
            
            genre = st.text_input("🎵 ժանր", placeholder="Օրինակ՝ Սիրային, Թրիլեր, Կենսագրական...")
            
            description = st.text_area("📋 Կարճ Նկարագրություն", 
                                     placeholder="Ստեղծագործության համառոտ նկարագրություն...",
                                     height=80)
            
            content = st.text_area("📖 Բովանդակություն *", 
                                 placeholder="Մուտքագրեք ձեր ստեղծագործության տեքստը այստեղ...",
                                 height=200)
            
            is_public = st.checkbox("🌍 Հասանելի է բոլորին", value=True, 
                                  help="Եթե նշված է, ձեր ստեղծագործությունը տեսանելի կլինի բոլոր օգտատերերին")
            
            submitted = st.form_submit_button("📤 Հրապարակել Ստեղծագործություն")
            
            if submitted:
                if not work_title.strip() or not content.strip():
                    st.error("❌ Վերնագիրը և բովանդակությունը պարտադիր են")
                else:
                    work_id = add_creative_work(
                        user['id'], 
                        work_title.strip(), 
                        content_type, 
                        content.strip(), 
                        genre.strip() if genre.strip() else "Ընդհանուր",
                        description.strip() if description.strip() else None,
                        is_public
                    )
                    
                    if work_id:
                        st.success("✅ Ձեր ստեղծագործությունը հաջողությամբ հրապարակված է!")
                        if is_public:
                            st.info("🌍 Ձեր ստեղծագործությունը այժմ հասանելի է բոլոր օգտատերերին")
                    else:
                        st.error("❌ Չհաջողվեց հրապարակել ստեղծագործությունը")
    
    with tab2:
        st.write("### 📂 Իմ Ստեղծագործությունները")
        
        my_works = get_creative_works(user_id=user['id'])
        
        if my_works:
            for idx, work in enumerate(my_works):
                with st.expander(f"🎭 {work['title']} ({work['content_type']})"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Տեսակ:** {work['content_type']}")
                        if work['genre']:
                            st.write(f"**ժանր:** {work['genre']}")
                        if work['description']:
                            st.write(f"**Նկարագրություն:** {work['description']}")
                        
                        st.write("---")
                        st.write("**📖 Բովանդակություն:**")
                        st.write(work['content'])
                    
                    with col2:
                        st.write(f"**Հրապարակված է:**")
                        st.write(work['created_at'].strftime('%Y-%m-%d %H:%M'))
                        st.write(f"**Տեսանելիություն:** {'🌍 Հասարակական' if work['is_public'] else '🔒 Մասնավոր'}")
                    
                    # Show comments for this work
                    st.write("---")
                    show_creative_work_comments_section(work['id'], user, f"my_work_{work['id']}_{idx}")
        else:
            st.info("📝 Դեռ չունեք հրապարակված ստեղծագործություններ։ Սկսեք ստեղծել ձեր առաջին աշխատանքը։")
    
    with tab3:
        st.write("### 🌍 Համայնքի Ստեղծագործություններ")
        
        community_works = get_creative_works(public_only=True)
        
        if community_works:
            for idx, work in enumerate(community_works):
                # Don't show user's own works in community section
                if work['user_id'] != user['id']:
                    with st.expander(f"🎭 {work['title']} - 👤 {work['username']} ({work['content_type']})"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Հեղինակ:** {work['username']}")
                            st.write(f"**Տեսակ:** {work['content_type']}")
                            if work['genre']:
                                st.write(f"**ժանր:** {work['genre']}")
                            if work['description']:
                                st.write(f"**Նկարագրություն:** {work['description']}")
                            
                            st.write("---")
                            st.write("**📖 Բովանդակություն:**")
                            st.write(work['content'])
                        
                        with col2:
                            st.write(f"**Հրապարակված է:**")
                            st.write(work['created_at'].strftime('%Y-%m-%d %H:%M'))
                        
                        # Show comments for this work
                        st.write("---")
                        show_creative_work_comments_section(work['id'], user, f"community_{work['id']}_{idx}")
        else:
            st.info("👥 Դեռ չկան համայնքի ստեղծագործություններ։ Դուք կարող եք լինել առաջինը։")

def show_creative_work_comments_section(creative_work_id, user, unique_suffix=""):
    """Show comments section for a specific creative work"""
    st.write("#### 💬 Մեկնաբանություններ")
    
    # Get existing comments
    comments = get_creative_work_comments(creative_work_id)
    
    # Display existing comments
    if comments:
        for comment in comments:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**👤 {comment['username']}**")
                    st.write(comment['comment_text'])
                with col2:
                    st.write(f"_{comment['created_at'].strftime('%Y-%m-%d %H:%M')}_")
                st.markdown("---")
    else:
        st.info("💭 Դեռ չկան մեկնաբանություններ։ Դուք կարող եք լինել առաջինը։")
    
    # Add new comment form
    with st.form(key=f"creative_comment_form_{creative_work_id}_{unique_suffix}"):
        new_comment = st.text_area("Ձեր մեկնաբանությունը", height=80, 
                                 placeholder="Կիսվեք ձեր կարծիքով ստեղծագործության մասին...",
                                 key=f"creative_comment_{creative_work_id}_{unique_suffix}")
        
        submit_comment = st.form_submit_button("📤 Ուղարկել Մեկնաբանություն")
        
        if submit_comment and new_comment.strip():
            success = add_creative_work_comment(creative_work_id, user['id'], new_comment.strip())
            if success:
                st.success("✅ Ձեր մեկնաբանությունը հաջողությամբ ավելացվել է!")
                st.rerun()
            else:
                st.error("❌ Չհաջողվեց ավելացնել մեկնաբանությունը")

def show_settings(user):
    st.subheader("⚙️ Օգտատիրոջ Կարգավորումներ")
    
    st.write(f"**Օգտանուն:** {user['username']}")
    st.write(f"**Էլ. Փոստ:** {user['email']}")
    
    # Update preferences
    st.subheader("🔄 Թարմացնել Նախապատվությունները")
    
    new_reading_speed = st.slider(
        "Ընթերցման Արագություն (էջ/րոպե)",
        min_value=1,
        max_value=5,
        value=user['reading_speed']
    )
    
    new_daily_time = st.slider(
        "Օրական Ընթերցման Ժամանակ (րոպե)",
        min_value=15,
        max_value=180,
        value=user['daily_reading_time']
    )
    
    books_df = load_books()
    available_genres = books_df['genre'].unique().tolist() if not books_df.empty else []
    current_genres = user['preferred_genres'] if user['preferred_genres'] else []
    new_preferred_genres = st.multiselect(
        "Նախընտրելի Ժանրեր",
        options=available_genres,
        default=current_genres
    )
    
    # ADD LANGUAGE PREFERENCE TO SETTINGS
    current_language = user.get('preferred_language', 'Հայերեն')
    new_preferred_language = st.selectbox(
        "Նախընտրելի Լեզու",
        ["Հայերեն", "Ռուսերեն", "Անգլերեն"],
        index=["Հայերեն", "Ռուսերեն", "Անգլերեն"].index(current_language) if current_language in ["Հայերեն", "Ռուսերեն", "Անգլերեն"] else 0
    )
    
    if st.button("💾 Պահպանել Կարգավորումները"):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Handle empty genres
            if not new_preferred_genres:
                genres_value = None
            else:
                genres_value = json.dumps(new_preferred_genres)
            
            # UPDATE THE SQL QUERY TO INCLUDE PREFERRED_LANGUAGE
            cursor.execute("""
                UPDATE users 
                SET reading_speed = %s, daily_reading_time = %s, preferred_genres = %s, preferred_language = %s
                WHERE id = %s
            """, (new_reading_speed, new_daily_time, genres_value, new_preferred_language, user['id']))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Update session state
            st.session_state.user = get_user(user['username'])
            st.success("✅ Կարգավորումները պահպանված են!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Սխալ կարգավորումները պահպանելիս: {e}")

def show_auth_page():
    st.title("🔐 Մուտք Գործել կամ Գրանցվել")
    
    tab1, tab2 = st.tabs(["🚪 Մուտք Գործել", "📝 Գրանցվել"])
    
    with tab1:
        st.subheader("Մուտք Գործել")
        login_username = st.text_input("Օգտանուն", key="login_username")
        login_password = st.text_input("Գաղտնաբառ", type="password", key="login_password")

        if st.button("Մուտք Գործել", key="login_btn"):
            if login_username.strip() and login_password.strip():
                user = verify_user(login_username, login_password)
                if user:
                    st.session_state.user = user
                    st.session_state.page = "main"
                    st.success(f"✅ Բարի գալուստ, {user['username']}!")
                    st.rerun()
                else:
                    st.error("❌ Սխալ օգտանուն կամ գաղտնաբառ")
            else:
                st.error("⚠️ Խնդրում եմ մուտքագրեք օգտանունը և գաղտնաբառը")
    
    with tab2:
        st.subheader("Նոր Գրանցում")
        
        st.info("📝 Մուտքագրեք ձեր տվյալները նոր գրանցման համար")
        
        reg_username = st.text_input("Նոր Օգտանուն *", key="reg_username")
        reg_email = st.text_input("Էլ. Փոստ *", key="reg_email")
        reg_password = st.text_input("Գաղտնաբառ *", type="password", key="reg_password", 
                                   help="Գաղտնաբառը պետք է լինի առնվազն 4 նիշ")
        reg_confirm_password = st.text_input("Հաստատել Գաղտնաբառը *", type="password", key="reg_confirm_password")
        
        st.subheader("Ընթերցման Նախապատվություններ")
        reg_reading_speed = st.slider("Ընթերցման Արագություն (էջ/րոպե)", 1, 5, 2, key="reg_speed")
        reg_daily_time = st.slider("Օրական Ընթերցման Ժամանակ (րոպե)", 15, 180, 30, key="reg_time")
        
        # Load available genres from books
        books_df = load_books()
        available_genres = books_df['genre'].unique().tolist() if not books_df.empty else []
        reg_preferred_genres = st.multiselect("Նախընտրելի Ժանրեր", available_genres, key="reg_genres")

        # ADD LANGUAGE PREFERENCE TO REGISTRATION
        reg_preferred_language = st.selectbox(
            "Նախընտրելի Լեզու",
            ["Հայերեն", "Ռուսերեն", "Անգլերեն"],
            key="reg_language"
        )

        if st.button("📝 Գրանցվել", key="reg_btn", type="primary"):
            # Validation
            if not reg_username.strip():
                st.error("❌ Խնդրում եմ մուտքագրեք օգտանուն")
            elif not reg_email.strip():
                st.error("❌ Խնդրում եմ մուտքագրեք էլ. փոստի հասցե")
            elif not reg_password.strip():
                st.error("❌ Խնդրում եմ մուտքագրեք գաղտնաբառ")
            elif reg_password != reg_confirm_password:
                st.error("❌ Գաղտնաբառերը չեն համընկնում")
            elif len(reg_password) < 4:
                st.error("❌ Գաղտնաբառը պետք է լինի առնվազն 4 նիշ")
            else:
                # Check if username already exists
                existing_user = get_user(reg_username)
                if existing_user:
                    st.error("❌ Այս օգտանունն արդեն գոյություն ունի")
                else:
                    # UPDATE CREATE_USER CALL TO INCLUDE LANGUAGE PREFERENCE
                    user_id = create_user(reg_username, reg_email, reg_password, reg_reading_speed, reg_daily_time, reg_preferred_genres, reg_preferred_language)
                    if user_id:
                        # Get the newly created user
                        new_user = get_user(reg_username)
                        if new_user:
                            st.session_state.user = new_user
                            st.session_state.page = "main"
                            st.success("✅ Գրանցումը հաջող էր!")
                            st.rerun()
                        else:
                            st.error("❌ Չհաջողվեց բեռնել օգտատիրոջ տվյալները")
                    else:
                        st.error("❌ Չհաջողվեց գրանցել օգտատիրոջը")

def show_main_app():
    user = st.session_state.user
    books_df = load_books()
    
    # Check for reminders
    if check_reminder_time(user['id']):
        st.toast("🔔 Ընթերցման Ժամանակն է! Մոտենում է ձեր ընթերցման ժամանակը։", icon="📚")
    
    # Header with user info and logout
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title(f"📖 Բարի Գալուստ, {user['username']}!")
    with col3:
        if st.button("🚪 Դուրս Գալ"):
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()
    
    st.markdown("---")
    
    # Main tabs - UPDATED to include Reminders and Creative Works
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📚 Բոլոր Գրքերը", 
        "💡 Առաջարկներ", 
        "📅 Ընթերցման Պլան",
        "📊 Իմ Վիճակագրությունը",
        "🎨 Ստեղծագործություններ",
        "⏰ Հիշեցումներ",
        "⚙️ Կարգավորումներ"
    ])
    
    with tab1:
        show_all_books(books_df, user)
    
    with tab2:
        show_recommendations(books_df, user)
    
    with tab3:
        show_reading_plan(books_df, user)
    
    with tab4:
        show_statistics(user)
    
    with tab5:
        show_creative_works(user)
    
    with tab6:
        show_reminders(user)
    
    with tab7:
        show_settings(user)

def main():
    st.set_page_config(page_title="📖 Ընթերցանության Հավելված", layout="wide")
    
    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = "login"
    if 'link_status' not in st.session_state:
        st.session_state.link_status = {}
    if 'last_reminder_check' not in st.session_state:
        st.session_state.last_reminder_check = None
    
    # Create tables if they don't exist
    create_tables_if_not_exist()
    
    # Navigation
    if st.session_state.user is None:
        show_auth_page()
    else:
        show_main_app()

if __name__ == "__main__":
    main()
