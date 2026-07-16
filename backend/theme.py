import streamlit as st

def load_theme():

    st.set_page_config(
        page_title="RadarSaham",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown("""
    <style>

    .main{
        background-color:#F5F7FA;
    }

    h1,h2,h3{
        color:#1F2937;
    }

    .stMetric{
        background:white;
        border-radius:15px;
        padding:15px;
        box-shadow:0px 3px 12px rgba(0,0,0,0.08);
    }

    section[data-testid="stSidebar"]{
        background:#111827;
    }

    section[data-testid="stSidebar"] *{
        color:white;
    }

    </style>
    """, unsafe_allow_html=True)