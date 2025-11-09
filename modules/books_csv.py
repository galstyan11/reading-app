import streamlit as st
import pandas as pd
import requests

@st.cache_data
def load_books():
    """Load books from GitHub CSV"""
    url = "https://raw.githubusercontent.com/galstyan11/reading-app/main/reading_app_db.csv"
    
    try:
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading books: {e}")
        return pd.DataFrame()

def show_all_books(books_df, user):
    # Your existing book display logic, but using CSV data
    st.subheader("📚 Գրքերի Ամբողջական Ցանկ")
    
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
    
    # Display books
    for idx, (_, book) in enumerate(filtered_books.iterrows()):
        with st.expander(f"📗 {book['title']} - {book['author']}"):
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.write(f"**ժանր:** {book['genre']}")
                st.write(f"**Էջեր:** {book['pages']}")
                st.write(f"**Լեզու:** {book['language']}")
                
                if pd.notna(book['description']) and book['description']:
                    st.write(f"**Նկարագրություն:** {book['description']}")
                
                # PDF Link Section
                st.write("---")
                st.write("**📖 Կարդալ Գիրքը**")
                
                if pd.notna(book['link']) and book['link']:
                    # Check link status if not already checked
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
                        <p style='margin: 5px 0; color: #555;'>Կարդալու համար սեղմեք <<Բացել գիրքը>> </p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("❌ PDF հղումը չի աշխատում")
                        st.markdown(f"[🔗 Փորձել արտաքին հղումը]({book['link']})")
                else:
                    st.warning("⚠️ Այս գրքի համար PDF հղում չկա")

def check_link_availability(url):
    """Check if link is accessible"""
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except:
        return False

def show_recommendations(books_df, user):
    # Your existing recommendation logic
    st.subheader("💡 Անհատականացված Առաջարկներ")
    # ... [rest of your recommendation code]

def show_reading_plan(books_df, user):
    # Your existing reading plan logic
    st.subheader("📅 Ընթերցման Պլանավորում")
    # ... [rest of your reading plan code]
