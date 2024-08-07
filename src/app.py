import os
import tempfile
import streamlit as st
from streamlit_chat import message
from streamlit_option_menu import option_menu
from rag import ChatPDF

# st.set_page_config(page_title="ChatPDF")
# page_bg="""
# <style>
# [data-testid = "stAppViewContainer"]{
# background-color : #3364FF;
# text-color : #FFFFFF;
# }
# <style>
# """
# st.markdown(page_bg, unsafe_allow_html=True)

def Teknic():
    st.subheader("Please improve me with new knowledge")
    st.file_uploader(
        "Upload document",
        type=["pdf"],
        key="file_uploader",
        on_change=read_and_save_file,
        label_visibility="collapsed",
        accept_multiple_files=True,
    )

def display_messages():
    
    for i, (msg, is_user) in enumerate(st.session_state["messages"]):
        message(msg, is_user=is_user, key=str(i))
    st.session_state["thinking_spinner"] = st.empty()


def process_input():
    if st.session_state["user_input"] and len(st.session_state["user_input"].strip()) > 0:
        user_text = st.session_state["user_input"].strip()
        with st.session_state["thinking_spinner"], st.spinner(f"Thinking"):
            agent_text = st.session_state["assistant"].ask(user_text)

        st.session_state["messages"].append((user_text, True))
        st.session_state["messages"].append((agent_text, False))


def read_and_save_file():
    st.session_state["assistant"].clear()
    st.session_state["messages"] = []
    st.session_state["user_input"] = ""

    for file in st.session_state["file_uploader"]:
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(file.getbuffer())
            file_path = tf.name

        with st.session_state["ingestion_spinner"], st.spinner(f"Ingesting {file.name}"):
            st.session_state["assistant"].ingest(file_path)
        os.remove(file_path)


def page():
    if len(st.session_state) == 0:
        st.session_state["messages"] = []
        st.session_state["assistant"] = ChatPDF()
    svg_path="svg/logo-no-background.svg"
    # st.title("Gheorghe") 
    st.image(svg_path,width = 400)
    options = ["General", "Teknic"]
    
    with st.sidebar:
        toggle_switch = st.checkbox("Do you have rights?")

    
        if toggle_switch:
            st.write("Admin")
            # options.append("HRista")

        else:
            st.write("User")
        
        selected = option_menu(
            menu_title = "Gheorghe",
            options = options
        )
        

    if selected == "General":
        st.title(f"Welcome to {selected}")

    if selected == "Teknic":
        st.title(f"Welcome to {selected}")
        if toggle_switch:
            Teknic()
        
    if selected == "HRista":
        st.title(f"Welcome to {selected}")
        if toggle_switch:
            HRista()
    st.subheader(f"Explore what {selected} has to offer")
    

    st.session_state["ingestion_spinner"] = st.empty()

    display_messages()
    st.text_input("Message", key="user_input", on_change=process_input)
        


if __name__ == "__main__":
    page()