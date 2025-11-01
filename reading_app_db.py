import streamlit as st
import pandas as pd
import sqlite3
import json
import requests
import hashlib

def create_tables_if_not_exist():
    """Ավտոմատ ստեղծել աղյուսակները, եթե չկան"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Ստեղծել users աղյուսակը
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password TEXT,
                reading_speed INTEGER DEFAULT 2,
                daily_reading_time INTEGER DEFAULT 30,
                preferred_genres TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ստեղծել reading_sessions աղյուսակը
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reading_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                book_id INTEGER,
                start_time DATETIME,
                end_time DATETIME,
                pages_read INTEGER,
                session_duration INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ստեղծել books աղյուսակը
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                author TEXT,
                genre TEXT,
                pages INTEGER,
                language TEXT,
                publication_year INTEGER,
                link TEXT,
                description TEXT
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error creating tables: {e}")
        return False

def get_connection():
    """SQLite database connection"""
    return sqlite3.connect('reading_app.db', check_same_thread=False)

def hash_password(password):
    """Hash password for security"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, email, password, reading_speed=2, daily_reading_time=30, preferred_genres=None):
    """Ստեղծել նոր օգտատիրոջ"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if preferred_genres is None or len(preferred_genres) == 0:
            genres_value = None
        else:
            genres_value = json.dumps(preferred_genres)
        
        hashed_password = hash_password(password)
        
        cursor.execute("""
            INSERT INTO users (username, email, password, reading_speed, daily_reading_time, preferred_genres)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, email, hashed_password, reading_speed, daily_reading_time, genres_value))
        
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return user_id
    except Exception as e:
        st.error(f"❌ Սխալ օգտատիրոջ ստեղծման ընթացքում: {e}")
        return None

def verify_user(username, password):
    """Verify user credentials"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if user_data:
            columns = ['id', 'username', 'email', 'password', 'reading_speed', 'daily_reading_time', 'preferred_genres', 'created_at']
            user = dict(zip(columns, user_data))
            
            if user['password'] is None:
                st.error("❌ Այս օգտանունով օգտատերը գոյություն ունի, բայց գաղտնաբառ չի սահմանված։")
                return None
            
            hashed_password = hash_password(password)
            if user['password'] == hashed_password:
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
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if user_data:
            columns = ['id', 'username', 'email', 'password', 'reading_speed', 'daily_reading_time', 'preferred_genres', 'created_at']
            user = dict(zip(columns, user_data))
            
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
        st.error(f"Error getting user: {e}")
        return None

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

def add_reading_session(user_id, book_id, pages_read, session_duration):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO reading_sessions (user_id, book_id, pages_read, session_duration)
            VALUES (?, ?, ?, ?)
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
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT rs.*, b.title, b.author 
            FROM reading_sessions rs 
            JOIN books b ON rs.book_id = b.id 
            WHERE rs.user_id = ? 
            ORDER BY rs.created_at DESC
        """, (user_id,))
        
        sessions_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if sessions_data:
            columns = ['id', 'user_id', 'book_id', 'start_time', 'end_time', 'pages_read', 'session_duration', 'created_at', 'title', 'author']
            sessions = [dict(zip(columns, session)) for session in sessions_data]
            return sessions
        return []
    except Exception as e:
        st.error(f"Error getting sessions: {e}")
        return []

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
        
        preferred_genres = user_preferences.get('preferred_genres', [])
        if book['genre'] in preferred_genres:
            score += 40
        
        preferred_pages = user_preferences.get('preferred_page_range', [100, 300])
        if preferred_pages[0] <= book['pages'] <= preferred_pages[1]:
            score += 20
        
        if book['language'] == user_preferences.get('preferred_language', 'Հայերեն'):
            score += 15
        
        reading_speed = user_preferences.get('reading_speed', 2)
        daily_time = user_preferences.get('daily_reading_time', 30)
        estimated_time = book['pages'] / reading_speed
        
        if estimated_time <= daily_time * 7:
            score += 25
        
        recommendations.append((book, score))
    
    recommendations.sort(key=lambda x: x[1], reverse=True)
    return [book for book, score in recommendations[:5]]

def show_all_books(books_df, user):
    st.subheader("📚 Գրքերի Ամբողջական Ցանկ")
    
    if 'link_status' not in st.session_state:
        st.session_state.link_status = {}
    
    col1, col2, col3 = st.columns(3)
    with col1:
        search_title = st.text_input("🔍 Որոնել ըստ անվանման")
    with col2:
        search_author = st.text_input("🔍 Որոնել ըստ հեղինակի")
    with col3:
        selected_genre = st.selectbox("Ընտրել ժանր", ["Բոլորը"] + books_df['genre'].unique().tolist())
    
    filtered_books = books_df.copy()
    if search_title:
        filtered_books = filtered_books[filtered_books['title'].str.contains(search_title, case=False, na=False)]
    if search_author:
        filtered_books = filtered_books[filtered_books['author'].str.contains(search_author, case=False, na=False)]
    if selected_genre != "Բոլորը":
        filtered_books = filtered_books[filtered_books['genre'] == selected_genre]
    
    for _, book in filtered_books.iterrows():
        with st.expander(f"📗 {book['title']} - {book['author']}"):
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.write(f"**ժանր:** {book['genre']}")
                st.write(f"**Էջեր:** {book['pages']}")
                st.write(f"**Լեզու:** {book['language']}")
                
                if pd.notna(book['description']) and book['description']:
                    st.write(f"**Նկարագրություն:** {book['description']}")
                
                st.write("---")
                st.write("**📖 Կարդալ Գիրքը**")
                
                if pd.notna(book['link']) and book['link']:
                    if book['id'] not in st.session_state.link_status:
                        st.session_state.link_status[book['id']] = check_link_availability(book['link'])
                    
                    link_status = st.session_state.link_status[book['id']]
                    
                    if link_status:
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
                        <p style='margin: 5px 0; color: #555;'>Կտտացրեք վերևի կապը գիրքը կարդալու համար</p>
                        <p style='margin: 5px 0; color: #777; font-size: 0.9em;'>Հղում: {book['link'][:50]}...</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("❌ PDF հղումը չի աշխատում")
                        st.markdown(f"[🔗 Փորձել արտաքին հղումը]({book['link']})")
                else:
                    st.warning("⚠️ Այս գրքի համար PDF հղում չկա")
                
                st.write("---")
                st.write("📖 Ընթերցման Հետևում")
                pages_read = st.number_input(
                    "Կարդացած էջեր",
                    min_value=0,
                    max_value=book['pages'],
                    value=0,
                    key=f"pages_{book['id']}"
                )
                reading_time = st.number_input(
                    "Ընթերցման ժամանակ (րոպե)",
                    min_value=0,
                    max_value=480,
                    value=0,
                    key=f"time_{book['id']}"
                )
                
                if st.button("💾 Պահպանել Ընթերցումը", key=f"save_{book['id']}"):
                    if pages_read > 0 and reading_time > 0:
                        success = add_reading_session(user['id'], book['id'], pages_read, reading_time)
                        if success:
                            st.success("Տվյալները պահպանված են!")
            
            with col2:
                st.write("**📊 Գրքի Մասին**")
                
                total_minutes = book['pages'] // user['reading_speed']
                hours = total_minutes // 60
                minutes = total_minutes % 60
                
                if hours > 0:
                    st.metric("⏱️ Ընդհանուր Ժամանակ", f"{hours}ժ {minutes}ր")
                else:
                    st.metric("⏱️ Ընդհանուր Ժամանակ", f"{minutes} րոպե")
                
                daily_pages, daily_minutes = calculate_reading_plan(
                    book['pages'], user['reading_speed'], user['daily_reading_time'], 30
                )
                st.metric("📅 Օրական Պլան", f"{daily_pages} էջ")
                
                if pd.notna(book['publication_year']):
                    st.write(f"**📅 Հրատարակման Տարի:** {int(book['publication_year'])}")

def show_recommendations(books_df, user):
    st.subheader("💡 Անհատականացված Առաջարկներ")
    
    user_preferences = {
        'preferred_genres': user['preferred_genres'] if user['preferred_genres'] else [],
        'reading_speed': user['reading_speed'],
        'daily_reading_time': user['daily_reading_time'],
        'preferred_language': 'Հայերեն',
        'preferred_page_range': [50, 400]
    }
    
    recommendations = get_advanced_recommendations(books_df, user_preferences)
    
    if recommendations:
        st.success(f"✅ Գտնվել է {len(recommendations)} առաջարկվող գիրք")
        
        for book in recommendations:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"### {book['title']}")
                    st.write(f"**Հեղինակ:** {book['author']}")
                    st.write(f"**ժանր:** {book['genre']} • **Էջեր:** {book['pages']}")
                    st.write(f"**Լեզու:** {book['language']}")
                    
                    if pd.notna(book['description']) and book['description']:
                        with st.expander("📖 Նկարագրություն"):
                            st.write(book['description'])
                    
                    if pd.notna(book['link']) and book['link']:
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
            
            if pd.notna(book_info['link']) and book_info['link']:
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
                    
                    total_reading_time = book_info['pages'] // user['reading_speed']
                    st.info(f"**Ընդհանուր ընթերցման ժամանակ:** {total_reading_time} րոպե")
                    
                    st.subheader("📅 Շաբաթական Պլան")
                    weekly_pages = daily_pages * 7
                    st.write(f"**Շաբաթական ընթերցում:** {weekly_pages} էջ")
                    st.write(f"**Շաբաթական ժամանակ:** {daily_minutes * 7} րոպե")
                    
                    if daily_minutes > user['daily_reading_time']:
                        st.warning("⚠️ Օրական պլանը գերազանցում է ձեր նախընտրած ժամանակը")
                    else:
                        st.success("✅ Պլանը իրագործելի է ձեր նախընտրած ժամանակում")
                else:
                    st.error("❌ Չհաջողվեց հաշվարկել պլանը")
            else:
                st.warning("⚠️ Գրքի էջերի քանակը վավեր չէ")

def show_statistics(user):
    st.subheader("📊 Իմ Ընթերցման Վիճակագրություն")
    
    sessions = get_user_sessions(user['id'])
    
    if sessions:
        sessions_df = pd.DataFrame(sessions)
        
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
        
        st.subheader("🕒 Վերջին Ընթերցումները")
        for session in sessions[:5]:
            st.write(f"- **{session['title']}** - {session['pages_read']} էջ ({session['session_duration']} րոպե)")
    
    else:
        st.info("📝 Դեռ չունեք ընթերցման տվյալներ։ Սկսեք ընթերցել և ավելացրեք ձեր առաջին ընթերցումը։")

def show_settings(user):
    st.subheader("⚙️ Օգտատիրոջ Կարգավորումներ")
    
    st.write(f"**Օգտանուն:** {user['username']}")
    st.write(f"**Էլ. Փոստ:** {user['email']}")
    
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
    
    if st.button("💾 Պահպանել Կարգավորումները"):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            if not new_preferred_genres:
                genres_value = None
            else:
                genres_value = json.dumps(new_preferred_genres)
            
            cursor.execute("""
                UPDATE users 
                SET reading_speed = ?, daily_reading_time = ?, preferred_genres = ?
                WHERE id = ?
            """, (new_reading_speed, new_daily_time, genres_value, user['id']))
            
            conn.commit()
            cursor.close()
            conn.close()
            
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
        
        books_df = load_books()
        available_genres = books_df['genre'].unique().tolist() if not books_df.empty else []
        reg_preferred_genres = st.multiselect("Նախընտրելի Ժանրեր", available_genres, key="reg_genres")
        
        if st.button("📝 Գրանցվել", key="reg_btn", type="primary"):
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
                existing_user = get_user(reg_username)
                if existing_user:
                    st.error("❌ Այս օգտանունն արդեն գոյություն ունի")
                else:
                    user_id = create_user(reg_username, reg_email, reg_password, reg_reading_speed, reg_daily_time, reg_preferred_genres)
                    if user_id:
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
    
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title(f"📖 Բարի Գալուստ, {user['username']}!")
    with col3:
        if st.button("🚪 Դուրս Գալ"):
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📚 Բոլոր Գրքերը", 
        "💡 Առաջարկներ", 
        "📅 Ընթերցման Պլան",
        "📊 Իմ Վիճակագրություն",
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
        show_settings(user)

def main():
    st.set_page_config(page_title="📖 Ընթերցանության Հավելված", layout="wide")
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = "login"
    if 'link_status' not in st.session_state:
        st.session_state.link_status = {}
    
    create_tables_if_not_exist()
    
    if st.session_state.user is None:
        show_auth_page()
    else:
        show_main_app()

if __name__ == "__main__":
    main()