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
    def load_questions(self, test_type):
        filename = 'basic_question_bank.json' if test_type == "Basic" else 'advanced_question_bank.json'
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                all_q = json.load(f)
            random.shuffle(all_q)
            return all_q
        except Exception as e:
            st.error(f"Error loading {filename}: {e}")
            return []

    def calculate_basic(self, responses):
        """Basic Formula: ((Average Score - 1) / 4) * 100"""
        dims = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
        metrics = {}
        for d in dims:
            scores = [r['score'] for r in responses if r['dimension'] == d]
            if scores:
                avg_raw = sum(scores) / len(scores)
                metrics[d] = round(((avg_raw - 1) / 4) * 100, 2)
            else:
                metrics[d] = 0.0
        overall = round(sum(metrics.values()) / 5, 2)
        return overall, metrics

    def calculate_advanced(self, responses):
        """
        Advanced Formula Logic:
        1. Weighted Score = Score * Loading Factor
        2. Sub-dim Score = Sum(Weighted) / Sum(Loadings)
        3. Percentage = ((Sub-dim Score - 1) / 4) * 100
        """
        structure = {}
        for r in responses:
            dim = r['dimension']
            sub = r.get('sub_dimension', 'General')
            if dim not in structure: structure[dim] = {}
            if sub not in structure[dim]: structure[dim][sub] = []
            structure[dim][sub].append(r)

        dim_final_scores = {}
        for dim, subs in structure.items():
            sub_percentages = []
            for sub_name, items in subs.items():
                # --- FIXED CALCULATION LINE ---
                sum_weighted_scores = sum(item['score'] * item['loading_factor'] for item in items)
                sum_loadings = sum(item['loading_factor'] for item in items)
                
                if sum_loadings > 0:
                    sub_dim_score = sum_weighted_scores / sum_loadings
                    sub_pct = ((sub_dim_score - 1) / 4) * 100
                    sub_percentages.append(sub_pct)
            
            if sub_percentages:
                dim_final_scores[dim] = round(sum(sub_percentages) / len(sub_percentages), 2)
            else:
                dim_final_scores[dim] = 0.0

        overall = round(sum(dim_final_scores.values()) / 5, 2)
        return overall, dim_final_scores

    def generate_report(self, name, test_type, overall, metrics):
        prompt = f"""
        Generate a professional Synqsol {test_type} Personality Report for {name}.
        Overall Score: {overall}%
        Dimension Scores: {metrics}
        STRICT FORMATTING: No square brackets. Use '##' for headings.
        """
        try:
            response = client.models.generate_content(
                model="models/gemini-3.1-flash-lite-preview",
                contents=prompt
            )
            return response.text
        except:
            return "AI_BUSY_ERROR"

# --- STREAMLIT UI LOGIC ---
def reset_state():
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.session_state.test_started = False
    st.session_state.current_q = 0
    st.session_state.responses = []
    st.session_state.final_report = None
    st.session_state.name = ""

if 'test_started' not in st.session_state: reset_state()
agent = SynqsolAgent()

# --- STAGE 1: SELECTION ---
if not st.session_state.test_started and st.session_state.final_report is None:
    st.title("🧠 Synqsol Assessment Portal")
    name = st.text_input("Candidate Name", value=st.session_state.name)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Start Basic Test (20Q)"):
            if name:
                # 1. Load questions first
                questions = agent.load_questions("Basic")
                if questions:
                    # 2. Update state in the correct order
                    st.session_state.questions = questions
                    st.session_state.name = name
                    st.session_state.test_type = "Basic"
                    st.session_state.current_q = 0  # CRITICAL: Reset to 0
                    st.session_state.responses = [] # CRITICAL: Clear old data
                    st.session_state.test_started = True
                    st.rerun()
            else: st.warning("Enter name first")

    with col2:
        if st.button("🚀 Start Advanced Test (45Q)"):
            if name:
                questions = agent.load_questions("Advanced")
                if questions:
                    st.session_state.questions = questions
                    st.session_state.name = name
                    st.session_state.test_type = "Advanced"
                    st.session_state.current_q = 0  # CRITICAL: Reset to 0
                    st.session_state.responses = [] # CRITICAL: Clear old data
                    st.session_state.test_started = True
                    st.rerun()
            else: st.warning("Enter name first")

# STAGE 2: TEST LOOP
elif st.session_state.test_started:
    idx = st.session_state.current_q
    qs = st.session_state.questions
    q = qs[idx]
    st.progress((idx + 1) / len(qs))
    st.subheader(f"{st.session_state.test_type}: Question {idx + 1} of {len(qs)}")
    st.write(f"### {q['text']}")
    opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
    ans = st.radio("Response:", opts, index=2, key=f"q_{idx}")
    
    if st.button("Next ➡️" if idx < len(qs)-1 else "Finish ✅"):
        score = opts.index(ans) + 1
        if str(q.get('level')).upper() == "R": score = 6 - score
        st.session_state.responses.append({
            "dimension": q['dimension'],
            "sub_dimension": q.get('sub_dimension', 'General'),
            "score": score,
            "loading_factor": q.get('loading_factor', 1.0)
        })
        if idx < len(qs)-1:
            st.session_state.current_q += 1
            st.rerun()
        else:
            with st.spinner("Calculating..."):
                if st.session_state.test_type == "Basic":
                    o, m = agent.calculate_basic(st.session_state.responses)
                else:
                    o, m = agent.calculate_advanced(st.session_state.responses)
                st.session_state.overall_pct, st.session_state.metrics = o, m
                st.session_state.final_report = agent.generate_report(st.session_state.name, st.session_state.test_type, o, m)
                st.session_state.test_started = False
                st.rerun()

# STAGE 3: REPORT
elif st.session_state.final_report:
    st.title(f"Synqsol {st.session_state.test_type} Report")
    c1, c2, c3 = st.columns(3)
    with c1: st.write(f"**Name:** {st.session_state.name}\n**Date:** 26/03/26")
    with c3: st.metric("Overall Score", f"{st.session_state.overall_pct}%")
    with st.expander("📊 View Visualization"):
        st.bar_chart(st.session_state.metrics)
    st.write("---")
    st.markdown(st.session_state.final_report.replace("[", "").replace("]", ""))
    if st.button("🔄 Start New Assessment"):
        reset_state()
        st.rerun()