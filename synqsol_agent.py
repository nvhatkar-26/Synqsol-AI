import streamlit as st
import json
import random
from google import genai
from dotenv import load_dotenv
import os

# --- INITIAL SETUP ---
st.set_page_config(page_title="Synqsol AI Agent", page_icon="🧠")

# Load API Key from Streamlit Secrets (for Cloud) or .env (for Local)
load_dotenv()
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

class SynqsolAgent:
    def __init__(self, bank_path='question_bank.json'):
        self.bank_path = bank_path

    def load_questions(self, test_type="Basic"):
        try:
            with open(self.bank_path, 'r', encoding='utf-8') as f:
                all_q = json.load(f)
            
            # This takes EVERYTHING in your file. 
            # If you have 20 questions, it loads 20.
            final_selection = all_q
            random.shuffle(final_selection)
            return final_selection
        except Exception as e:
            st.error(f"Error loading JSON: {e}")
            return []

    def calculate_results(self, responses):
        """Original Formula: (Average Score / 5) * 100"""
        dims = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
        metrics = {}

        for d in dims:
            # Filter scores for the specific dimension
            scores = [r['score'] for r in responses if r['dimension'] == d]
            
            if len(scores) > 0:
                # Formula: (Sum of scores / Number of questions / 5) * 100
                avg = sum(scores) / len(scores)
                metrics[d] = round((avg / 5) * 100, 2)
            else:
                metrics[d] = 0.0

        overall_pct = round(sum(metrics.values()) / 5, 2)
        return overall_pct, metrics

    def generate_report(self, name, overall_pct, metrics, responses):
        """Generates the AI Personality Report using Gemini."""
        prompt = f"""
        Analyze the Synqsol Psychometric results for {name}.
        Overall Personality Index: {overall_pct}%
        Trait Scores: {metrics}

        Candidate Question-by-Question Responses:
        {responses}

        INSTRUCTIONS:
        1. Provide a professional executive summary of the candidate's personality.
        2. Analyze the TEXT of the questions to identify specific behavioral nuances 
           (e.g., if they scored high on organization-related questions, highlight their 'Orderliness').
        3. Create a 3-step 'Synqsol Growth Plan' for {name}.
        4. Keep the tone professional, insightful, and supportive.
        """
        
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Report Generation Error: {e}"

# --- STREAMLIT SESSION STATE ---
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

agent = SynqsolAgent()

# --- STAGE 1: WELCOME & SETUP ---
if not st.session_state.test_started and st.session_state.final_report is None:
    st.title("🧠 Synqsol AI Personality Agent")
    st.write("Welcome to the 20-question professional assessment.")
    
    name = st.text_input("Enter Candidate Name:", placeholder="e.g. Neha Hatkar")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Start Assessment"):
            if name:
                st.session_state.name = name
                qs = agent.load_questions()
                if len(qs) >= 20:
                    st.session_state.questions = qs
                    st.session_state.test_started = True
                    st.rerun()
                else:
                    st.error("JSON Error: Found fewer than 20 questions.")
            else:
                st.warning("Please enter a name first.")
    with col2:
        st.button("🔒 Pro Test (50Q) - Locked", disabled=True)

# --- STAGE 2: THE TEST LOOP ---
elif st.session_state.test_started:
    q_idx = st.session_state.current_q
    q = st.session_state.questions[q_idx]
    
    st.progress((q_idx + 1) / 20)
    st.subheader(f"Question {q_idx + 1} of 20")
    st.info(f"Trait focus: {q['dimension']}")
    st.write(f"### {q['text']}")

    # Likert Scale Options
    options = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
    choice = st.radio("Select your response:", options, index=2, key=f"q_{q_idx}")

    if st.button("Next ➡️" if q_idx < 19 else "Finish Assessment ✅"):
        # Map response to score 1-5
        score = options.index(choice) + 1
        
        # Handle Reverse Scoring (Level R)
        if str(q.get('level')) == "R":
            score = 6 - score
            
        st.session_state.responses.append({
            "text": q['text'],
            "dimension": q['dimension'],
            "score": score
        })

        if q_idx < 19:
            st.session_state.current_q += 1
            st.rerun()
        else:
            # End of test
            with st.spinner("Analyzing your personality..."):
                overall_pct, metrics = agent.calculate_results(st.session_state.responses)
                report = agent.generate_report(st.session_state.name, overall_pct, metrics, st.session_state.responses)
                st.session_state.final_report = report
                st.session_state.overall_pct = overall_pct