# NIRACONCHEM AI

UAE-focused construction chemicals recommendation web app.

## MVP Goal

Recommend generic construction chemical categories based on:

- Construction type
- Construction area
- UAE location and climate exposure
- User notes
- Uploaded project documents
- RAG knowledge from product datasheets

## Project Structure

- `frontend/` - Web app interface
- `backend/` - API, Groq LLM calls, LangGraph workflow, RAG, file parsing, PDF generation
- `data/datasheets/` - Product datasheets and chemistry documents for RAG
- `data/vector_store/` - Local vector database files
- `reports/` - Generated PDF reports

## Build Phases

1. Project scaffold
2. Basic recommendation form
3. Backend API with UAE climate rules
4. Groq LLM recommendation response
5. PDF report generation
6. Datasheet ingestion and RAG
7. File upload parsing
8. LangGraph agent workflow
9. Live climate/weather API integration
