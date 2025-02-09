import streamlit as st

st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            background:#ddcfb3;
        }
        [data-testid="stSidebar"] * {
            color: #1c4a30;
        }
    </style>
    """,
    unsafe_allow_html=True
)



# Initialize the session state for logged_in if it doesn't exist
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Define pages, including standalone pages and grouped pages
if st.session_state['logged_in']:
    # Exclude Login and Register pages for logged-in users
    pages = {
        "SecureShield": [
            st.Page("SecureShield/app_pages/Chatbot.py", title="Chatbot", icon="🤖")
        ]
    }
else:
    # Include Login and Register pages for logged-out users
    pages = {
        "SecureShield": [
            st.Page("SecureShield/app_pages/Chatbot.py", title="Chatbot", icon="🤖"),
            st.Page("SecureShield/app_pages/Login.py", title="Log in", icon="🔓")
        ]
    }

# Initialize the navigation
pg = st.navigation(pages)

# Run the navigation component
pg.run()

# Sidebar with the logout button, which only shows if logged in
with st.sidebar:
    if st.session_state['logged_in']:
        # Hide pages that are not relevant for logged-in users (Login and Register)
        if st.button("Log Out"):
            # Update session state on logout
            st.session_state['logged_in'] = False
            st.session_state['username'] = None
            st.sidebar.empty()  # Clear the logout button from the sidebar
    else:
        st.sidebar.empty()
