import streamlit as st
import hashlib
import json
from datetime import datetime
from modules.mysql_db import db, init_database

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, email, password, reading_speed=2, daily_reading_time=30, preferred_genres=None, preferred_language='Հայերեն'):
    """Create new user in MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            st.error("❌ Այս օգտանունն արդեն գոյություն ունի")
            cursor.close()
            return False
        
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            st.error("❌ Այս էլ․ փոստն արդեն գոյություն ունի")
            cursor.close()
            return False
        
        # Insert new user
        query = """
        INSERT INTO users (username, email, password, reading_speed, daily_reading_time, preferred_genres, preferred_language)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        genres_json = json.dumps(preferred_genres or [])
        cursor.execute(query, (username, email, hash_password(password), reading_speed, daily_reading_time, genres_json, preferred_language))
        conn.commit()
        cursor.close()
        return True
        
    except Exception as e:
        st.error(f"❌ Սխալ գրանցման ընթացքում: {e}")
        return False

def verify_user(username, password):
    """Verify user credentials from MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM users WHERE username = %s AND password = %s"
        cursor.execute(query, (username, hash_password(password)))
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            # Convert JSON string back to list
            if user['preferred_genres']:
                user['preferred_genres'] = json.loads(user['preferred_genres'])
            else:
                user['preferred_genres'] = []
            
            user['id'] = user['id']  # Use database ID
            user['username'] = user['username']
            return user
        
        return None
        
    except Exception as e:
        st.error(f"❌ Սխալ մուտքագրման ընթացքում: {e}")
        return None

def get_current_user():
    return st.session_state.get('user')

def logout():
    st.session_state.user = None
    st.session_state.page = "login"

def update_user_preferences(username, reading_speed, daily_reading_time, preferred_genres, preferred_language):
    """Update user preferences in MySQL"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = """
        UPDATE users 
        SET reading_speed = %s, daily_reading_time = %s, preferred_genres = %s, preferred_language = %s 
        WHERE username = %s
        """
        
        genres_json = json.dumps(preferred_genres or [])
        cursor.execute(query, (reading_speed, daily_reading_time, genres_json, preferred_language, username))
        conn.commit()
        cursor.close()
        return True
        
    except Exception as e:
        st.error(f"❌ Սխալ կարգավորումները թարմացնելիս: {e}")
        return False

def show_auth_page(books_df):
    # Initialize database on first run
    init_database()
    
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
        available_genres = books_df['genre'].unique().tolist() if not books_df.empty else []
        reg_preferred_genres = st.multiselect("Նախընտրելի Ժանրեր", available_genres, key="reg_genres")

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
                success = create_user(reg_username, reg_email, reg_password, reg_reading_speed, reg_daily_time, reg_preferred_genres, reg_preferred_language)
                if success:
                    # Get the newly created user
                    new_user = verify_user(reg_username, reg_password)
                    if new_user:
                        st.session_state.user = new_user
                        st.session_state.page = "main"
                        st.success("✅ Գրանցումը հաջող էր!")
                        st.rerun()
                    else:
                        st.error("❌ Չհաջողվեց բեռնել օգտատիրոջ տվյալները")
