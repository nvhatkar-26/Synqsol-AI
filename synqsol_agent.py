import streamlit as st
import json
import random
import os
from google import genai
from datetime import datetime
from dotenv import load_dotenv

# 1. --- Configuration & API Setup ---
load_dotenv()

# We use the 2026 standard model for instant psychometric reports
MODEL_ID = "gemini-3.1-flash-lite-preview" 

# Fail-safe API Key retrieval (Checks Streamlit Secrets then .env)
API_KEY = None
try:
    API_KEY = st.secrets.get("GEMINI_API_KEY")
except Exception:
    pass

if not API_KEY:
    API_KEY = os.getenv("GEMINI_API_KEY")

# --- Page Config ---
st.set_page_config(page_title="Synqsol AI Agent", page_icon="🧠", layout="centered")

# 2. --- Core Logic Class ---
class SynqsolApp:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.bank_path = "question_bank.json"

    def load_questions(self, test_type):
        """Loads 20 or 40 questions balanced across OCEAN traits."""
        num_total = 20 if test_type == "Basic" else 40
        num_per_dim = num_total // 5
        
        try:
            with open(self.bank_path, 'r') as f:
                all_questions = json.load(f)
            
            dimensions = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
            selected = []
            for dim in dimensions:
                pool = [q for q in all_questions if q['dimension'] == dim]
                selected.extend(random.sample(pool, num_per_dim))
            
            random.shuffle(selected)
            return selected
        except FileNotFoundError:
            st.error(f"Error: {self.bank_path} not found in directory.")
            return []

    def calculate_results(self, responses):
        """Calculates OCEAN percentages."""
        dims = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
        stats = {d: {"total": 0, "count": 0} for d in dims}
        for r in responses:
            d = r['dimension']
            stats[d]["total"] += r['score']
            stats[d]["count"] += 1
            
        overall_total = sum(r['score'] for r in responses)
        metrics = {d: round((stats[d]["total"] / (stats[d]["count"] * 5) * 100), 2) for d in dims}
        return overall_total, metrics

    def generate_report(self, name, total, metrics):
        """Triggers Gemini 3.1 for the instant formatted report."""
        today_date = datetime.now().strftime("%d %B, %Y")
        prompt = f"""
        Act as the Synqsol Psychometric Expert. Generate a personality report for {name}.
        DATA: Total Score: {total}, OCEAN Percentages: {metrics}
        Date of Report: {today_date}
        
        FORMAT:
        Include the date "{today_date}" at the top of the report.
        1. **Overall Personality Index**: Explain the score archetype.
        2. **Dimension Breakdown**: Show % and 2-sentence meaning for each trait.
        3. **Areas of Improvement**: 3 actionable growth steps based on results.
        
        Tone: Professional, empathetic, and insightful.
        """
        response = self.client.models.generate_content(model=MODEL_ID, contents=prompt)
        return response.text

# 3. --- Streamlit UI Engine ---

if not API_KEY:
    st.error("🔑 API Key Missing! Please check your .env or secrets.toml")
    st.stop()

agent = SynqsolApp(API_KEY)

# Initialize Session States
if 'test_started' not in st.session_state:
    st.session_state.test_started = False
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'responses' not in st.session_state:
    st.session_state.responses = []
if 'final_report' not in st.session_state:
    st.session_state.final_report = None

st.title("🧠 Synqsol Psychometric Agent")
st.write("Understand your personality through the OCEAN model.")

# --- STAGE 1: Setup ---
if not st.session_state.test_started:
    name = st.text_input("Enter your name")
    test_type = st.selectbox("Select Test Length", ["Basic (20Q)", "Advanced (40Q)"])
    
    if st.button("Start Test"):
        if name:
            st.session_state.name = name
            st.session_state.questions = agent.load_questions(test_type.split()[0])
            st.session_state.test_started = True
            st.rerun()
        else:
            st.warning("Please enter your name to begin.")

# --- STAGE 2: Testing ---
else:
    current_q_idx = len(st.session_state.responses)
    num_questions = len(st.session_state.questions)

    if current_q_idx < num_questions:
        q = st.session_state.questions[current_q_idx]
        
        # UI Elements
        st.progress(current_q_idx / num_questions)
        st.write(f"**Question {current_q_idx + 1} of {num_questions}**")
        st.info(f"Dimension: {q['dimension']}")
        st.markdown(f"### {q['text']}")
        
        # Radio Button with Fixed String Conversion
        score = st.radio(
            "Select your response:",
            options=[1, 2, 3, 4, 5],
            format_func=lambda x: {
                1: "1 - Strongly Disagree", 
                2: "2 - Disagree", 
                3: "3 - Neutral", 
                4: "4 - Agree", 
                5: "5 - Strongly Agree"
            }[x],
            horizontal=True,
            key=f"q_{current_q_idx}"
        )
        
        if st.button("Next Question →"):
            st.session_state.responses.append({"dimension": q['dimension'], "score": score})
            st.rerun()

    # --- STAGE 3: Final Report ---
    else:
        st.success("✅ Test Completed! Analyzing your results...")
        
        if st.session_state.final_report is None:
            with st.spinner("Synqsol AI is generating your personalized report..."):
                total, metrics = agent.calculate_results(st.session_state.responses)
                report = agent.generate_report(st.session_state.name, total, metrics)
                st.session_state.final_report = report
        
        st.markdown("---")
        st.markdown(st.session_state.final_report)
        
        if st.button("Restart Test"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()