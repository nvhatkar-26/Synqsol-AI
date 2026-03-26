import streamlit as st
import json
import random
from google import genai
from dotenv import load_dotenv
import os

# --- INITIAL SETUP ---
st.set_page_config(page_title="Synqsol AI Agent", page_icon="🧠", layout="wide")

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
            # Ensure we always have exactly 20 questions for the Basic Test
            random.shuffle(all_q)
            return all_q[:20] 
        except Exception as e:
            st.error(f"Error loading JSON: {e}")
            return []

    def calculate_results(self, responses):
        dims = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
        metrics = {}
        for d in dims:
            scores = [r['score'] for r in responses if r['dimension'] == d]
            if len(scores) > 0:
                avg_raw_score = sum(scores) / len(scores)
                dimension_pct = ((avg_raw_score - 1) / 4) * 100
                metrics[d] = round(dimension_pct, 2)
            else:
                metrics[d] = 0.0
        overall_pct = round(sum(metrics.values()) / 5, 2)
        return overall_pct, metrics

    def generate_report(self, name, overall_pct, metrics):
        prompt = f"""
        Generate a professional Synqsol personality report for {name}.
        Overall Score: {overall_pct}%
        Dimension Scores: {metrics}

        STRICT FORMATTING RULES:
        - Do NOT use square brackets. Use '##' for headings.
        - 'Detailed Dimension Analysis' must be a descriptive paragraph for each trait.
        
        REPORT STRUCTURE:
        ## Executive Summary
        (4-line overview)

        ## Detailed Dimension Analysis
        (A 2-3 sentence descriptive paragraph for each of the five traits)

        ## Key Strengths
        (3 detailed bullet points)

        ## Development Opportunities
        (2 actionable areas for improvement)
        """
        try:
            response = client.models.generate_content(
                model="models/gemini-3.1-flash-lite-preview",
                contents=prompt
            )
            return response.text
        except Exception as e:
            return "AI_BUSY_ERROR" if "429" in str(e) else f"Report Error: {e}"

# --- SECURE SESSION STATE INITIALIZATION ---
def init_state(force_reset=False):
    if force_reset:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
    
    defaults = {
        'test_started': False,
        'current_q': 0,
        'responses': [],
        'questions': [],
        'final_report': None,
        'name': "",
        'overall_pct': 0,
        'metrics': {}
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_state()
agent = SynqsolAgent()

# --- STAGE 1: WELCOME ---
if not st.session_state.test_started and st.session_state.final_report is None:
    st.title("🧠 Synqsol Assessment")
    st.write("Welcome to the Synqsol Basic Personality Test.")
    
    input_name = st.text_input("Candidate Name", value=st.session_state.name)
    
    if st.button("🚀 Start Test"):
        if input_name:
            st.session_state.name = input_name
            st.session_state.questions = agent.load_questions()
            st.session_state.current_q = 0  # Reset counter
            st.session_state.responses = [] # Clear old answers
            st.session_state.test_started = True
            st.rerun()
        else:
            st.warning("Please enter a name to begin.")

# --- STAGE 2: TEST LOOP ---
elif st.session_state.test_started:
    q_idx = st.session_state.current_q
    total_q = len(st.session_state.questions)
    
    if q_idx < total_q:
        q = st.session_state.questions[q_idx]
        st.progress((q_idx + 1) / total_q)
        st.subheader(f"Question {q_idx + 1} of {total_q}")
        st.write(f"### {q['text']}")

        options = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
        # Default index 2 is 'Neutral'
        choice = st.radio("Select your response:", options, index=2, key=f"q_radio_{q_idx}")

        if st.button("Next ➡️" if q_idx < (total_q - 1) else "Finish ✅"):
            score = options.index(choice) + 1
            if str(q.get('level')).upper() == "R":
                score = 6 - score
            
            # Save response
            st.session_state.responses.append({"dimension": q['dimension'], "score": score})
            
            if q_idx < (total_q - 1):
                st.session_state.current_q += 1
                st.rerun()
            else:
                # FINAL STEP: CALCULATE AND GENERATE
                with st.spinner("Analyzing your profile..."):
                    o_pct, m = agent.calculate_results(st.session_state.responses)
                    st.session_state.overall_pct = o_pct
                    st.session_state.metrics = m
                    st.session_state.final_report = agent.generate_report(st.session_state.name, o_pct, m)
                    st.session_state.test_started = False
                    st.rerun()
    else:
        st.error("Error: Question index out of range. Restarting...")
        if st.button("Back to Start"):
            init_state(force_reset=True)
            st.rerun()

# --- STAGE 3: STRUCTURED REPORT ---
elif st.session_state.final_report:
    st.title("Synqsol Personality Report")
    
    # 1. Header Information
    c1, c2, c3 = st.columns(3)
    with c1: 
        st.write(f"**Name:** {st.session_state.name}")
        st.write(f"**Date:** 26/03/26")
    with c2: 
        st.write("**Test:** Basic Personality (20Q)")
    with c3: 
        st.metric("Overall Score", f"{st.session_state.overall_pct}%")

    # 1a. Bar Chart Dropdown
    with st.expander("📊 View Score Visualization (Bar Chart)"):
        st.bar_chart(st.session_state.metrics)

    # 2. Review Tab
    st.write("---")
    st.subheader("📑 Dimension Review")
    defs = {
        "Openness": "Describes a person's tendency to be intellectually curious, creative, and willing to try new experiences.",
        "Conscientiousness": "Measures how organized, dependable, and disciplined a person is in managing tasks.",
        "Extraversion": "Indicates social energy, assertiveness, and sociability.",
        "Agreeableness": "Assesses the tendency to be compassionate, cooperative, and helpful.",
        "Neuroticism": "Reflects emotional stability and the likelihood of experiencing fluctuations under stress."
    }
    for d, df in defs.items():
        with st.expander(f"Definition: {d}"):
            st.write(df)

    # 3, 4, 5. AI Content
    st.write("---")
    clean_report = st.session_state.final_report.replace("[", "").replace("]", "")
    st.markdown(clean_report)

    if st.button("🔄 Start a New Assessment"):
        init_state(force_reset=True)
        st.rerun()