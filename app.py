import streamlit as st
from modules.database import create_tables_if_not_exist, get_connection
from modules.auth import show_auth_page, hash_password, create_user, verify_user, get_user
from modules.books import show_all_books, show_recommendations, show_reading_plan
from modules.users import show_statistics, show_reminders, show_settings
from modules.creative import show_creative_works

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
    
    # Main tabs
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
    st.set_page_config(
        page_title="📖 Ընթերցանության Հավելված", 
        page_icon="📚",
        layout="wide"
    )
    
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
