import streamlit as st


def kpi_card(title, value, delta=None):

    col = st.container(border=True)

    with col:

        st.markdown(
            f"### {title}"
        )

        st.metric(
            label="",
            value=value,
            delta=delta
        )

def section_header(title):

    st.markdown(f"""
    <div style="
        margin-top:20px;
        margin-bottom:10px;
        font-size:24px;
        font-weight:bold;
        color:#1F2937;
    ">
        {title}
    </div>
    """, unsafe_allow_html=True)

def status_badge(text, color="#22C55E"):

    st.markdown(f"""
    <div style="
        background:{color};
        color:white;
        padding:10px;
        border-radius:10px;
        text-align:center;
        font-weight:bold;
    ">
        {text}
    </div>
    """, unsafe_allow_html=True)

def info_card(title, value):

    with st.container(border=True):

        st.markdown(f"### {title}")

        st.write(value)

def footer():

    st.divider()

    st.caption(
        "RadarSaham v1.0 | Smart Indonesian Stock Analysis Platform"
    )