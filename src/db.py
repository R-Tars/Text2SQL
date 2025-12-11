import os
import streamlit as st
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase

# Load environment variables
load_dotenv()

@st.cache_resource
def get_db_connection():
    """
    Establishes and caches the database connection.
    """
    db_uri = os.getenv("DATABASE_URL")
    if not db_uri:
        st.error("Please set DATABASE_URL in your .env file.")
        return None
    
    try:
        # Using LangChain's SQLDatabase wrapper directly
        db = SQLDatabase.from_uri(db_uri)
        return db
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        return None

def get_schema(db):
    """
    Returns the schema information of the connected database.
    """
    if db:
        return db.get_table_info()
    return ""



