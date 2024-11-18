import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
import openai
import os

# Load environment variables
load_dotenv()

# Constants
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Function to perform SerpAPI search
def perform_search(query):
    try:
        params = {
            "q": query,
            "hl": "en",
            "gl": "in",
            "api_key": SERP_API_KEY
        }
        response = requests.get(SERP_API_URL, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: Unable to fetch results for '{query}' (Status Code: {response.status_code})")
            return None
    except requests.RequestException as e:
        st.error(f"Network error: {e}")
        return None

# Function to extract and structure search results
def extract_results(data):
    results = []
    if "organic_results" in data:
        for item in data["organic_results"]:
            title = item.get("title", "No title")
            link = item.get("link", "No link")
            snippet = item.get("snippet", "No snippet available")
            results.append({"Title": title, "Link": link, "Snippet": snippet})
    return pd.DataFrame(results)

# Function to connect to Hugging Face API for parsing
def query_huggingface_api(prompt, model="google/flan-t5-large"):
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_length": 200,
            "temperature": 0.7,
        }
    }
    response = requests.post(
        f"https://api-inference.huggingface.co/models/{model}",
        headers=headers,
        json=payload
    )
    if response.status_code == 200:
        return response.json()[0]["generated_text"]
    else:
        raise Exception(f"API Error: {response.status_code} - {response.text}")

# Function to connect to Google Sheets and retrieve data
def load_google_sheet(sheet_url):
    credentials = service_account.Credentials.from_service_account_file(
        'credentials.json',
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build('sheets', 'v4', credentials=credentials)
    sheet_id = sheet_url.split("/")[5]  # Extract Google Sheet ID
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=sheet_id, range="Sheet1").execute()
    data = result.get('values', [])
    df = pd.DataFrame(data[1:], columns=data[0])  # Using header as column names
    return df

# Streamlit App
st.title("AI Agent Dashboard")
st.markdown("### 📈 Analyze your data and retrieve information from the web automatically.")

# File upload section
data_source = st.radio("Choose data source:", ("Upload CSV", "Google Sheets URL"))

# Upload CSV file
if data_source == "Upload CSV":
    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write("Preview of Uploaded Data (Limited to 20 rows)")
        st.dataframe(df.head(20))  # Show first 20 rows only

        # Select main column
        main_column = st.selectbox("Select main column for querying:", df.columns)

# Google Sheets section
elif data_source == "Google Sheets URL":
    sheet_url = st.text_input("Enter Google Sheets URL:")
    if sheet_url:
        try:
            df = load_google_sheet(sheet_url)
            st.write("Preview of Google Sheet Data (Limited to 20 rows)")
            st.dataframe(df.head(20))  # Show first 20 rows only

            # Select main column
            main_column = st.selectbox("Select main column for querying:", df.columns)
        except Exception as e:
            st.error("Failed to load Google Sheet. Check URL or credentials.")
            st.write(e)

# Automated Web Search and LLM Integration
if 'df' in locals() and not df.empty:
    st.markdown("### 🔍 Define Query Template")
    placeholder = f"Get information about {{{main_column}}}"
    query_template = st.text_input("Enter your query template:", value=placeholder)

    st.write("Example of your query template with sample data:")
    if main_column:
        sample_entity = str(df[main_column].iloc[0])  # Convert sample entity to string
        sample_query = query_template.replace(f"{{{main_column}}}", sample_entity)
        st.markdown(f"**Sample query:** {sample_query}")

    # Perform web search
    st.markdown("### 🌐 Perform Automated Web Search")
    if st.button("Run Search"):
        st.info("Starting the search process. This may take some time...")
        progress_bar = st.progress(0)
        queries = df[main_column].apply(lambda x: query_template.replace(f"{{{main_column}}}", str(x)))
        all_results = []

        for idx, query in enumerate(queries):
            progress = int((idx + 1) / len(queries) * 100)
            progress_bar.progress(progress)

            st.write(f"🔄 Searching for: `{query}`...")
            search_data = perform_search(query)
            sleep(1)  # To avoid hitting API rate limits
            
            if search_data:
                search_results = extract_results(search_data)
                search_results["Query"] = query  # Add query to results for context
                all_results.append(search_results)

        # Combine all results
        if all_results:
            combined_results = pd.concat(all_results, ignore_index=True)
            st.success("Search completed successfully!")
            st.write("### Search Results:")
            st.dataframe(combined_results)

            # Option to process results with LLM
            st.markdown("### 🔎 Process Results with LLM")
            if st.button("Process Results with LLM"):
                with st.spinner("Processing with LLM..."):
                    for query in queries:
                        prompt = f"Extract relevant details about '{query}' from the following search results:\n{combined_results}"
                        try:
                            response = query_huggingface_api(prompt)
                            st.write(f"**Processed Information for {query}:**")
                            st.text_area("LLM Output", response, height=150)
                        except Exception as e:
                            st.error(f"Error during LLM processing: {str(e)}")
