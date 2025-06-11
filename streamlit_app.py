# Question and Answer on a Given Topic 
# Topic file is uploaded as a Text

import streamlit as st
from openai import OpenAI
from QnA_Utils import fetch_pdf_in_chunks
from PyPDF2 import PdfReader
import subprocess
from datetime import datetime
import pytz
from github import Github, GithubException
import base64
#import re
#import json
# GitHub raw URL
GITHUB_RAW_URL = "https://raw.githubusercontent.com/UnniAmbady/BAS-Quiz/main/BAS_Notes.pdf"


# deifine global variables
if "sys_qn" not in st.session_state:
    st.session_state.sys_qn = "Q yet to come"
if "sys_ans" not in st.session_state:
    st.session_state.sys_ans = "Ans not ready"
if "st_answer" not in st.session_state:
    st.session_state.st_answer = "student to answer"
if "st_answered" not in st.session_state:
    st.session_state.st_answered = 0


# Show title and description.
st.title("📄 BAS Knowledge Test🎈")
st.write("Read your lecture notes & refer to the PDF before answering. "
    "Students need to answer at least 2 Questions.")


query = "Create a random Question with an Answer. Answer must be short."
document = None  # Initially set to None to indicate no document is uploaded
uploaded_file = None  # Define uploaded_file ly

#parse
# Function to parse the input string

def extract_question_and_answer(generated_content):
    
    """
    Extracts the question and answer from a given string based on the keywords 'Question:' and 'Answer:'.
    
    Parameters:
        generated_content (str): The input string containing the question and answer.
        
    Returns:
        tuple: A tuple containing the question (qn) and the answer (ans).
    """
    try:
        # Split the content into parts based on the keywords
        question_part = generated_content.split("Question:", 1)[-1]
        answer_part = question_part.split("Answer:", 1)
        
        # Extract the question and answer
        qn = answer_part[0].strip()  # Question part
        ans = answer_part[1].strip() if len(answer_part) > 1 else ""  # Answer part
        # Remove '**' from the question and answer
        qn = qn.replace("**", "")
        ans = ans.replace("**", "")
        return qn, ans
    except Exception as e:
        raise ValueError(f"Error parsing content: {e}")
#end of parsing


# Define the function to be called when the button is clicked
def AskQn():
    # Placeholder for future implementation
    global document, query   # Access the global variables
 
    # Conditionally avoid redundant parsing of the file
    if not document:
        document = uploaded_file.read().decode()

    #messages = [
    #    {"role": "system", "content": f"Keep the scope of answering strictly within the context of the document: {document}."},
    #    {"role": "system", "content": f"If a question is not within the scope of the document, respond with 'I am not sure'."},
    #    {"role": "user", "content": f"Here's a document: {document} \n\n---\n\n {query}"}
    #]
    messages = [
        {	"role": "system",
            "content": (
                "You are a question generator. Keep the scope of your questions strictly within the context "
                "of the document below. Pick a random sub-topic or fact from the document and use *only* that "
                "to form a question. Don’t pick the same fact twice in a row. If you cannot form a question "
                "based on the document, respond with 'I am not sure'." )
        },
        {   "role": "user",
            "content": f"Here’s the document:\n\n{document}\n\n---\n\n{query}"
        }
            ]

    
                # Generate an answer using the OpenAI API.
    stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=False)
    generated_content = stream.choices[0].message.content
    sys_qn, sys_ans = extract_question_and_answer(generated_content)
    st.write(sys_qn)
    # if(not hide_ans):
        # st.write(sys_ans)  
    return sys_qn, sys_ans
#function ended

# Add the Validate function
def Validate():
    sys_qn = st.session_state.sys_qn
    sys_ans = st.session_state.sys_ans
    st_answer = st.session_state.st_answer

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

    # Extract structured feedback
    right_feedback, improve_feedback, score_feedback = analyse_n_feedback(stream1)

    # Display clearly structured feedback
    st.markdown(f"**Question:** {sys_qn}")
    st.markdown(f"**Modal Answer:** {sys_ans}")
    st.markdown(f"**Your Answer:** {st_answer}")

    st.markdown(f"**Feedback:**")
    st.markdown(f"**✔️ Right:** {right_feedback}")
    st.markdown(f"**⚠️ Improve:** {improve_feedback}")
    st.markdown(f"**📌 Score:** {score_feedback}")

    # Log everything to GitHub
    analysis_text = (
        f"Right points: {right_feedback}\n"
        f"Improve on: {improve_feedback}\n"
        f"Score: {score_feedback}\n"
    )

    log_and_commit(sys_qn, sys_ans, st_answer, analysis_text)
    #st.success("✅ Logged to GitHub.")
    #Messging included inside the function
    return




def log_and_commit(sys_qn: str, sys_ans: str, st_ans: str, analysis_text: str):
    """
    Logs question, answers, and GPT feedback analysis into GitHub.
    """
    # Authenticate
    github_token = st.secrets["github"]["token"]
    gh = Github(github_token)
    repo = gh.get_repo("UnniAmbady/BAS-Quiz")

    # Prepare the log entry
    ts = datetime.now(pytz.timezone("Asia/Singapore")).strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"Timestamp:    {ts}\n"
        f"Question:     {sys_qn}\n"
        f"Modal Answer: {sys_ans}\n"
        f"Student Ans:  {st_ans}\n\n"
        f"GPT Feedback:\n{analysis_text}\n"
        + "-" * 60 + "\n"
    )

    # Update/create Activity_log.txt
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
        st.success("✅ Responce recorded.")
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

    # 3) (Optional) ensure the workflow YAML exists
    #YAML already created and hence code removed
    return

def analyse_n_feedback(stream1):
    """
    Extracts 'Right:', 'Improve:', and 'Score:' from stream1's response.
    
    Parameters:
        stream1: ChatGPT response object (stream=False).
        
    Returns:
        tuple: (right_feedback, improve_feedback, score_feedback)
    """
    try:
        generated_content = stream1.choices[0].message.content.strip()

        # Extract sections
        right_part = generated_content.split("Right:", 1)[-1].split("Improve:", 1)[0].strip()
        improve_part = generated_content.split("Improve:", 1)[-1].split("Score:", 1)[0].strip()
        score_part = generated_content.split("Score:", 1)[-1].strip()

        return right_part, improve_part, score_part
    except Exception as e:
        raise ValueError(f"Error parsing feedback: {e}")
    return

### __mail__ body Starts from here

# openai_api_key = st.text_input("OpenAI API Key", type="password")
openai_api_key = st.secrets["openai"]["secret_key"]
client = OpenAI(api_key=openai_api_key)

if not client:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    # Streamlit app layout
    st.title("Interactive Q&A Generator")
    pdf_data = fetch_pdf_in_chunks(GITHUB_RAW_URL)

    if pdf_data:
        reader = PdfReader(pdf_data)
        document = ""
        for page in reader.pages:
            document += page.extract_text() or ""
    else:
        st.error("Failed to load BAS_Notes.pdf from GitHub.")
        st.stop()
        
    uploaded_file= document #used back old variable name

    if uploaded_file:             
        if st.button("Ask Question"):         
            sys_qn, sys_ans = AskQn()
            st.session_state.sys_qn =sys_qn
            st.session_state.sys_ans =sys_ans
            
        if st_answer := st.chat_input("Type (Your Name) and answer here:"):
            st.session_state.st_answer = st_answer
            st.session_state.st_answered = 1
            #save_global(sys_qn, sys_ans, st_answer)              
            Validate()     
    
  
    if not uploaded_file:
        st.write("Upload a file before you can ask a Question.")
        




