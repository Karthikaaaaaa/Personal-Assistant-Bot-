import streamlit as st
import os
import sys

# Get the absolute path to the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from utils.intent_parser import IntentParser
import json

# Initialize the intent parser
parser = IntentParser()

# Streamlit app configuration
st.set_page_config(page_title="Personal Assistant", layout="centered")

# Load custom CSS
with open("frontend/styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# App header
st.markdown(
    """
    <div class="header">
        <h1>Personal Assistant</h1>
        <p>Your charming personal assistant for all your needs</p>
    </div>
    """,
    unsafe_allow_html=True
)

with st.form(key="user_input_form"):
    user_input = st.text_area(
        "How may I assist you today?",
        placeholder="e.g., Need a sunset-view table for two tonight; gluten-free menu a must",
        height=100
    )
    submit_button = st.form_submit_button(label="Submit")

# Process input and display output
if submit_button and user_input:
    with st.spinner("Processing your request..."):
        try:
            results = parser.process_input(user_input)
            if results and "error" in results[0]:
                st.error(results[0]["error"])
                st.stop()

            # Handle multiple intents
            for idx, result in enumerate(results, 1):
                # Capitalize category for display
                display_category = result['intent_category'].replace("_", " ").title()
                st.markdown(f"### Intent {idx}: {display_category}")
                
                # Display intent and confidence
                st.markdown(f"""
                <div class="output-box">
                    <h4>Intent Category</h4>
                    <p>{display_category}</p>
                    <h4>Confidence Score</h4>
                    <p>{result['confidence_score']:.2f}</p>
                </div>
                """, unsafe_allow_html=True)

                # Display key entities
                if result['key_entities']:
                    st.markdown("<h4>Key Entities</h4>", unsafe_allow_html=True)
                    entities_str = json.dumps(result['key_entities'], indent=2)
                    st.markdown(f"<pre class='output-box'>{entities_str}</pre>", unsafe_allow_html=True)

                # Display conflicts
                if result.get('conflict'):
                    st.markdown("<h4>Intent Conflict</h4>", unsafe_allow_html=True)
                    st.markdown(f"<div class='output-box'><p>⚠️ {result['conflict']}</p></div>", unsafe_allow_html=True)

                # Display validation errors
                if result.get('validation_errors'):
                    st.markdown("<h4>Validation Issues</h4>", unsafe_allow_html=True)
                    for error in result['validation_errors']:
                        st.markdown(f"<div class='output-box'><p>⚠️ {error}</p></div>", unsafe_allow_html=True)

                # Display follow-up questions (intent-specific)
                if result['follow_up_questions']:
                    st.markdown(f"<h4>Follow-Up Questions for {display_category}</h4>", unsafe_allow_html=True)
                    for question in result['follow_up_questions']:
                        st.markdown(f"<div class='output-box'><p>🔍 {question}</p></div>", unsafe_allow_html=True)

                # Display web search results for non-standard requests
                if result['web_search_results']:
                    st.markdown("<h4>Web Search Results</h4>", unsafe_allow_html=True)
                    for web_result in result['web_search_results']:
                        st.markdown(
                            f"""
                            <div class='output-box'>
                                <h5>{web_result['title']}</h5>
                                <p>{web_result['snippet']}</p>
                                <a href='{web_result['url']}' target='_blank'>Visit Link</a>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

            # Display JSON output with copy button
            st.markdown("<h4>JSON Output</h4>", unsafe_allow_html=True)
            json_output = json.dumps(results, indent=2)
            st.code(json_output, language="json")

        except Exception as e:
            st.error(f"Error processing request: {e}")