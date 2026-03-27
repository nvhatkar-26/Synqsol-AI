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
            if not os.path.exists(filename):
                st.error(f"File not found: {filename}")
                return []
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    st.error(f"The file {filename} is empty.")
                    return []
                all_q = json.loads(content)
            random.shuffle(all_q)
            return all_q
        except json.JSONDecodeError:
            st.error(f"Format Error: {filename} contains invalid JSON. Check for stray characters.")
            return []
        except Exception as e:
            st.error(f"Error loading {filename}: {e}")
            return []

    def calculate_basic(self, responses):
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
                # Corrected syntax for Summation logic
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
        Overall Score: {overall}% | Metrics: {metrics}
        STRICT FORMATTING: No square brackets. Use '##' for headings. 
        Include: Executive Summary, Detailed Dimension Analysis, Key Strengths, and Development Opportunities.
        """
        try:
            response = client.models.generate_content(
                model="models/gemini-3.1-flash-lite-preview",
                contents=prompt
            )
            return response.text
        except:
            return "AI_BUSY_ERROR"

# --- STATE MANAGEMENT ---
def reset_state():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.test_started = False
    st.session_state.current_q = 0
    st.session_state.responses = []
    st.session_state.final_report = None
    st.session_state.name = ""
    st.session_state.test_type = None

if 'test_started' not in st.session_state:
    reset_state()

agent = SynqsolAgent()

# --- STAGE 1: SELECTION ---
if not st.session_state.test_started and st.session_state.final_report is None:
    st.title("🧠 Synqsol Assessment Portal")
    name_input = st.text_input("Candidate Name", value=st.session_state.name)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Start Basic Test (20Q)"):
            if name_input:
                qs = agent.load_questions("Basic")
                if qs:
                    st.session_state.name, st.session_state.test_type = name_input, "Basic"
                    st.session_state.questions, st.session_state.current_q = qs, 0
                    st.session_state.responses, st.session_state.test_started = [], True
                    st.rerun()
            else: st.warning("Please enter your name.")

    with col2:
        if st.button("🚀 Start Advanced Test (45Q)"):
            if name_input:
                qs = agent.load_questions("Advanced")
                if qs:
                    st.session_state.name, st.session_state.test_type = name_input, "Advanced"
                    st.session_state.questions, st.session_state.current_q = qs, 0
                    st.session_state.responses, st.session_state.test_started = [], True
                    st.rerun()
            else: st.warning("Please enter your name.")

# --- STAGE 2: TEST LOOP ---
elif st.session_state.test_started:
    qs = st.session_state.questions
    idx = st.session_state.current_q
    
    # SAFETY: Prevent IndexError if state is inconsistent
    if idx >= len(qs):
        st.session_state.current_q = 0
        st.rerun()

    q = qs[idx]
    st.progress((idx + 1) / len(qs))
    st.subheader(f"{st.session_state.test_type} Test: Q{idx + 1} of {len(qs)}")
    st.write(f"### {q['text']}")
    
    opts = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
    ans = st.radio("Your response:", opts, index=2, key=f"q_{idx}")
    
    if st.button("Next ➡️" if idx < len(qs)-1 else "Finish ✅"):
        score = opts.index(ans) + 1
        if str(q.get('level')).upper() == "R": score = 6 - score
        
        st.session_state.responses.append({
            "dimension": q['dimension'],
            "sub_dimension": q.get('sub_dimension', 'General'),
            "score": score,
            "loading_factor": float(q.get('loading_factor', 1.0))
        })
        
        if idx < len(qs)-1:
            st.session_state.current_q += 1
            st.rerun()
        else:
            with st.spinner("Analyzing Results..."):
                if st.session_state.test_type == "Basic":
                    o, m = agent.calculate_basic(st.session_state.responses)
                else:
                    o, m = agent.calculate_advanced(st.session_state.responses)
                
                st.session_state.overall_pct, st.session_state.metrics = o, m
                st.session_state.final_report = agent.generate_report(st.session_state.name, st.session_state.test_type, o, m)
                st.session_state.test_started = False
                st.rerun()

# --- STAGE 3: REPORT ---
elif st.session_state.final_report:
    st.title(f"Synqsol {st.session_state.test_type} Report")
    c1, c2, c3 = st.columns(3)
    with c1: st.write(f"**Candidate:** {st.session_state.name}\n**Date:** 27/03/26")
    with c3: st.metric("Overall Score", f"{st.session_state.overall_pct}%")

    with st.expander("📊 View Score Visualization"):
        st.bar_chart(st.session_state.metrics)

    st.write("---")
    # Removal of square brackets and clean rendering
    report_text = st.session_state.final_report.replace("[", "").replace("]", "")
    st.markdown(report_text)

    if st.button("🔄 Start New Assessment"):
        reset_state()
        st.rerun()