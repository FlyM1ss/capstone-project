"""
Google Docs API setup and document creation script.
Creates the Software Engineering Assignment as a Google Doc with embedded images.

Usage:
  1. Place credentials.json in the same directory as this script
  2. Run: python3 setup_google_docs.py
  3. A browser window will open for Google sign-in (first time only)
  4. The script creates the doc and prints the URL
"""

import subprocess
import sys

# ── Install dependencies if needed ──
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--break-system-packages",
        "google-api-python-client", "google-auth", "google-auth-oauthlib"
    ])
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, "credentials.json")
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.json")
DIAGRAMS_DIR = os.path.join(SCRIPT_DIR, "diagrams")

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]


def authenticate():
    """Handle OAuth2 authentication. Opens browser on first run."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"\n ERROR: credentials.json not found at:")
                print(f"   {CREDENTIALS_FILE}")
                print(f"\n Please download it from Google Cloud Console")
                print(f" and place it in the directory above.")
                sys.exit(1)

            print("\n Starting OAuth2 flow (console-based for WSL)...\n")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=8085, open_browser=False)
            # The above prints a URL — copy it to your browser, sign in,
            # and the redirect back to localhost:8085 completes the flow.

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print("Authentication successful! Token saved.\n")

    return creds


def upload_image_to_drive(drive_service, filepath, filename):
    """Upload an image to Google Drive and return a shareable URI."""
    media = MediaFileUpload(filepath, mimetype="image/png")
    file_metadata = {"name": filename}
    file = drive_service.files().create(
        body=file_metadata, media_body=media, fields="id"
    ).execute()
    file_id = file["id"]

    # Make it publicly readable so Google Docs can embed it
    drive_service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    uri = f"https://drive.google.com/uc?id={file_id}"
    print(f"  Uploaded {filename} -> {uri}")
    return uri


def create_document(docs_service, drive_service):
    """Create the Software Engineering Google Doc with all content and diagrams."""

    # ── Upload diagram images to Drive first ──
    print("Uploading diagram images to Google Drive...")
    diagram_files = {
        "usecase": "usecase.png",
        "activity": "activity.png",
        "sequence": "sequence.png",
        "component": "component.png",
        "deployment": "deployment.png",
    }
    image_uris = {}
    for key, filename in diagram_files.items():
        filepath = os.path.join(DIAGRAMS_DIR, filename)
        if os.path.exists(filepath):
            image_uris[key] = upload_image_to_drive(
                drive_service, filepath, f"SE_Diagram_{key}.png"
            )
        else:
            print(f"  WARNING: {filepath} not found, skipping")

    # ── Create the document ──
    print("\nCreating Google Doc...")
    doc = docs_service.documents().create(
        body={"title": "Software Design and Engineering — Group Two"}
    ).execute()
    doc_id = doc["documentId"]
    print(f"  Document ID: {doc_id}")
    print(f"  URL: https://docs.google.com/document/d/{doc_id}/edit")

    # ── Build the content ──
    # We build forward, tracking the insertion index.
    requests = []
    idx = 1  # Google Docs index starts at 1

    def add_text(text, style=None):
        nonlocal idx
        requests.append({
            "insertText": {"location": {"index": idx}, "text": text}
        })
        start = idx
        idx += len(text)
        if style:
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": start, "endIndex": idx},
                    "textStyle": style,
                    "fields": ",".join(style.keys()),
                }
            })
        return start

    def add_heading(text, level):
        nonlocal idx
        start = idx
        add_text(text + "\n")
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": idx},
                "paragraphStyle": {"namedStyleType": f"HEADING_{level}"},
                "fields": "namedStyleType",
            }
        })

    def add_normal(text):
        add_text(text + "\n")

    def add_bold_line(text):
        add_text(text + "\n", style={"bold": True})

    def add_image(uri, width_pts=460):
        nonlocal idx
        requests.append({
            "insertInlineImage": {
                "location": {"index": idx},
                "uri": uri,
                "objectSize": {
                    "width": {"magnitude": width_pts, "unit": "PT"},
                },
            }
        })
        idx += 1  # inline image takes 1 index
        add_text("\n")

    # ═══════════════════════════════════════
    # TITLE BLOCK
    # ═══════════════════════════════════════
    add_text("Software Design and Engineering\n",
             style={"bold": True, "fontSize": {"magnitude": 22, "unit": "PT"}})
    add_text("AI-Driven Company-Wide Search Engine for Deloitte Resources\n",
             style={"italic": True, "fontSize": {"magnitude": 13, "unit": "PT"}})
    add_text("\n")
    add_bold_line("Group Two")
    add_normal("Jesse Gabriel, Andrew Jung, Raven Levitt, Felix Tian, Sophia Turnbow, Matthew Voynovich")
    add_text("\n")
    add_normal("Information Technology Capstone \u2014 ITWS 4100")
    add_normal("Professor Richard Plotka")
    add_normal("Spring 2026")
    add_text("\n\n")

    # ═══════════════════════════════════════
    # 1. INTRODUCTION
    # ═══════════════════════════════════════
    add_heading("1. Introduction", 1)
    add_normal(
        "This document describes the software design and engineering specifications "
        "for the AI-Driven Company-Wide Search Engine being developed for Deloitte. "
        "The system is a web application that enables Deloitte employees to search "
        "across internal resources\u2014documents, policies, slide decks, and images\u2014"
        "using natural language queries. It leverages Natural Language Processing (NLP) "
        "with hybrid retrieval (combining semantic search and keyword matching) to "
        "understand user intent and return relevant results even when the query wording "
        "does not exactly match the document text."
    )
    add_text("\n")
    add_normal(
        "The software design follows standard UML modeling practices to describe the "
        "system\u2019s behavior, structure, and deployment. This section identifies core "
        "use cases, specifies the primary use case in detail, and provides Use Case, "
        "Activity, Sequence, Component, and Deployment diagrams."
    )
    add_text("\n")

    # ═══════════════════════════════════════
    # 2. USE CASES
    # ═══════════════════════════════════════
    add_heading("2. Use Cases", 1)
    add_normal(
        "Five use cases have been identified for the Deloitte AI Search Engine. "
        "These represent the primary interactions between users (Deloitte employees "
        "and system administrators) and the system."
    )
    add_text("\n")

    # UC1
    add_heading("Use Case 1: Search for Resources by Name or Topic (Primary)", 2)
    add_normal(
        "The core use case of the system. A Deloitte employee enters a natural language "
        "query into the search bar to locate a specific known resource (e.g., \u201cQ4 "
        "healthcare consulting deck\u201d or \u201ctravel reimbursement policy\u201d). The system "
        "processes the query through input validation, intent classification, and entity "
        "extraction, then performs hybrid retrieval (semantic + keyword search) against the "
        "indexed resource database. Results are ranked by relevance and presented with "
        "title, snippet, author, date, and document type. The user can click on a result "
        "to access the document."
    )
    add_bold_line("Actors: Deloitte Employee (primary)")
    add_bold_line("Trigger: Employee needs to locate a specific internal resource by name, topic, or description.")
    add_text("\n")

    # UC2
    add_heading("Use Case 2: Search for Information Within Documents", 2)
    add_normal(
        "A Deloitte employee searches for a specific piece of information without knowing "
        "which document contains it. Rather than looking for a document by name, the user "
        "asks a content-level question (e.g., \u201cWhat is Accenture\u2019s GAAP and non-GAAP EPS "
        "for the most recent quarterly earnings report?\u201d or \u201cWhat are the current billable "
        "hour thresholds for senior consultants?\u201d). The system uses semantic search to "
        "identify document chunks whose content is most relevant to the query, then returns "
        "the source documents ranked by how well their internal content matches the question. "
        "Results highlight the relevant passage or section within each document, allowing the "
        "user to go directly to the answer rather than reading entire files."
    )
    add_bold_line("Actors: Deloitte Employee (primary)")
    add_bold_line("Trigger: Employee needs a specific data point, fact, or policy detail but does not know which document contains it.")
    add_text("\n")

    # UC3
    add_heading("Use Case 3: Filter and Refine Search Results", 2)
    add_normal(
        "After performing an initial search, a user applies metadata filters to narrow "
        "down the result set. Available filters include document type (PDF, slide deck, "
        "policy document, image), date range, author, and department. The system re-ranks "
        "and redisplays results based on the applied filters without requiring a new query."
    )
    add_bold_line("Actors: Deloitte Employee (primary)")
    add_bold_line("Trigger: Initial search returns too many results or the user wants to scope results to a specific category.")
    add_text("\n")

    # UC4
    add_heading("Use Case 4: Ingest and Index Documents", 2)
    add_normal(
        "A system administrator uploads new documents (PDFs, Word files, slide decks) "
        "into the system. The ingestion pipeline extracts text and metadata, chunks long "
        "documents, generates vector embeddings, and stores both the metadata (in PostgreSQL) "
        "and embeddings (in the vector store) for future retrieval. Cross-referencing is "
        "maintained via unique document IDs."
    )
    add_bold_line("Actors: System Administrator (primary)")
    add_bold_line("Trigger: New company resources are made available and need to be searchable.")
    add_text("\n")

    # UC5
    add_heading("Use Case 5: Manage Query Boundaries", 2)
    add_normal(
        "A system administrator configures the rules governing what queries the engine "
        "can and cannot process. This includes setting input length limits, defining content "
        "filtering rules (blocking profanity, PII, prompt injection patterns), enabling or "
        "disabling specific query types, and configuring rate limits. Changes take effect "
        "immediately and are logged for audit purposes."
    )
    add_bold_line("Actors: System Administrator (primary)")
    add_bold_line("Trigger: Security policy update or detection of query abuse patterns.")
    add_text("\n")

    # ═══════════════════════════════════════
    # 3. USE CASE SPECIFICATION
    # ═══════════════════════════════════════
    add_heading("3. Use Case Specification: Search for Resources by Name or Topic", 1)
    add_normal("The following short-form use case template specifies the primary use case in detail.")
    add_text("\n")

    spec_rows = [
        ("Use Case", "UC1: Search for Resources by Name or Topic"),
        ("Scope", "Deloitte AI-Driven Search Engine Web Application"),
        ("Level", "User Goal"),
        ("Primary Actor", "Deloitte Employee"),
        ("Stakeholders and Interests",
         "Deloitte Employee: Wants to quickly find the most relevant internal resource "
         "without knowing its exact title, location, or platform.\n"
         "System Administrator: Wants search queries to stay within defined boundaries "
         "and not expose sensitive data or exploit the NLP models.\n"
         "Deloitte Management: Wants employees to spend less time searching and more time "
         "on billable work, improving overall productivity."),
        ("Preconditions",
         "The user has access to the search engine web application. The resource database "
         "has been populated with indexed documents."),
        ("Success Guarantee (Postconditions)",
         "The user is presented with a ranked list of relevant resources matching their "
         "query intent. The query and its results are logged for analytics."),
        ("Main Success Scenario",
         "1. The user navigates to the search engine web application.\n"
         "2. The user enters a natural language query into the search bar "
         "(e.g., \u201cdigital transformation client pitch deck Q3\u201d).\n"
         "3. The system validates the input (length, language, content filtering).\n"
         "4. The system classifies the user\u2019s intent and extracts entities "
         "(topic, time period, document type).\n"
         "5. The system converts the query into a vector embedding.\n"
         "6. The system performs hybrid retrieval: keyword search (BM25) and semantic "
         "search (vector cosine similarity) run in parallel.\n"
         "7. The system merges and re-ranks results using Reciprocal Rank Fusion, "
         "applying metadata signals (recency, document type).\n"
         "8. The system returns a ranked list displaying each result\u2019s title, snippet, "
         "author, date, document type, and relevance indicator.\n"
         "9. The user clicks on a result to access the full document.\n"
         "10. The system logs the query and the selected result."),
        ("Extensions (Alternate Flows)",
         "3a. Input validation fails: The system displays a specific error message "
         "(e.g., \u201cQuery too long,\u201d \u201cPlease search in English,\u201d or \u201cYour query could not "
         "be processed\u201d). The user is prompted to reformulate their query.\n"
         "6a. Zero results returned: The system displays a \u201cNo results found\u201d message "
         "along with contextual suggestions (e.g., \u201cDid you mean\u2026?\u201d corrections, "
         "related search terms, or tips for broadening the query).\n"
         "6b. Low-relevance results: The system displays results with a note encouraging "
         "the user to try filters or rephrase their query, and provides query refinement "
         "suggestions.\n"
         "8a. Rate limit exceeded: The system informs the user that they have exceeded the "
         "query limit and should try again shortly."),
        ("Special Requirements",
         "Query response time should be under 2 seconds for 95% of queries. The system "
         "must support concurrent queries from multiple users. All queries must be logged "
         "with timestamps for audit compliance."),
        ("Technology and Data Variations",
         "Queries may include free-form text, partial phrases, or questions. Documents in "
         "the index include PDFs, Word documents, PowerPoint slide decks, and images with "
         "extracted text (OCR)."),
    ]

    # Build the table
    num_rows = len(spec_rows)
    requests.append({
        "insertTable": {
            "location": {"index": idx},
            "rows": num_rows,
            "columns": 2,
        }
    })

    # ── Execute batch 1: all text + table skeleton ──
    print("\nWriting content (batch 1: text + table skeleton)...")
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests}
    ).execute()

    # ── Populate table cells ──
    doc = docs_service.documents().get(documentId=doc_id).execute()
    body = doc["body"]["content"]

    table_element = None
    for element in body:
        if "table" in element:
            table_element = element["table"]
            break

    if table_element:
        print("  Populating specification table...")
        # Process rows in REVERSE order to avoid index shifting
        for row_idx in range(num_rows - 1, -1, -1):
            field, desc = spec_rows[row_idx]
            row = table_element["tableRows"][row_idx]

            cell1 = row["tableCells"][1]
            c1_start = cell1["content"][0]["paragraph"]["elements"][0]["startIndex"]

            cell0 = row["tableCells"][0]
            c0_start = cell0["content"][0]["paragraph"]["elements"][0]["startIndex"]

            cell_requests = [
                {"insertText": {"location": {"index": c1_start}, "text": desc}},
                {"updateTextStyle": {
                    "range": {"startIndex": c1_start, "endIndex": c1_start + len(desc)},
                    "textStyle": {"fontSize": {"magnitude": 10, "unit": "PT"}},
                    "fields": "fontSize",
                }},
                {"insertText": {"location": {"index": c0_start}, "text": field}},
                {"updateTextStyle": {
                    "range": {"startIndex": c0_start, "endIndex": c0_start + len(field)},
                    "textStyle": {"bold": True, "fontSize": {"magnitude": 10, "unit": "PT"}},
                    "fields": "bold,fontSize",
                }},
            ]

            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": cell_requests}
            ).execute()

    # ── Batch 2: Diagram sections after the table ──
    doc = docs_service.documents().get(documentId=doc_id).execute()
    body = doc["body"]["content"]
    end_idx = body[-1]["endIndex"] - 1

    requests2 = []
    idx = end_idx

    def add_text2(text, style=None):
        nonlocal idx
        requests2.append({
            "insertText": {"location": {"index": idx}, "text": text}
        })
        start = idx
        idx += len(text)
        if style:
            requests2.append({
                "updateTextStyle": {
                    "range": {"startIndex": start, "endIndex": idx},
                    "textStyle": style,
                    "fields": ",".join(style.keys()),
                }
            })

    def add_heading2(text, level):
        nonlocal idx
        start = idx
        add_text2(text + "\n")
        requests2.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": idx},
                "paragraphStyle": {"namedStyleType": f"HEADING_{level}"},
                "fields": "namedStyleType",
            }
        })

    def add_normal2(text):
        add_text2(text + "\n")

    def add_image2(uri, width_pts=460):
        nonlocal idx
        requests2.append({
            "insertInlineImage": {
                "location": {"index": idx},
                "uri": uri,
                "objectSize": {
                    "width": {"magnitude": width_pts, "unit": "PT"},
                },
            }
        })
        idx += 1
        add_text2("\n")

    add_text2("\n")

    # Section 4-9 diagram sections
    sections = [
        {
            "heading": "4. Use Case Diagram",
            "intro": (
                "The Use Case Diagram below shows the interactions between the two primary actors "
                "(Deloitte Employee and System Administrator) and the five identified use cases. "
                "\u201cSearch for Information Within Documents\u201d extends the resource search since both "
                "share the same retrieval pipeline but differ in intent (finding a document vs. "
                "finding content inside a document). \u201cFilter and Refine Results\u201d also extends the "
                "search use cases as an optional post-search step."
            ),
            "image": "usecase", "width": 440,
            "desc": (
                "The Deloitte Employee interacts with the system through three use cases: searching "
                "for a known resource by name or topic (UC1), searching for specific information "
                "contained within documents without knowing the source (UC2), and filtering/refining "
                "results from either search type (UC3). UC2 extends UC1 because both use the same "
                "hybrid retrieval pipeline but UC2 emphasizes chunk-level content matching and passage "
                "highlighting rather than document-level matching. UC3 extends both UC1 and UC2 as an "
                "optional post-search step. The System Administrator manages backend operations: "
                "ingesting documents into the searchable index (UC4) and configuring query boundaries "
                "and security rules (UC5)."
            ),
        },
        {
            "heading": "5. Activity Diagram: Search for Resources",
            "intro": (
                "The Activity Diagram models the workflow of the \u201cSearch for Resources\u201d use case, "
                "showing the sequence of actions from query entry to result display, including "
                "decision points for validation and result quality."
            ),
            "image": "activity", "width": 380,
            "desc": (
                "The activity begins when a Deloitte employee enters a query. The system first "
                "validates the input\u2014rejecting queries that violate length limits, language "
                "constraints, or content policies\u2014and provides guidance for reformulation. Valid "
                "queries proceed through intent classification, embedding generation, and parallel "
                "hybrid retrieval (keyword + semantic). Results are merged via Reciprocal Rank "
                "Fusion, filtered by metadata and RBAC permissions, and displayed to the user. If "
                "no results are found, the system offers suggestions. The user may refine the query, "
                "apply filters, or select a result to view the full document. All interactions are logged."
            ),
        },
        {
            "heading": "6. Sequence Diagram: Search for Resources",
            "intro": (
                "The Sequence Diagram shows the object-level interactions that occur when a user "
                "performs a search, illustrating the messages exchanged between the frontend, backend "
                "API, NLP engine, vector store, metadata store, and ranking service."
            ),
            "image": "sequence", "width": 480,
            "desc": (
                "The sequence begins when the user enters a query in the React frontend, which sends "
                "an HTTP POST request to the FastAPI backend. The backend first validates the input "
                "through the Input Validator. If validation fails, an error with guidance is returned "
                "to the user. On success, the backend calls the NLP Engine to classify the user\u2019s "
                "intent and generate a vector embedding of the query. Two retrieval paths execute in "
                "parallel: the Vector Store (Pinecone) performs semantic similarity search while the "
                "Metadata Store (PostgreSQL) performs BM25 keyword search. Both result sets are passed "
                "to the Ranking Service, which merges them using Reciprocal Rank Fusion and applies "
                "any metadata filters. The ranked results are returned to the frontend for display. "
                "The query is logged in PostgreSQL for analytics and audit purposes."
            ),
        },
        {
            "heading": "7. Component Diagram",
            "intro": (
                "The Component Diagram shows the high-level software components of the system "
                "and their dependencies."
            ),
            "image": "component", "width": 440,
            "desc": (
                "The system is organized into four layers. The Frontend Layer consists of "
                "React + TypeScript components: the Search Interface (main search bar), Filter Panel "
                "(metadata filtering), Results Display (ranked results with metadata), and User "
                "Guidance (tips, suggestions, \u201cDid you mean?\u201d corrections). The API Layer is a "
                "FastAPI REST server with Authentication/RBAC middleware that enforces access controls "
                "and a Rate Limiter to prevent abuse. The Processing Layer contains the Input Validator "
                "(enforcing query boundaries\u2014length limits, language, PII blocking, prompt injection "
                "detection), the NLP Engine (intent classification + embedding generation using the "
                "BGE-M3 model), and the Ranking Service (Reciprocal Rank Fusion of keyword and semantic "
                "results). The Data Layer includes the Vector Store (Pinecone, for semantic search over "
                "document embeddings), the Metadata Store (PostgreSQL, for structured metadata, keyword "
                "search via BM25, and audit logs), and the Document Ingestion Pipeline (which parses "
                "incoming documents, extracts text and metadata, chunks content, generates embeddings, "
                "and stores everything with cross-referenced document IDs)."
            ),
        },
        {
            "heading": "8. Deployment Diagram",
            "intro": (
                "The Deployment Diagram shows the physical architecture\u2014how software components "
                "are deployed across hardware nodes and how they communicate."
            ),
            "image": "deployment", "width": 440,
            "desc": (
                "The deployment architecture uses Docker containers for reproducibility and "
                "cloud-readiness. The Client Workstation runs a standard web browser accessing the "
                "application over HTTPS. The Docker Host (which can be deployed to any cloud provider) "
                "runs three containers: (1) the Frontend Container serves the React + TypeScript "
                "application through an Nginx reverse proxy that handles static assets and routes API "
                "calls; (2) the Backend Container runs the FastAPI application on a Uvicorn ASGI server "
                "with the NLP Engine (BGE-M3 embedding model and intent classifier) loaded in-process "
                "for low-latency inference; (3) the Database Container runs PostgreSQL 16, which stores "
                "document metadata, supports BM25 keyword search, and maintains audit logs. The Vector "
                "Store (Pinecone) is deployed as a managed cloud service, providing optimized semantic "
                "search over document embeddings with low query latency. Communication between the "
                "frontend and backend uses REST API calls. The backend communicates with PostgreSQL "
                "via SQL/ORM and with Pinecone via its REST/gRPC API."
            ),
        },
    ]

    for sec in sections:
        add_heading2(sec["heading"], 1)
        add_normal2(sec["intro"])
        add_text2("\n")
        if sec["image"] in image_uris:
            add_image2(image_uris[sec["image"]], width_pts=sec["width"])
        add_text2("\n")
        add_normal2(sec["desc"])
        add_text2("\n")

    # Section 9: Summary
    add_heading2("9. Summary", 1)
    add_normal2(
        "This software engineering specification defines the design of the Deloitte "
        "AI-Driven Search Engine through five use cases, a detailed specification of the "
        "primary \u201cSearch for Resources by Name or Topic\u201d use case, and five UML diagrams. "
        "The system\u2019s architecture reflects the technical requirements outlined in "
        "Deloitte\u2019s project brief: a user-friendly search application with NLP-powered intent "
        "understanding, clearly defined query boundaries, built-in user guidance, and a "
        "searchable resource database. The component and deployment diagrams demonstrate a "
        "clean separation of concerns across the frontend, API, processing, and data layers, "
        "with Docker containerization ensuring a reproducible and cloud-ready deployment."
    )

    print("\nWriting content (batch 2: diagrams + remaining sections)...")
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests2}
    ).execute()

    return doc_id


def main():
    print("=" * 60)
    print("  Software Engineering Assignment -> Google Docs")
    print("=" * 60)
    print()

    creds = authenticate()

    docs_service = build("docs", "v1", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    doc_id = create_document(docs_service, drive_service)

    print("\n" + "=" * 60)
    print("  DONE!")
    print(f"  https://docs.google.com/document/d/{doc_id}/edit")
    print("=" * 60)


if __name__ == "__main__":
    main()
