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
        try:
            with open(self.bank_path, 'r', encoding='utf-8') as f:
                all_q = json.load(f)
            
            dimensions = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
            final_selection = []

            for dim in dimensions:
                dim_pool = [q for q in all_q if q.get('dimension') == dim]
                
                # We are forcing both types to use the 20Q logic for now
                # 2x L1, 1x L2, 1x LR = 4 questions per trait
                l1 = random.sample([q for q in dim_pool if str(q.get('level')) == "1"], 2)
                l2 = random.sample([q for q in dim_pool if str(q.get('level')) == "2"], 1)
                lr = random.sample([q for q in dim_pool if str(q.get('level')) == "R"], 1)
                final_selection.extend(l1 + l2 + lr)
            
            random.shuffle(final_selection)
            return final_selection
            
        except Exception as e:
            st.error(f"Selection Error: {e}")
            return []
        
    def calculate_results(self, responses):
        dims = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
        scores_by_dim = {d: [] for d in dims}

        for r in responses:
            dim_name = r.get('dimension')
            if dim_name in scores_by_dim:
                scores_by_dim[dim_name].append(r['score'])

        metrics = {}
        for d in dims:
            dim_scores = scores_by_dim[d]
            if len(dim_scores) > 0:
                # ORIGINAL FORMULA: (Average / 5) * 100
                avg_score = sum(dim_scores) / len(dim_scores)
                percentage = (avg_score / 5) * 100
                metrics[d] = round(percentage, 2)
            else:
                metrics[d] = 0.0
        
        overall_pct = round(sum(metrics.values()) / len(metrics), 2)
        return overall_pct, metrics
    
    def generate_report(self, name, overall_pct, metrics):
        today_date = datetime.now().strftime("%d %m, %Y")
        prompt = f"""
        Act as the Synqsol Psychometric Expert.
        Generate a personality report for {name}.
        Date: {today_date}
        Overall Personality Index: {overall_pct}%
        Dimension Breakdowns (OCEAN %): {metrics}
        
        FORMAT:
        1. **Summmary**: Describe the user based on the {overall_pct}% index.
        2. **Detailed Traits**: 3-4 sentences for each of the 5 OCEAN categories.
        3. **Growth Plan**: 3 specific key areas of improvement.
        
        Tone: Professional, Insightful, and Analytical.
        """
        
        response = self.client.models.generate_content(model = MODEL_ID, contents = prompt)
        return response.text
    
#3 Streamlit UI Engine
    
if not API_KEY:
        st.error("🔑 API Key Missing! Check your configuration.")
        st.stop()
        
agent = SynqsolApp(API_KEY)
    
# Session State Initialisation
if 'test_started' not in st.session_state:
    st.session_state.test_started = False
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'responses' not in st.session_state:
    st.session_state.responses = []
if 'final_report' not in st.session_state:
    st.session_state.final_report = None
        
st.title("🧠 Synqsol AI Psychometric Agent")

# --- STAGE 1: Setup ---
if not st.session_state.test_started:
    st.markdown("### Welcome to the Synqsol Assessment")
    st.write("Please enter your name to begin your personality analysis.")
    
    name = st.text_input("Candidate Name", placeholder="e.g. Neha")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Start Basic Test (20Q)"):
            if name:
                st.session_state.name = name
                # Crucial: Load the questions into session state
                questions = agent.load_questions("Basic")
                
                # DEBUG CHECK: Ensure the loop picked up all 5 dimensions
                if len(questions) < 20:
                    st.error(f"⚠️ Error: Only {len(questions)} questions loaded. Check your JSON levels.")
                else:
                    st.session_state.questions = questions
                    st.session_state.test_started = True
                    st.rerun()
            else:
                st.warning("Please enter a name before starting.")
                
    with col2:
        if st.button("Start Pro Test (50Q)"):
            if name:
                st.session_state.name = name
                questions = agent.load_questions("Full")
                
                # DEBUG CHECK: Ensure the loop picked up 50 questions
                if len(questions) < 50:
                    st.error(f"⚠️ Error: Only {len(questions)} questions loaded. Check your JSON levels.")
                else:
                    st.session_state.questions = questions
                    st.session_state.test_started = True
                    st.rerun()
            else:
                st.warning("Please enter a name before starting.")

    st.info("The Basic Test takes ~3 minutes. The Pro Test takes ~12 minutes.")
                
# Stage 2: Test Taking
else:
    current_q_idx = len(st.session_state.responses)
    num_questions = len(st.session_state.questions)
    
    if current_q_idx < num_questions:
        q = st.session_state.questions[current_q_idx]
        
        st.progress(current_q_idx / num_questions)
        st.write(f"**Question {current_q_idx + 1} of {num_questions}**")
        st.markdown(f"### {q['text']}")
        
        # Mirror Image Likert Logic
        is_reverse = (q.get('Level') == "R")
        
        labels = {
            1: "Strongly Disagree", 
            2: "Disagree",
            3: "Neutral",
            4: "Agree",
            5: "Strongly Agree"
        } if not is_reverse else {
            1: "Strongly Agree", 
            2: "Agree",
            3: "Neutral",
            4: "Disagree",
            5: "Strongly Disagree"
        }
        
        score = st.radio("Select Response:",
                         options = [1, 2, 3, 4, 5],
                         format_func = lambda x: labels[x],
                         horizontal = True,
                         key = f"q_{current_q_idx}"
        )
        if st.button("Next ->"):
            st.session_state.responses.append({
                "dimension": q['dimension'],
                "score": score,
                "level": q['level']
            })
            st.rerun()
            
    # Sage 3: Final Report
    else:
        # Only calculate if we haven't already generated the report
        if st.session_state.final_report is None:
            with st.spinner("AI is analyzing your Synqsol profile..."):
                overall_pct, metrics = agent.calculate_results(st.session_state.responses)
                report = agent.generate_report(st.session_state.name, overall_pct, metrics)
                st.session_state.final_report = report
                st.session_state.metrics = metrics
        
        st.success("✅ Assessment Completed.")
        st.markdown("---")
        st.markdown(st.session_state.final_report)
        st.bar_chart(st.session_state.metrics)
        
        # RESET BUTTON
        if st.button("🔄 Start New Assessment"):
            st.session_state.clear()
            st.rerun()
    