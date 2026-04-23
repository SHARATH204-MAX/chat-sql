import streamlit as st
from pathlib import Path
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.callbacks import StreamlitCallbackHandler
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
from streamlit_mic_recorder import speech_to_text

load_dotenv()

st.set_page_config(page_title="🦜LangChain: Chat with SQL DB", page_icon="🦜", layout="wide")

# Custom CSS for Premium UI with High Visibility
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #0e1117;
        color: #ffffff; /* Global high contrast text */
    }

    [data-testid="stHeader"] {
        background: rgba(0,0,0,0);
    }

    [data-testid="stSidebar"] {
        background: rgba(23, 28, 41, 0.85);
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* Original Title Styling */
    h1 {
        font-weight: 800 !important;
        color: #ffffff !important;
        margin-bottom: 1.5rem !important;
    }

    /* High Visibility Chat Bubbles */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #ffffff !important;
        border-radius: 12px !important;
    }

    .stChatMessage p, .stChatMessage div {
        color: #ffffff !important; /* Ensure text inside bubbles is white */
        font-size: 1rem !important;
    }

    /* Sidebar Text visibility */
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* Input area styling */
    .stChatInput {
        background: #1e232d !important;
        border: 1px solid rgba(0, 210, 255, 0.3) !important;
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #00d2ff 0%, #3a7bd5 100%) !important;
        color: white !important;
        font-weight: 700 !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

st.title("🦜 LangChain: Chat with SQL DB")

LOCALDB="USE_LOCALDB"
MYSQL="USE_MYSQL"

radio_opt=["Use SQLLite 3 Database- Student.db","Connect to you MySQL Database"]

selected_opt=st.sidebar.radio(label="Choose the DB which you want to chat",options=radio_opt)

if radio_opt.index(selected_opt)==1:
    db_uri=MYSQL
    mysql_host=st.sidebar.text_input("Provide MySQL Host")
    mysql_user=st.sidebar.text_input("MYSQL User")
    mysql_password=st.sidebar.text_input("MYSQL password",type="password")
    mysql_db=st.sidebar.text_input("MySQL database")
else:
    db_uri=LOCALDB

api_key=st.sidebar.text_input(label="Groq API Key",type="password", value=os.getenv("GROQ_API_KEY", ""))

if not db_uri:
    st.info("Please enter the database information and uri")

if not api_key:
    st.info("Please add the groq api key")

## Voice Input in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🎙️ Voice Input")
voice_text = speech_to_text(
    language='en', 
    start_prompt="Start Recording", 
    stop_prompt="Stop Recording", 
    just_once=False, 
    key='STT'
)

if not api_key:
    st.info("Please add the groq api key in the sidebar to begin.")
    st.stop()

llm=ChatGroq(groq_api_key=api_key,model_name="llama-3.3-70b-versatile",streaming=True, max_retries=2, timeout=60)

@st.cache_resource(ttl="2h")
def configure_db(db_uri,mysql_host=None,mysql_user=None,mysql_password=None,mysql_db=None):
    try:
        if db_uri==LOCALDB:
            dbfilepath=(Path(__file__).parent/"student.db").absolute()
            creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)
            return SQLDatabase(create_engine("sqlite:///", creator=creator), include_tables=['STUDENT', 'DEPARTMENTS'])
        elif db_uri==MYSQL:
            if not (mysql_host and mysql_user and mysql_password and mysql_db):
                st.error("Please provide all MySQL connection details.")
                st.stop()
            return SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"))   
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        st.stop()
    
if db_uri==MYSQL:
    db=configure_db(db_uri,mysql_host,mysql_user,mysql_password,mysql_db)
else:
    db=configure_db(db_uri)

## toolkit
toolkit=SQLDatabaseToolkit(db=db,llm=llm)

prefix = """You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct sqlite query to run, then look at the results of the query and return the answer.
If the query returns no results, your Final Answer should be "No records found matching your criteria."
ALWAYS follow the format:
Thought: <your reasoning>
Action: <tool name>
Action Input: <tool input>
Observation: <tool output>
... (repeat if needed)
Thought: I now know the final answer
Final Answer: <your final response>
"""


if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

agent=create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type="zero-shot-react-description",
    handle_parsing_errors=True,
    prefix=prefix,
    max_iterations=10,
    max_execution_time=60,
    early_stopping_method="generate"
)

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

user_query=st.chat_input(placeholder="Ask anything from the database")

# Prioritize voice input if available
if voice_text:
    user_query = voice_text

if user_query:
    user_query = user_query.strip()
    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        streamlit_callback=StreamlitCallbackHandler(st.container())
        
        # Manual history injection for context
        history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-6:-1]])
        enhanced_query = f"Previous Conversation:\n{history_context}\n\nCurrent Question: {user_query}"
        
        response=agent.run(enhanced_query,callbacks=[streamlit_callback])
        st.session_state.messages.append({"role":"assistant","content":response})
        st.write(response)

        


