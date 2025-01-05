import streamlit as st
from query import CourseQuery
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="UBC Course Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Custom CSS
st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding: 2rem;
    }
    
    /* Header styling */
    .stTitle {
        color: #002145;  /* UBC Blue */
        font-size: 2.5rem !important;
        margin-bottom: 2rem !important;
        text-align: center;
    }
    
    /* Chat message styling */
    .chat-message {
        padding: 1.5rem;
        border-radius: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        max-width: 80%;
    }
    
    .user-message {
        background-color: #002145;  /* UBC Blue */
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 0.2rem;
    }
    
    .bot-message {
        background-color: #f7f9fc;
        border: 1px solid #e1e4e8;
        margin-right: auto;
        border-bottom-left-radius: 0.2rem;
    }
    
    /* Course card styling */
    .course-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #e1e4e8;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }
    
    .course-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .score-badge {
        background-color: #0055B7;  /* UBC Secondary Blue */
        color: white;
        padding: 0.4rem 0.8rem;
        border-radius: 2rem;
        font-size: 0.9rem;
        float: right;
        font-weight: 500;
    }
    
    /* Form styling */
    .stTextInput > div > div > input {
        border-radius: 0.5rem;
    }
    
    .stButton > button {
        background-color: #002145;  /* UBC Blue */
        color: white;
        border-radius: 0.5rem;
        padding: 0.5rem 2rem;
        font-weight: 500;
        border: none;
        transition: background-color 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #003366;  /* Darker UBC Blue */
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: #f7f9fc;
    }
    
    /* Tips section styling */
    .tip-box {
        background-color: #e6f3ff;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
    }
    
    /* Course details styling */
    .course-title {
        color: #002145;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .course-description {
        color: #4a4a4a;
        font-size: 1rem;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'querier' not in st.session_state:
        st.session_state.querier = CourseQuery()

def display_message(message, is_user=False):
    message_class = "user-message" if is_user else "bot-message"
    st.markdown(f"""
        <div class="chat-message {message_class}">
            {message}
        </div>
    """, unsafe_allow_html=True)

def format_course_result(result):
    score = result['score']
    code = result['courseCode']
    name = result['name']
    description = result['description']
    
    return f"""
    <div class="course-card">
        <div class="score-badge">Match: {score:.2f}</div>
        <div class="course-title">{code}: {name}</div>
        <div class="course-description">{description}</div>
    </div>
    """

def main():
    initialize_session_state()
    
    # Header with UBC branding
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🎓 UBC Course Assistant")
    
    # Feature description
    st.markdown("""
    <div style='text-align: center; padding: 1rem; background-color: #f7f9fc; border-radius: 1rem; margin-bottom: 2rem;'>
        <h3 style='color: #002145;'>Your AI Course Discovery Assistant</h3>
        <p>Find the perfect courses using natural language search!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Chat interface in main column
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("### Chat History")
        
        # Chat history container
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                display_message(message['content'], message['is_user'])
        
        # Input form
        with st.form(key="chat_form", clear_on_submit=True):
            user_input = st.text_input(
                "Ask about courses:",
                placeholder="E.g., 'Show me courses about machine learning'",
                key="user_input"
            )
            
            cols = st.columns([1, 3, 1])
            with cols[0]:
                num_results = st.number_input(
                    "Results:",
                    min_value=1,
                    max_value=10,
                    value=2
                )
            with cols[2]:
                submit_button = st.form_submit_button("🔍 Search")
    
    if submit_button and user_input:
        # Add user message to chat
        st.session_state.messages.append({
            "content": user_input,
            "is_user": True
        })
        
        # Get course recommendations
        results = st.session_state.querier.search_courses(user_input, top_k=num_results)
        
        # Format response
        response = "<div class='response-container'>"
        for result in results:
            response += format_course_result(result)
        response += "</div>"
        
        # Add bot response to chat
        st.session_state.messages.append({
            "content": response,
            "is_user": False
        })
        
        # Rerun to update chat display
        st.rerun()

    # Sidebar with additional information
    with st.sidebar:
        st.markdown("### About")
        st.markdown("""
        This chatbot uses AI to help you find relevant UBC courses. 
        It searches through course descriptions and matches your query 
        with the most relevant courses using advanced natural language processing.
        
        **Tips for better results:**
        - Be specific about your interests
        - Mention relevant keywords
        - Ask about specific topics or skills
        """)
        
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

if __name__ == "__main__":
    main()
