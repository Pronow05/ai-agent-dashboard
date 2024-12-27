# ai-agent-dashboard

A powerful web application that automates information extraction from the web using AI. This dashboard allows users to upload datasets (CSV or Google Sheets) and leverages AI to perform automated web searches and extract specific information for each entity in the dataset.

## Features
### 1. Flexible Data Input

 - Upload CSV files directly through the web interface
 - Connect to Google Sheets via URL
- Preview data before processing
- Select specific columns for analysis

### 2. Dynamic Query System

- Customizable query templates with variable substitution
- Support for dynamic entity replacement in queries
- Flexible prompt engineering for different use cases

### 3. Automated Web Search

- Integration with SerpAPI for reliable web searches
- Intelligent content extraction from search results
- Rate limiting and error handling for robust operation
- Processes multiple URLs per entity for comprehensive results

### 4. AI-Powered Information Extraction

- Integration with OpenAI's GPT-4 for intelligent information parsing
- Customizable prompts for specific information extraction
- Structured output generation
- Error handling and retry mechanisms

### 5. Results Management

- Interactive data preview
- CSV export functionality
- Direct Google Sheets updates
- Real-time progress tracking

## Prerequisites

- Python 3.8+
- Streamlit
- Valid API keys for:

  - OpenAI API
  - SerpAPI
  - Google Sheets API (for Google Sheets integration)
