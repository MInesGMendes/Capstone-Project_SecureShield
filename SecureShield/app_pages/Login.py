import sqlitecloud
import streamlit as st
import time

# Database setup
conn = sqlite3.connect("secure_shield.db")  # Path to your SQLite database
cursor = conn.cursor()

# Helper Functions
def check_if_email_exists(email):
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM Employees WHERE email = ?", (email,))
    return cursor.fetchone() is not None

def verify_user(email, password):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Employees WHERE email = ? AND password = ?", (email, password))
    return cursor.fetchone()

def get_username_by_email(email):
    cursor = conn.cursor()
    cursor.execute("SELECT first_name FROM Employees WHERE email = ?", (email,))
    result = cursor.fetchone()
    return result[0] if result else None

# Login Form
st.title("Login")

with st.form("login_form"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    submit = st.form_submit_button("Login")

    if submit:
        if not email or not password:
            st.error("Please fill all fields")
            st.session_state.logged_in = False
        elif not check_if_email_exists(email):
            st.error("Email not registered")
            st.session_state.logged_in = False
        else:
            # Verify user with email and password
            user = verify_user(email, password)
            if user:
                # Fetch and store the username in session state
                username = get_username_by_email(email)
                st.session_state['username'] = username
                st.session_state['user_email'] = email
                st.session_state['logged_in'] = True
                
                st.success(f"Welcome, {username}!")
                update_user_conversation_id(username)
                time.sleep(1)
                st.switch_page("app_pages/Chatbot.py")
            else:
                st.error("Incorrect password")
                st.session_state.logged_in = False

