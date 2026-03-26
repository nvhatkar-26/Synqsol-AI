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
            random.shuffle(all_q)
            return all_q
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
                # Min-Max Normalization: ((Avg - 1) / 4) * 100
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
        - Do NOT use square brackets like [SUMMARY]. Use '##' headings.
        - The 'Dimension Analysis' section must be a descriptive paragraph for each trait.
        
        REPORT STRUCTURE:
        ## Executive Summary
        A 4-line overview of the overall personality profile.

        ## Detailed Dimension Analysis
        For each of the five traits, provide a 2-3 sentence descriptive analysis of what {name}'s specific percentage means for their professional behavior.

        ## Key Strengths
        List 3 detailed bullet points.

        ## Development Opportunities
        List 2 specific, actionable areas for improvement.
        """

# --- SESSION STATE ---
for key in ['test_started', 'current_q', 'responses', 'questions', 'final_report', 'name']:
    if key not in st.session_state:
        st.session_state[key] = False if key == 'test_started' else (0 if key == 'current_q' else ([] if key in ['responses', 'questions'] else (None if key == 'final_report' else "")))

agent = SynqsolAgent()

# --- STAGE 1: WELCOME ---
if not st.session_state.test_started and st.session_state.final_report is None:
    st.title("🧠 Synqsol Assessment")
    input_name = st.text_input("Candidate Name", value=st.session_state.name)
    if st.button("🚀 Start Basic Test"):
        if input_name:
            st.session_state.name = input_name
            st.session_state.questions = agent.load_questions()
            st.session_state.test_started = True
            st.rerun()
        else:
            st.warning("Please enter your name.")

# --- STAGE 2: TEST LOOP ---
elif st.session_state.test_started:
    q_idx, total_q = st.session_state.current_q, len(st.session_state.questions)
    q = st.session_state.questions[q_idx]
    st.progress((q_idx + 1) / total_q)
    st.subheader(f"Question {q_idx + 1} of {total_q}")
    st.write(f"### {q['text']}")
    options = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
    choice = st.radio("Response:", options, index=2, key=f"q_{q_idx}")

    if st.button("Next ➡️" if q_idx < (total_q - 1) else "Finish ✅"):
        score = options.index(choice) + 1
        if str(q.get('level')).upper() == "R": score = 6 - score
        st.session_state.responses.append({"dimension": q['dimension'], "score": score})
        if q_idx < (total_q - 1):
            st.session_state.current_q += 1
            st.rerun()
        else:
            with st.spinner("Analyzing..."):
                o_pct, m = agent.calculate_results(st.session_state.responses)
                st.session_state.overall_pct, st.session_state.metrics = o_pct, m
                st.session_state.final_report = agent.generate_report(st.session_state.name, o_pct, m)
                st.session_state.test_started = False
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

    # 1a. Bar Chart as a Dropdown
    with st.expander("📊 View Score Visualization (Bar Chart)"):
        st.bar_chart(st.session_state.metrics)

    # 2. Review Tab (Detailed Definitions)
    st.write("---")
    st.subheader("📑 Dimension Review")
    defs = {
        "Openness": "Openness describes a person's tendency to be intellectually curious, creative, and willing to try new experiences rather than sticking to strict routines.",
        "Conscientiousness": "Conscientiousness measures how organized, dependable, and disciplined a person is in managing their tasks and professional responsibilities.",
        "Extraversion": "Extraversion indicates how much energy an individual draws from social interactions, reflecting their level of assertiveness and sociability.",
        "Agreeableness": "Agreeableness assesses a person's tendency to be compassionate, cooperative, and helpful toward others rather than suspicious or antagonistic.",
        "Neuroticism": "Neuroticism (or Emotional Stability) reflects how a person responds to stress and their likelihood of experiencing emotional fluctuations under pressure."
    }
    for d, df in defs.items():
        with st.expander(f"Definition: {d}"):
            st.write(df)

    # 3, 4, 5. AI Content
    st.write("---")
    # Cleaning up any stray brackets if the AI generates them by mistake
    clean_report = st.session_state.final_report.replace("[", "").replace("]", "")
    st.markdown(clean_report)

    if st.button("🔄 Restart New Test"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()