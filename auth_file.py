import streamlit as st
import hashlib
import json
import os

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """Load users from JSON file"""
    try:
        if os.path.exists('data/users.json'):
            with open('data/users.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_users(users):
    """Save users to JSON file"""
    os.makedirs('data', exist_ok=True)
    with open('data/users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def create_user(username, email, password, reading_speed=2, daily_reading_time=30, preferred_genres=None, preferred_language='Հայերեն'):
    """Create new user"""
    users = load_users()
    
    if username in users:
        st.error("❌ Այս օգտանունն արդեն գոյություն ունի")
        return False
    
    users[username] = {
        'email': email,
        'password': hash_password(password),
        'reading_speed': reading_speed,
        'daily_reading_time': daily_reading_time,
        'preferred_genres': preferred_genres or [],
        'preferred_language': preferred_language,
        'created_at': str(st.datetime.now())
    }
    
    save_users(users)
    return True

def verify_user(username, password):
    """Verify user credentials"""
    users = load_users()
    
    if username in users and users[username]['password'] == hash_password(password):
        user_data = users[username].copy()
        user_data['username'] = username
        user_data['id'] = username  # Use username as ID for file-based system
        return user_data
    
    return None

def get_current_user():
    return st.session_state.get('user')

def logout():
    st.session_state.user = None
    st.session_state.page = "login"

def show_auth_page(books_df):
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
        # ... [rest of your registration form]
