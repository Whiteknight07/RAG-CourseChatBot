import streamlit as st
from query import CourseQuery
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="UBC Course Assistant",
    page_icon="🎓",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e6f3ff;
    }
    .bot-message {
        background-color: #f0f2f6;
    }
    .course-card {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        border: 1px solid #ddd;
    }
    .score-badge {
        background-color: #4CAF50;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        float: right;
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
        <div class="score-badge">{score:.2f}</div>
        <h4>{code}: {name}</h4>
        <p>{description}</p>
    </div>
    """

def main():
    initialize_session_state()
    
    # Header
    st.title("🎓 UBC Course Assistant")
    st.markdown("""
    Ask me anything about UBC courses! I can help you:
    - Find courses by topic or content
    - Learn about course descriptions and prerequisites
    - Discover similar courses
    - Understand course requirements
    """)
    
    # Chat interface
    st.markdown("### Chat")
    
    # Display chat history
    for message in st.session_state.messages:
        display_message(message['content'], message['is_user'])
    
    # User input
    with st.form(key="chat_form"):
        user_input = st.text_input("Type your question here:", key="user_input")
        col1, col2 = st.columns([1, 5])
        with col1:
            num_results = st.number_input("Number of results:", min_value=1, max_value=10, value=2)
        with col2:
            submit_button = st.form_submit_button("Ask")
    
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
