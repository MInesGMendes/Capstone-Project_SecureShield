import streamlit as st
import time
from dotenv import load_dotenv
from chatbot.bot import MainChatbot  # Import the chatbot class
import sqlitecloud  


# Function to check authentication
def check_auth():
    return 'logged_in' in st.session_state and st.session_state.logged_in

# Function to simulate streaming response
def simulate_streaming(message):
    buffer = ""
    for char in message:
        buffer += char
        if char in [" ", "\n"]:
            yield buffer.strip() + ("<br>" if char == "\n" else " ")
            buffer = ""
            time.sleep(0.1 if char == "\n" else 0.05)
    if buffer:
        yield buffer

# Authentication check
if not check_auth():
    st.warning("You need to login to access the chatbot.")
    if st.button("Go to Login Page"):
        st.switch_page("app_pages/Login.py")
else:
    st.title("Secure Shield Chatbot")

    username = st.session_state['username']


    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

     load_dotenv()
    # Accept user input
    if user_input := st.chat_input("Chat with SecureShield Chatbot"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        # Initialize the chatbot instance
        bot = MainChatbot()
        bot.user_login(username=username)

        with st.spinner('Thinking...'):
            try:
                # Process user input using the bot
                response = bot.process_user_input({"user_input": user_input})
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(response, unsafe_allow_html=True)
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
              st.error(f"Error: {str(e)}")
