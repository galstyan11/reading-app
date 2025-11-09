import streamlit as st
import pandas as pd
import requests
from io import StringIO

# Configure the page
st.set_page_config(
    page_title="Reading App Database",
    page_icon="📚",
    layout="wide"
)

# Load data from GitHub
@st.cache_data
def load_data():
    # Use the raw GitHub URL of your CSV file
    url = "https://raw.githubusercontent.com/galstyan11/reading-app/main/reading_app_db.csv"
    
    try:
        # Read CSV directly from GitHub with proper encoding for BOM
        df = pd.read_csv(url, encoding='utf-8-sig')
        
        # Clean column names (remove BOM and whitespace)
        df.columns = df.columns.str.strip()
        
        st.success("✅ Data loaded successfully!")
        return df
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return None

def main():
    st.title("📚 Reading App Database")
    st.markdown("Explore books in Armenian, English, and Russian")
    
    # Load data
    df = load_data()
    
    if df is None:
        st.stop()
    
    # Show basic stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Books", len(df))
    with col2:
        st.metric("Languages", df['language'].nunique())
    with col3:
        st.metric("Genres", df['genre'].nunique())
    with col4:
        st.metric("Authors", df['author'].nunique())
    
    st.divider()
    
    # Filters
    st.subheader("🔍 Filter Books")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        languages = st.multiselect(
            "Language",
            options=sorted(df['language'].unique()),
            default=[]
        )
    
    with col2:
        genres = st.multiselect(
            "Genre",
            options=sorted(df['genre'].unique()),
            default=[]
        )
    
    with col3:
        book_types = st.multiselect(
            "Type",
            options=sorted(df['type'].unique()),
            default=[]
        )
    
    # Apply filters
    filtered_df = df.copy()
    
    if languages:
        filtered_df = filtered_df[filtered_df['language'].isin(languages)]
    
    if genres:
        filtered_df = filtered_df[filtered_df['genre'].isin(genres)]
    
    if book_types:
        filtered_df = filtered_df[filtered_df['type'].isin(book_types)]
    
    # Search by title or author
    search_term = st.text_input("🔎 Search by title or author")
    if search_term:
        mask = (filtered_df['title'].str.contains(search_term, case=False, na=False) | 
                filtered_df['author'].str.contains(search_term, case=False, na=False))
        filtered_df = filtered_df[mask]
    
    st.divider()
    
    # Display results
    st.subheader(f"📖 Results ({len(filtered_df)} books)")
    
    if len(filtered_df) > 0:
        # Display as cards or table based on user preference
        view_mode = st.radio("View mode:", ["Table", "Cards"], horizontal=True)
        
        if view_mode == "Table":
            st.dataframe(
                filtered_df[['title', 'author', 'type', 'genre', 'language', 'pages', 'publication_year']],
                use_container_width=True
            )
        else:
            # Card view
            cols = st.columns(2)
            for idx, row in filtered_df.reset_index(drop=True).iterrows():
                with cols[idx % 2]:
                    with st.container():
                        st.markdown(f"### {row['title']}")
                        st.markdown(f"**Author:** {row['author']}")
                        st.markdown(f"**Type:** {row['type']} | **Genre:** {row['genre']}")
                        st.markdown(f"**Language:** {row['language']} | **Pages:** {row['pages']}")
                        st.markdown(f"**Year:** {row['publication_year']}")
                        
                        if pd.notna(row['link']) and row['link'] != '':
                            st.markdown(f"[📖 Read Book]({row['link']})")
                        
                        if pd.notna(row['description']) and row['description'] != '':
                            with st.expander("Description"):
                                st.write(row['description'])
                        
                        st.divider()
    else:
        st.info("No books found matching your filters.")
    
    st.divider()
    
    # Data insights
    st.subheader("📊 Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Books by Language**")
        lang_counts = df['language'].value_counts()
        st.bar_chart(lang_counts)
    
    with col2:
        st.markdown("**Books by Genre**")
        genre_counts = df['genre'].value_counts().head(10)
        st.bar_chart(genre_counts)

if __name__ == "__main__":
    main()
