import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as gen_ai
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract
import sqlite3
from datetime import datetime

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configure Streamlit page
st.set_page_config(
    page_title="AI Learning Companion",
    page_icon=":brain:",
    layout="wide",
)

# Initialize Google Gemini-Pro AI
gen_ai.configure(api_key=GOOGLE_API_KEY)

# Set up database and connection
DB_NAME = "learning_companion.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn

def create_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Create tables for users, history, sessions, and profiles
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        email TEXT UNIQUE,
        password TEXT,
        profile_picture TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        topic TEXT,
        scheduled_time DATETIME,
        completed BOOLEAN DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id))''')

    conn.commit()
    conn.close()


# Gemini AI interaction
def ask_gemini_ai(prompt):
    if "chat_session" not in st.session_state:
        st.session_state.chat_session = gen_ai.GenerativeModel('gemini-pro').start_chat(history=[])

    response = st.session_state.chat_session.send_message(prompt)
    return response.text

# OCR for extracting text from images
def extract_text_from_image(image):
    return pytesseract.image_to_string(image)
      

# Initialize conversation session state
if 'conversation' not in st.session_state:
    st.session_state.conversation = []

# Initialize database
create_db()

# Initialize session state variables
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Sidebar logic
if st.session_state.logged_in:
    # User is logged in
    menu = ["Chat", "Profile"]
    choice = st.sidebar.selectbox("Menu", menu)
    st.sidebar.subheader("Welcome!")
    st.sidebar.write("You are logged in.")
    if choice == "Profile":
        # Profile settings
        st.subheader("Profile Settings")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE id = ?", (st.session_state.user_id,))
        user_info = cursor.fetchone()
        conn.close()

        email = st.text_input("Email", value=user_info[0], disabled=True)

        new_password = st.text_input("New Password", type='password')
        if st.button("Update Profile"):
            conn = get_connection()
            cursor = conn.cursor()
            if new_password:
                cursor.execute("UPDATE users SET email = ?, password = ? WHERE id = ?", (email, new_password, st.session_state.user_id))
            else:
                cursor.execute("UPDATE users SET email = ? WHERE id = ?", (email, st.session_state.user_id))
            conn.commit()
            conn.close()
            st.success("Profile updated!")

        # Displaying the scheduled learning sessions
        # Displaying the scheduled learning sessions
        st.subheader("📅 Scheduled Learning Sessions")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, topic, scheduled_time, completed FROM sessions WHERE user_id = ?", (st.session_state.user_id,))
        sessions = cursor.fetchall()
        for session in sessions:
            session_id = session[0]  # Get the session ID for updating
            st.write(f"Topic: {session[1]}, Time: {session[2]}, Status: {'Yes' if session[3] else 'Pending'}")
            
            # Button to mark the session as completed
            if not session[3]:  # Only show the button if the session is not completed
                if st.button(f"Complete Session {session_id}"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE sessions SET completed = 1 WHERE id = ?", (session_id,))
                    conn.commit()
                    conn.close()
                    st.success(f"Session '{session[1]}' marked as completed!")
                    st.rerun()  # Rerun to refresh the UI
        conn.close()

        # Logout button
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False  # Set logged-in state to False
            st.session_state.user_id = None  # Clear user ID
            st.success("Logged out successfully!")
            st.rerun()  # Rerun to refresh the UI


    elif choice == "Chat":
        if st.session_state.logged_in:
            # Layout setup for the logged-in user
            col2, col3 = st.columns([3, 1])
            with col3:

                # Schedule a new session
                st.subheader("Schedule a Learning Session")
                session_topic = st.text_input("Learning Topic")
                session_date = st.date_input("Scheduled Date")
                session_time = st.time_input("Scheduled Time")
                if st.button("Schedule"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    scheduled_datetime = datetime.combine(session_date, session_time)
                    cursor.execute("INSERT INTO sessions (user_id, topic, scheduled_time) VALUES (?, ?, ?)",
                                (st.session_state.user_id, session_topic, scheduled_datetime))
                    conn.commit()
                    st.success("Session scheduled!")
                    conn.close()

            # Center Column (Chat and Uploads)
            with col2:
                st.subheader("🤖 Chat with AI and Upload Documents")

                # Chat interaction
                user_input = st.text_input("Ask me anything:")
                if st.button("Learn"):
                    prompt = f"Give me a learning roadmap on {user_input}" 
                    response = ask_gemini_ai(prompt)
                    st.write(f"AI: {response}")
                    st.session_state.conversation.append((user_input, response))  # Store conversation

                    # Option to copy AI response
                    if st.button("📋 Copy AI Response"):
                        st.write(response)
                        st.success("Copied to clipboard!")

                # File upload for PDFs and images
                uploaded_file = st.file_uploader("Upload a PDF or Image", type=["pdf", "png", "jpg", "jpeg"])

                if uploaded_file is not None:
                    if uploaded_file.type == "application/pdf":
                        reader = PdfReader(uploaded_file)
                        text = "".join([page.extract_text() for page in reader.pages])
                        st.write("Extracted Text:", text)
                        st.session_state.conversation.append(("Uploaded PDF", text))  # Store conversation
                    else:
                        image = Image.open(uploaded_file)
                        text = extract_text_from_image(image)
                        st.write("Extracted Text:", text)
                        st.session_state.conversation.append(("Uploaded Image", text))  # Store conversation
                
                if st.sidebar.button("Logout"):
                    st.session_state.logged_in = False  # Set logged-in state to False
                    st.session_state.user_id = None  # Clear user ID
                    st.success("Logged out successfully!")
                    st.rerun()  # Rerun to refresh the UI


else:
    # User is not logged in
    menu = ["Login", "Register"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Register":
        st.subheader("Create New Account")
        email = st.text_input("Email")
        password = st.text_input("Password", type='password')
        
        if st.button("Register"):
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
                conn.commit()
                st.success("Registered! Please log in.")
            except sqlite3.IntegrityError:
                st.error("Email already exists.")
            finally:
                conn.close()

    if choice == "Login":
        st.subheader("Login to Your Account")
        email = st.text_input("Email")
        password = st.text_input("Password", type='password')
        
        if st.button("Login"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
            user = cursor.fetchone()
            conn.close()

            if user:
                st.session_state.user_id = user[0]  # Store user ID
                st.session_state.logged_in = True  # Set logged in state to True
                st.success("Logged in!")
                st.rerun()  # Rerun to refresh the UI
            else:
                st.error("Invalid email or password.")

# Run the application
if __name__ == "__main__":
    create_db()
