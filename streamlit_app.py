import streamlit as st
from openai import OpenAI
from QnA_Utils import fetch_pdf_in_chunks
from PyPDF2 import PdfReader
from datetime import datetime
import pytz
from github import Github, GithubException

GITHUB_RAW_URL = "https://raw.githubusercontent.com/UnniAmbady/BAS-Quiz/main/BAS_Notes.pdf"

# --- GLOBAL STATE ---
if "Name" not in st.session_state:
    st.session_state.Name = ""
if "asked_name" not in st.session_state:
    st.session_state.asked_name = False
if "sys_qn" not in st.session_state:
    st.session_state.sys_qn = "Q yet to come"
if "sys_ans" not in st.session_state:
    st.session_state.sys_ans = "Ans not ready"
if "st_answer" not in st.session_state:
    st.session_state.st_answer = "student to answer"
if "st_answered" not in st.session_state:
    st.session_state.st_answered = 0

# --- ASK FOR NAME IN MODAL/POPUP ---



def ask_name_popup():
    st.title("📄 BAS Knowledge Test🎈")
    st.warning("Please enter your Name to begin:")
    name = st.text_input("Enter your Name:", key="input_name")
    if st.button("Submit Name"):
        if name.strip():
            st.session_state.Name = name.strip()  # set the name in session state
            #return True  # indicate success
            st.session_state.asked_name = True  # <--- NEW LINE
            st.stop() 
        else:
            st.error("Name cannot be blank.")
    return False  # not yet submitted


if not st.session_state.Name:
    st.title("📄 BAS Knowledge Test🎈")
    st.warning("Please enter your Name to begin:")
    name = st.chat_input("Please enter your Name to begin:")
    if name:
        st.session_state.Name = name.strip()
        st.session_state.asked_name = True #Unni Added
        st.stop() 
    st.stop() 
else:
    # --- Show title, Name and description ---
    st.title("📄 BAS Knowledge Test🎈")
    st.write(f"Name: {st.session_state.Name}")
    st.write("Read your lecture notes & refer to the PDF before answering. "
        "Students need to answer at least 2 Questions.")

    query = "Create a random Question with an Answer. Answer must be short."
    document = None
    uploaded_file = None

    # (Rest of your parsing, extract_question_and_answer, and other utility functions here...)

def extract_question_and_answer(generated_content):
    try:
        question_part = generated_content.split("Question:", 1)[-1]
        answer_part = question_part.split("Answer:", 1)
        qn = answer_part[0].strip()
        ans = answer_part[1].strip() if len(answer_part) > 1 else ""
        qn = qn.replace("**", "")
        ans = ans.replace("**", "")
        return qn, ans
    except Exception as e:
        raise ValueError(f"Error parsing content: {e}")

def AskQn():
    global document, query
    if not document:
        document = uploaded_file.read().decode() if hasattr(uploaded_file, "read") else uploaded_file

    messages = [
        {"role": "system",
         "content": (
             "You are a question generator." 
             "To ensure variety, first pick a random starting offset between 0% and 100% of the document below." 
             "Begin scanning for a fact or sub-topic starting at that offset, and use only what you find nearby to create a unique question." 
             "Never use the same part of the document or repeat a question." 
             "If you cannot find a suitable new topic, respond with 'I am not sure.'"  )
        },
        {"role": "user",
         "content": f"Here’s the document:\n\n{document}\n\n---\n\n{query}"
        }
    ]

    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=False)
    generated_content = stream.choices[0].message.content
    sys_qn, sys_ans = extract_question_and_answer(generated_content)
    st.write(sys_qn)
    return sys_qn, sys_ans

def Validate():
    sys_qn = st.session_state.sys_qn
    sys_ans = st.session_state.sys_ans
    st_answer = st.session_state.st_answer
    Name = st.session_state.Name

    st.write("Thanks: The results will be sent to you at a later date.")

    messages = [{
        "role": "user",
        "content": f"[Ignore Grammar and Spelling errors]. "
                   f"[Respond in short sentences as brief as possible] "
                   f"[Compare and Comment with keyword `Right:` list the correct part of answer] "
                   f"[Compare and Comment with keyword `Improve:` list the incorrect part of answer, with needful corrections] "
                   f"[Be very lenient & don't flash too many errors. compute a higher grade, cap at 90%] "
                   f"[Based on the logical correctness, **AWARD** a Grade 0 to 100% scale with keyword `Score:`] "
                   f"\n\nCorrect Answer: {sys_ans}\n\nStudent Answer: {st_answer}"
    }]

    stream1 = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        temperature=0.6,
        stream=False
    )

    right_feedback, improve_feedback, score_feedback = analyse_n_feedback(stream1)

    # Show feedback -- MODIFIED LINE HERE:
    st.markdown(f"**Question:** {sys_qn}")
    st.markdown(f"**Modal Answer:** {sys_ans}")
    st.markdown(f"**Your Answer:** {st_answer}")

    st.markdown(f"**Feedback to :** {Name}")    # <-- Changed per request
    st.markdown(f"**✔️ Right:** {right_feedback}")
    st.markdown(f"**⚠️ Improve:** {improve_feedback}")
    st.markdown(f"**📌 Score:** {score_feedback}")

    # Log everything to GitHub, now include Name
    analysis_text = (
        f"Right points: {right_feedback}\n"
        f"Improve on: {improve_feedback}\n"
        f"Score: {score_feedback}\n"
    )
    log_and_commit(sys_qn, sys_ans, st_answer, analysis_text, Name)
    return

def log_and_commit(sys_qn: str, sys_ans: str, st_ans: str, analysis_text: str, Name: str):
    github_token = st.secrets["github"]["token"]
    gh = Github(github_token)
    repo = gh.get_repo("UnniAmbady/BAS-Quiz")
    ts = datetime.now(pytz.timezone("Asia/Singapore")).strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"Timestamp:    {ts}\n"
        f"Name:         {Name}\n"                  # <-- Name included in log
        f"Question:     {sys_qn}\n"
        f"Modal Answer: {sys_ans}\n"
        f"Student Ans:  {st_ans}\n\n"
        f"GPT Feedback:\n{analysis_text}\n"
        + "-" * 60 + "\n"
    )
    log_path = "Activity_log.txt"
    try:
        existing = repo.get_contents(log_path, ref="main")
        new_body = existing.decoded_content.decode() + entry
        repo.update_file(
            path=log_path,
            message=f"Update log at {ts}",
            content=new_body,
            sha=existing.sha,
            branch="main"
        )
        st.success("✅ Response recorded.")
    except GithubException as e:
        if e.status == 404:
            repo.create_file(
                path=log_path,
                message=f"Create log at {ts}",
                content=entry,
                branch="main"
            )
            st.success("✅ Activity_log.txt created")
        else:
            raise

def analyse_n_feedback(stream1):
    try:
        generated_content = stream1.choices[0].message.content.strip()
        right_part = generated_content.split("Right:", 1)[-1].split("Improve:", 1)[0].strip()
        improve_part = generated_content.split("Improve:", 1)[-1].split("Score:", 1)[0].strip()
        score_part = generated_content.split("Score:", 1)[-1].strip()
        return right_part, improve_part, score_part
    except Exception as e:
        raise ValueError(f"Error parsing feedback: {e}")
    return

# --- OPENAI CLIENT INIT ---
openai_api_key = st.secrets["openai"]["secret_key"]
client = OpenAI(api_key=openai_api_key)

# --- LOAD THE DOCUMENT ---
pdf_data = fetch_pdf_in_chunks(GITHUB_RAW_URL)
if pdf_data:
    reader = PdfReader(pdf_data)
    document = ""
    for page in reader.pages:
        document += page.extract_text() or ""
else:
    st.error("Failed to load BAS_Notes.pdf from GitHub.")
    st.stop()

uploaded_file = document

# --- MAIN APP FLOW ---
if uploaded_file:             
    if st.button("Ask Question"):         
        sys_qn, sys_ans = AskQn()
        st.session_state.sys_qn = sys_qn
        st.session_state.sys_ans = sys_ans
            
    if st_answer := st.chat_input(f"{st.session_state.Name}, type your answer here:"):
        st.session_state.st_answer = st_answer
        st.session_state.st_answered = 1
        Validate()     
else:
    st.write("Upload a file before you can ask a Question.")
