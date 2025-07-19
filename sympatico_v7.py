
import streamlit as st
import openai
import os
import requests
from urllib.parse import quote
import re

# Set OpenAI API key
openai.api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="Sympatico", layout="centered")
st.title("🧠 Sympatico – AI for the world's best paediatrician")

with st.sidebar:
    st.markdown("### ⚙️ Mode Selector")
    mode = st.selectbox("Select Mode", ["Case Scenario", "Drug Overview", "Condition Overview"])
    model_choice = st.selectbox("AI Model", ["gpt-4", "gpt-3.5-turbo"])

# --- Reference Search Helper (RCH + PubMed style links) ---
def search_rch_links(condition, max_results=1):
    try:
        search_term = quote(f"{condition} site:rch.org.au")
        url = f"https://html.duckduckgo.com/html/?q={search_term}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers).text
        matches = re.findall(r'<a rel="nofollow" class="result__a" href="(https://www.rch.org.au[^"]+)"', response)
        return matches[:max_results]
    except Exception:
        return []

def search_pubmed_links(condition, max_results=3):
    try:
        query = " ".join(condition.strip().split()[:10])
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmax={max_results}&term={quote(query)}&retmode=json"
        res = requests.get(search_url).json()
        ids = res.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml"
        data = requests.get(fetch_url).text
        import xml.etree.ElementTree as ET
        root = ET.fromstring(data)
        articles = []
        for article in root.findall(".//PubmedArticle"):
            title = article.findtext(".//ArticleTitle", "")
            pmid = article.findtext(".//PMID", "")
            link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"
            articles.append({"title": title, "link": link})
        return articles
    except Exception:
        return []

# --- Condition Overview Generator ---
def generate_condition_overview(condition_name, model_choice):
    prompt = f'''
You are a clinical assistant. Provide a comprehensive overview of the paediatric condition: **{condition_name}**

Use Markdown formatting with bolded subheadings and short paragraphs. Include:

**Overview** – Brief definition and clinical context  
**Prevalence & Epidemiology** – Who it affects and how commonly  
**Pathophysiology** – Core mechanism of disease  
**Presenting Symptoms & Signs** – Typical clinical features  
**Differential Diagnoses** – Key alternatives and distinguishing features  
**Investigations** – Relevant initial and confirmatory tests  
**Management** – First-line and escalated care  
**Prognosis** – Expected course and outcomes
'''
    try:
        response = openai.ChatCompletion.create(
            model=model_choice,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1800
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# --- Mode Routing ---
if mode == "Condition Overview":
    condition_name = st.text_input("Enter a condition (e.g. bronchiolitis, nephrotic syndrome):")
    if st.button("Generate Condition Overview"):
        with st.spinner("Generating overview..."):
            overview = generate_condition_overview(condition_name, model_choice)
            rch_links = search_rch_links(condition_name)
            pubmed_links = search_pubmed_links(condition_name)

            tabs = st.tabs(["📖 Overview", "📚 References"])
            with tabs[0]:
                st.markdown("### 📖 Condition Overview")
                st.markdown(overview, unsafe_allow_html=True)

            with tabs[1]:
                st.markdown("### 📘 RCH Guideline")
                if rch_links:
                    for link in rch_links:
                        st.markdown(f"- [RCH Guideline]({link})")
                else:
                    st.markdown("No RCH guideline found.")

                st.markdown("### 🔎 PubMed References")
                if pubmed_links:
                    for article in pubmed_links:
                        st.markdown(f"- [{article['title']}]({article['link']})")
                else:
                    st.markdown("No PubMed links found.")
