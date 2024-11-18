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

# Utility Functions
def fetch_full_content(url):
    """
    Fetches cleaned content from a given URL by removing unnecessary tags.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        for tag in soup(["script", "style", "header", "footer", "aside", "nav"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        cleaned_text = "\n".join(line for line in text.splitlines() if len(line.strip()) > 50)
        return cleaned_text[:1000]
    except requests.exceptions.RequestException as e:
        return f"Error fetching content from {url}: {e}"

def fetch_top_urls_content(search_results, num_urls=3):
    """
    Retrieves and processes content from the top search results.
    """
    full_parsed_results = []
    urls_processed = 0

    for result in search_results.get('organic_results', []):
        if urls_processed >= num_urls:
            break
        title = result.get('title', 'No Title')
        url = result.get('link', 'No URL')

        try:
            content = fetch_full_content(url)
            full_parsed_results.append(f"Title: {title}\nURL: {url}\nContent: {content[:400]}...")
            urls_processed += 1
        except Exception as e:
            full_parsed_results.append(f"Title: {title}\nURL: {url}\nError Fetching Content: {e}")

    return "\n\n".join(full_parsed_results)

def query_openai_api(prompt):
    """
    Queries the OpenAI API with a given prompt.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an advanced AI assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3,
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error querying OpenAI API: {e}"

def load_google_sheet(sheet_url):
    """
    Loads data from a Google Sheet URL.
    """
    try:
        credentials = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        sheet_id = sheet_url.split("/")[5]
        service = build('sheets', 'v4', credentials=credentials)
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range="Sheet1"
        ).execute()
        data = result.get('values', [])
        return pd.DataFrame(data[1:], columns=data[0])
    except Exception as e:
        raise RuntimeError(f"Failed to load Google Sheet: {e}")

def serpapi_search(query):
    """
    Performs a search query using the SerpAPI.
    """
    try:
        params = {'q': query, 'api_key': SERPAPI_API_KEY}
        response = requests.get('https://serpapi.com/search', params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error with SerpAPI request: {e}")

# Streamlit Interface
st.title("AI Agent Dashboard")
st.write("Upload a CSV file or connect to a Google Sheet to begin.")

# Data Source Selection
data_source = st.radio("Choose data source:", ("Upload CSV", "Google Sheets URL"))

if data_source == "Upload CSV":
    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
elif data_source == "Google Sheets URL":
    sheet_url = st.text_input("Enter Google Sheets URL:")
    if sheet_url:
        try:
            df = load_google_sheet(sheet_url)
        except Exception as e:
            st.error(e)
            df = None

if 'df' in locals() and df is not None:
    st.write("Preview of Data (Limited to 20 rows)")
    st.dataframe(df.head(20))

    main_column = st.selectbox("Select main column for querying:", df.columns)
    query_template = st.text_input(
        "Enter query template:", value=f"Get information about {{{main_column}}}"
    )

    if st.button("Run Query"):
        results = []
        for _, row in df.iterrows():
            entity = row[main_column]
            query = query_template.replace(f"{{{main_column}}}", entity)
            try:
                search_results = serpapi_search(query)
                top_urls_content = fetch_top_urls_content(search_results)
                prompt_template = """
                You are an advanced AI assistant tasked with summarizing and analyzing search results. Your objectives are:
                1. Provide accurate and concise answers to user queries.
                2. Use details from the top 3 URLs (title, URL, and scraped content).
                3. Respond in short paragraphs.

                Top URLs and Content:
                {results}

                User Query:
                {query}

                Respond with a clear and structured answer.
                """
                formatted_prompt = prompt_template.format(results=top_urls_content, query=query)
                response = query_openai_api(formatted_prompt)
                results.append(response)
            except Exception as e:
                results.append(f"Error processing query: {e}")

        df['Extracted Information'] = results

            # Display updated DataFrame
        st.write("### Updated Data with Extracted Information")
        st.dataframe(df)

            # Download CSV button
        st.download_button(
                label="Download CSV",
                data=df.to_csv(index=False),
                file_name="extracted_information.csv",
                mime="text/csv"
        )

            # Update Google Sheet if applicable
        if data_source == "Google Sheets URL":
                if st.button("Update Google Sheet"):
                    try:
                        # Validate the sheet URL
                        if "spreadsheets/d/" not in sheet_url:
                            raise ValueError("Invalid Google Sheets URL format. Please provide a valid URL.")
                        spreadsheet_id = sheet_url.split("/d/")[1].split("/")[0]
                        # Write the updated DataFrame back to Google Sheets
                        credentials = service_account.Credentials.from_service_account_file(
                            'credentials.json',
                            scopes=["https://www.googleapis.com/auth/spreadsheets"]
                        )
                        service = build('sheets', 'v4', credentials=credentials)
                        sheet = service.spreadsheets()
                        body = {
                            'values': [df.columns.tolist()] + df.values.tolist()
                        }
                        result = sheet.values().update(
                            spreadsheetId=spreadsheet_id,
                            range="Sheet1",  # Adjust range if needed
                            valueInputOption="RAW",
                            body=body
                        ).execute()

                        st.success("Google Sheet updated successfully!")
                        st.write(f"Updated {result.get('updatedCells')} cells.")
                    except FileNotFoundError:
                        st.error("The credentials.json file is missing. Ensure it is uploaded and accessible.")
                    except ValueError as ve:
                        st.error(f"Error: {ve}")
                    except Exception as e:
                        st.error("Failed to update Google Sheet.")
                        st.write(e)