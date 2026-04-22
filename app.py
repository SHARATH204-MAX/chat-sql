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

st.set_page_config(page_title="SQL Intelligence - AI Data Assistant", page_icon="💠", layout="wide")

# Custom CSS for Premium UI
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #0e1117;
        background-image: 
            radial-gradient(at 0% 0%, rgba(0, 210, 255, 0.1) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(58, 123, 213, 0.1) 0px, transparent 50%);
    }

    [data-testid="stSidebar"] {
        background: rgba(23, 28, 41, 0.7);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    .main-header {
        font-size: 3rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #00d2ff 0%, #3a7bd5 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }

    .sub-header {
        color: rgba(255, 255, 255, 0.6) !important;
        font-size: 1.1rem !important;
        margin-top: -10px !important;
        margin-bottom: 2rem !important;
    }

    /* Glassmorphic Chat Container */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 15px !important;
        padding: 1rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
    }

    /* Input area styling */
    .stChatInput {
        border-radius: 12px !important;
        border: 1px solid rgba(0, 210, 255, 0.2) !important;
    }

    /* Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 8px !important;
        background: linear-gradient(135deg, #00d2ff 0%, #3a7bd5 100%) !important;
        color: white !important;
        border: none !important;
        transition: all 0.3s ease !important;
    }

    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 15px rgba(0, 210, 255, 0.3) !important;
    }

    /* Sidebar text inputs */
    [data-testid="stTextInput"] input {
        background: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }

    /* Hide default streamlit menu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

st.markdown('<h1 class="main-header">SQL Intelligence</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Advanced AI-Powered Data Assistant</p>', unsafe_allow_html=True)

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

llm=ChatGroq(groq_api_key=api_key,model_name="llama-3.3-70b-versatile",streaming=True)

@st.cache_resource(ttl="2h")
def configure_db(db_uri,mysql_host=None,mysql_user=None,mysql_password=None,mysql_db=None):
    if db_uri==LOCALDB:
        dbfilepath=(Path(__file__).parent/"student.db").absolute()
        print(dbfilepath)
        creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)
        return SQLDatabase(create_engine("sqlite:///", creator=creator), include_tables=['STUDENT'])
    elif db_uri==MYSQL:
        if not (mysql_host and mysql_user and mysql_password and mysql_db):
            st.error("Please provide all MySQL connection details.")
            st.stop()
        return SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"))   
    
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
    prefix=prefix
)

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

user_query=st.chat_input(placeholder="Ask anything from the database")

# Prioritize voice input if available
if voice_text:
    user_query = voice_text

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

        


