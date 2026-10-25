# Nexus RAG

Nexus RAG is a multi-format document question-answering workspace built with Streamlit, LangChain, FAISS, and OpenAI. Upload one or more documents, index them into searchable passages, and ask grounded questions with source references.

## Features

- Secure API-key verification screen before entering the application
- Retrieval-augmented generation using FAISS and OpenAI embeddings
- Supports multiple files in one workspace
- Accepts PDF, Word, CSV, Excel, and JSON files
- Source-aware answers with document and page references where available
- Configurable model, chunk size, chunk overlap, and retrieved source count
- Futuristic dark interface with animated 3D floating elements
- No conversation-history panel in the sidebar
- In-memory session handling for uploaded files and API credentials

## Supported file formats

| Format | Extension |
|---|---|
| PDF | `.pdf` |
| Microsoft Word | `.docx` |
| Comma-separated values | `.csv` |
| Excel workbook | `.xlsx`, `.xls` |
| JavaScript Object Notation | `.json` |

## Requirements

- Python 3.10 or newer
- An OpenAI API key with access to chat and embedding models
- Internet access for OpenAI requests and the Google Fonts used by the interface

## Installation

Clone or download the project, then create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Run the application

```bash
streamlit run rag.py
```

The application opens in your browser, usually at `http://localhost:8501`.

## Authentication flow

1. Open the application.
2. Enter an OpenAI API key on the verification screen.
3. Select **Verify and enter workspace**.
4. After successful verification, upload documents and begin asking questions.

The API key is stored in Streamlit session state for the active browser session. It is not written to a project file.

You may also provide the key before launching the application:

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY = "your-api-key"
streamlit run rag.py
```

macOS/Linux:

```bash
export OPENAI_API_KEY="your-api-key"
streamlit run rag.py
```

## How to use

1. Upload one or more supported files using **Add your knowledge files**.
2. Wait for Nexus RAG to create the searchable index.
3. Ask a question in the chat input.
4. Review the answer and expand **View retrieved sources** to inspect the passages used.
5. Adjust model and retrieval settings from the sidebar when needed.

Answers are instructed to use the indexed document context only. If the requested information cannot be found, the assistant should say so rather than inventing an answer.

## Configuration

The sidebar provides these controls:

- **Model**: Select the OpenAI chat model used for answers.
- **Chunk size**: Controls how much text is included in each searchable passage.
- **Chunk overlap**: Preserves context between neighboring passages.
- **Sources per answer**: Controls the number of retrieved passages supplied to the model.

The application uses `text-embedding-3-small` for document embeddings.

## Project structure

```text
.
├── rag.py
├── requirements.txt
└── README.md
```

## Troubleshooting

### The API key is rejected

Confirm that the key is active, copied correctly, and has access to the required OpenAI APIs. Check that there are no extra spaces around the key.

### Excel files fail to load

Ensure the dependencies are installed from `requirements.txt`, especially `openpyxl` for `.xlsx` files.

### Word files fail to load

Install the `python-docx` dependency:

```bash
pip install python-docx
```

### Answers are incomplete

Try increasing **Sources per answer**, increasing the **Chunk size**, or reducing the **Chunk overlap** depending on the document structure.

### The interface does not update after changing files

Refresh the browser page and upload the files again. The index is cached based on the uploaded file names, sizes, and retrieval settings.

## Security notes

- Do not commit API keys to source control.
- Do not place secrets directly in `rag.py`.
- Uploaded content is processed in the active Streamlit session.
- Review generated answers before using them for legal, medical, financial, or other high-impact decisions.

## License

Add your preferred license here before distributing the project publicly.
