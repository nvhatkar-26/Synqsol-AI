import streamlit as st
import json
import random
from google import genai
from dotenv import load_dotenv
import os

# --- INITIAL SETUP ---
st.set_page_config(page_title="Synqsol AI Agent", page_icon="🧠")

load_dotenv()
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

class SynqsolAgent:
    def __init__(self, bank_path='question_bank.json'):
        self.bank_path = bank_path

    def load_questions(self):
        try:
            with open(self.bank_path, 'r', encoding='utf-8') as f:
                all_q = json.load(f)
            final_selection = all_q
            random.shuffle(final_selection)
            return final_selection
        except Exception as e:
            st.error(f"Error loading JSON: {e}")
            return []

    def calculate_results(self, responses):
        dims = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
        metrics = {}
        for d in dims:
            scores = [r['score'] for r in responses if r['dimension'] == d]
            if len(scores) > 0:
                avg = sum(scores) / len(scores)
                metrics[d] = round((avg / 5) * 100, 2)
            else:
                metrics[d] = 0.0
        overall_pct = round(sum(metrics.values()) / 5, 2)
        return overall_pct, metrics

    def generate_report(self, name, overall_pct, metrics, responses):
        # Switching to gemini-1.5-flash for better quota stability
        prompt = f"Analyze results for {name}. Overall: {overall_pct}%. Traits: {metrics}. Responses: {responses}"
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            if "429" in str(e):
                return "AI_BUSY_ERROR"
            return f"Report Error: {e}"

# --- SESSION STATE ---
if 'test_started' not in st.session_state:
    st.session_state.test_started = False
if 'current_q' not in st.session_state:
    st.session_state.current_q = 0
if 'responses' not in st.session_state:
    st.session_state.responses = []
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'final_report' not in st.session_state:
    st.session_state.final_report = None
if 'name' not in st.session_state:
    st.session_state.name = ""

agent = SynqsolAgent()

# --- STAGE 1: WELCOME ---
if not st.session_state.test_started and st.session_state.final_report is None:
    st.title("🧠 Synqsol Assessment")
    input_name = st.text_input("Candidate Name", value=st.session_state.name)
    
    if st.button("🚀 Start Basic Test"):
        if input_name:
            st.session_state.name = input_name
            qs = agent.load_questions()
            if len(qs) > 0:
                st.session_state.questions = qs
                st.session_state.test_started = True
                st.rerun()
            else:
                st.error("No questions found in question_bank.json.")
        else:
            st.warning("Please enter your name.")

# --- STAGE 2: TEST LOOP ---
elif st.session_state.test_started:
    q_idx = st.session_state.current_q
    total_q = len(st.session_state.questions)
    q = st.session_state.questions[q_idx]
    
    st.progress((q_idx + 1) / total_q)
    st.subheader(f"Question {q_idx + 1} of {total_q}")
    st.write(f"### {q['text']}")

    options = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
    choice = st.radio("Response:", options, index=2, key=f"q_{q_idx}")

    if st.button("Next ➡️" if q_idx < (total_q - 1) else "Finish ✅"):
        score = options.index(choice) + 1
        if str(q.get('level')) == "R":
            score = 6 - score
            
        st.session_state.responses.append({"dimension": q['dimension'], "score": score, "text": q['text']})

        if q_idx < (total_q - 1):
            st.session_state.current_q += 1
            st.rerun()
        else:
            with st.spinner("Analyzing with AI..."):
                overall_pct, metrics = agent.calculate_results(st.session_state.responses)
                st.session_state.overall_pct = overall_pct
                st.session_state.metrics = metrics
                # FIXED: Using st.session_state.name instead of 'name'
                st.session_state.final_report = agent.generate_report(
                    st.session_state.name, 
                    overall_pct, 
                    metrics, 
                    st.session_state.responses
                )
                st.session_state.test_started = False
                st.rerun()

# --- STAGE 3: REPORT ---
elif st.session_state.final_report:
    st.title(f"Report: {st.session_state.name}")
    st.metric("Overall Score", f"{st.session_state.overall_pct}%")
    
    if st.session_state.final_report == "AI_BUSY_ERROR":
        st.warning("🕒 The AI is currently busy. Please wait 60 seconds.")
        if st.button("🔄 Retry Generating Report"):
            with st.spinner("Retrying..."):
                st.session_state.final_report = agent.generate_report(
                    st.session_state.name, 
                    st.session_state.overall_pct, 
                    st.session_state.metrics, 
                    st.session_state.responses
                )
                st.rerun()
    else:
        st.json(st.session_state.metrics)
        st.markdown("---")
        st.markdown(st.session_state.final_report)
    
    if st.button("🔄 Restart New Test"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()