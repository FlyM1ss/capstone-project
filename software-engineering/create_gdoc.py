"""
Create the Software Engineering Google Doc in the team's shared Drive folder
with all diagram images embedded inline.
"""
import sys
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.json")
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, "credentials.json")
DIAGRAMS_DIR = os.path.join(SCRIPT_DIR, "diagrams")

# Target folder: ITWS Capstone Team 2 / Term Project / SWE
TARGET_FOLDER_ID = "1Nd6oR0qiGZ-HhtEQMnme864w-qZYss_x"

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]


def authenticate():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=8085, open_browser=False)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


def upload_image(drive, filepath, filename, folder_id):
    """Upload image to Drive folder, return shareable URI."""
    media = MediaFileUpload(filepath, mimetype="image/png")
    file = drive.files().create(
        body={"name": filename, "parents": [folder_id]},
        media_body=media, fields="id"
    ).execute()
    fid = file["id"]
    drive.permissions().create(
        fileId=fid, body={"type": "anyone", "role": "reader"}
    ).execute()
    uri = f"https://drive.google.com/uc?id={fid}"
    print(f"  {filename} -> {uri}")
    return uri


def build_content(image_uris):
    """Build all Google Docs API requests for the document content."""
    requests = []
    idx = 1

    def text(t, style=None):
        nonlocal idx
        requests.append({"insertText": {"location": {"index": idx}, "text": t}})
        start = idx
        idx += len(t)
        if style:
            requests.append({"updateTextStyle": {
                "range": {"startIndex": start, "endIndex": idx},
                "textStyle": style, "fields": ",".join(style.keys()),
            }})

    def heading(t, level):
        nonlocal idx
        start = idx
        text(t + "\n")
        requests.append({"updateParagraphStyle": {
            "range": {"startIndex": start, "endIndex": idx},
            "paragraphStyle": {"namedStyleType": f"HEADING_{level}"},
            "fields": "namedStyleType",
        }})

    def body(t):
        text(t + "\n")

    def bold_line(t):
        text(t + "\n", style={"bold": True})

    def image(key, width_pts=460):
        nonlocal idx
        if key in image_uris:
            requests.append({"insertInlineImage": {
                "location": {"index": idx},
                "uri": image_uris[key],
                "objectSize": {"width": {"magnitude": width_pts, "unit": "PT"}},
            }})
            idx += 1
            text("\n")

    # ── TITLE ──
    text("Software Design and Engineering\n",
         style={"bold": True, "fontSize": {"magnitude": 22, "unit": "PT"}})
    text("AI-Driven Company-Wide Search Engine for Deloitte Resources\n",
         style={"italic": True, "fontSize": {"magnitude": 13, "unit": "PT"}})
    text("\n")
    bold_line("Group Two")
    body("Jesse Gabriel, Andrew Jung, Raven Levitt, Felix Tian, Sophia Turnbow, Matthew Voynovich")
    text("\n")
    body("Information Technology Capstone \u2014 ITWS 4100")
    body("Professor Richard Plotka")
    body("Spring 2026")
    text("\n\n")

    # ── 1. INTRODUCTION ──
    heading("1. Introduction", 1)
    body(
        "This document describes the software design and engineering specifications "
        "for the AI-Driven Company-Wide Search Engine being developed for Deloitte. "
        "The system is a web application that enables Deloitte employees to search "
        "across internal resources\u2014documents, policies, slide decks, and images\u2014"
        "using natural language queries. It leverages Natural Language Processing (NLP) "
        "with hybrid retrieval (combining semantic search and keyword matching) to "
        "understand user intent and return relevant results even when the query wording "
        "does not exactly match the document text."
    )
    text("\n")
    body(
        "The software design follows standard UML modeling practices to describe the "
        "system\u2019s behavior, structure, and deployment. This section identifies core "
        "use cases, specifies the primary use case in detail, and provides Use Case, "
        "Activity, Sequence, Component, and Deployment diagrams."
    )
    text("\n")

    # ── 2. USE CASES ──
    heading("2. Use Cases", 1)
    body(
        "Five use cases have been identified for the Deloitte AI Search Engine. "
        "These represent the primary interactions between users (Deloitte employees "
        "and system administrators) and the system."
    )
    text("\n")

    heading("Use Case 1: Search for Resources by Name or Topic (Primary)", 2)
    body(
        "The core use case of the system. A Deloitte employee enters a natural language "
        "query into the search bar to locate a specific known resource (e.g., \u201cQ4 "
        "healthcare consulting deck\u201d or \u201ctravel reimbursement policy\u201d). The system "
        "processes the query through input validation, intent classification, and entity "
        "extraction, then performs hybrid retrieval (semantic + keyword search) against the "
        "indexed resource database. Results are ranked by relevance and presented with "
        "title, snippet, author, date, and document type. The user can click on a result "
        "to access the document."
    )
    bold_line("Actors: Deloitte Employee (primary)")
    bold_line("Trigger: Employee needs to locate a specific internal resource by name, topic, or description.")
    text("\n")

    heading("Use Case 2: Search for Information Within Documents", 2)
    body(
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
    bold_line("Actors: Deloitte Employee (primary)")
    bold_line("Trigger: Employee needs a specific data point, fact, or policy detail but does not know which document contains it.")
    text("\n")

    heading("Use Case 3: Filter and Refine Search Results", 2)
    body(
        "After performing an initial search, a user applies metadata filters to narrow "
        "down the result set. Available filters include document type (PDF, slide deck, "
        "policy document, image), date range, author, and department. The system re-ranks "
        "and redisplays results based on the applied filters without requiring a new query."
    )
    bold_line("Actors: Deloitte Employee (primary)")
    bold_line("Trigger: Initial search returns too many results or the user wants to scope results to a specific category.")
    text("\n")

    heading("Use Case 4: Ingest and Index Documents", 2)
    body(
        "A system administrator uploads new documents (PDFs, Word files, slide decks) "
        "into the system. The ingestion pipeline extracts text and metadata, chunks long "
        "documents, generates vector embeddings, and stores both the metadata (in PostgreSQL) "
        "and embeddings (in the vector store) for future retrieval. Cross-referencing is "
        "maintained via unique document IDs."
    )
    bold_line("Actors: System Administrator (primary)")
    bold_line("Trigger: New company resources are made available and need to be searchable.")
    text("\n")

    heading("Use Case 5: Manage Query Boundaries", 2)
    body(
        "A system administrator configures the rules governing what queries the engine "
        "can and cannot process. This includes setting input length limits, defining content "
        "filtering rules (blocking profanity, PII, prompt injection patterns), enabling or "
        "disabling specific query types, and configuring rate limits. Changes take effect "
        "immediately and are logged for audit purposes."
    )
    bold_line("Actors: System Administrator (primary)")
    bold_line("Trigger: Security policy update or detection of query abuse patterns.")
    text("\n")

    # ── 3. USE CASE SPECIFICATION ──
    heading("3. Use Case Specification: Search for Resources by Name or Topic", 1)
    body("The following short-form use case template specifies the primary use case in detail.")
    text("\n")

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

    # Insert table skeleton
    requests.append({"insertTable": {
        "location": {"index": idx},
        "rows": len(spec_rows), "columns": 2,
    }})

    return requests, spec_rows, idx


def main():
    print("=" * 60)
    print("  Creating Google Doc in Team SWE Folder")
    print("=" * 60)

    creds = authenticate()
    docs = build("docs", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)

    # ── Upload diagrams ──
    print("\nUploading diagrams to SWE folder...")
    diagram_names = ["usecase", "activity", "sequence", "component", "deployment"]
    image_uris = {}
    for name in diagram_names:
        path = os.path.join(DIAGRAMS_DIR, f"{name}.png")
        if os.path.exists(path):
            image_uris[name] = upload_image(drive, path, f"SE_Diagram_{name}.png", TARGET_FOLDER_ID)

    # ── Create doc in the target folder via Drive API ──
    print("\nCreating Google Doc in folder...")
    file_meta = {
        "name": "Software Design and Engineering \u2014 Group Two (Draft)",
        "mimeType": "application/vnd.google-apps.document",
        "parents": [TARGET_FOLDER_ID],
    }
    created = drive.files().create(body=file_meta, fields="id").execute()
    doc_id = created["id"]
    print(f"  Doc ID: {doc_id}")
    print(f"  URL: https://docs.google.com/document/d/{doc_id}/edit")

    # ── Batch 1: Title + Use Cases + Table skeleton ──
    print("\nWriting batch 1 (text + table skeleton)...")
    reqs, spec_rows, _ = build_content(image_uris)
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": reqs}).execute()

    # ── Populate table cells (reverse order to avoid index shift) ──
    print("  Populating specification table...")
    doc = docs.documents().get(documentId=doc_id).execute()
    table = None
    for el in doc["body"]["content"]:
        if "table" in el:
            table = el["table"]
            break

    if table:
        for ri in range(len(spec_rows) - 1, -1, -1):
            field, desc = spec_rows[ri]
            row = table["tableRows"][ri]
            c1_start = row["tableCells"][1]["content"][0]["paragraph"]["elements"][0]["startIndex"]
            c0_start = row["tableCells"][0]["content"][0]["paragraph"]["elements"][0]["startIndex"]
            docs.documents().batchUpdate(documentId=doc_id, body={"requests": [
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
            ]}).execute()

    # ── Batch 2: Diagram sections + Summary ──
    print("Writing batch 2 (diagrams + descriptions)...")
    doc = docs.documents().get(documentId=doc_id).execute()
    end_idx = doc["body"]["content"][-1]["endIndex"] - 1

    reqs2 = []
    idx = end_idx

    def text2(t, style=None):
        nonlocal idx
        reqs2.append({"insertText": {"location": {"index": idx}, "text": t}})
        start = idx; idx += len(t)
        if style:
            reqs2.append({"updateTextStyle": {
                "range": {"startIndex": start, "endIndex": idx},
                "textStyle": style, "fields": ",".join(style.keys()),
            }})

    def heading2(t, level):
        nonlocal idx
        start = idx; text2(t + "\n")
        reqs2.append({"updateParagraphStyle": {
            "range": {"startIndex": start, "endIndex": idx},
            "paragraphStyle": {"namedStyleType": f"HEADING_{level}"},
            "fields": "namedStyleType",
        }})

    def body2(t): text2(t + "\n")

    def img2(key, w=460):
        nonlocal idx
        if key in image_uris:
            reqs2.append({"insertInlineImage": {
                "location": {"index": idx},
                "uri": image_uris[key],
                "objectSize": {"width": {"magnitude": w, "unit": "PT"}},
            }})
            idx += 1; text2("\n")

    text2("\n")

    sections = [
        ("4. Use Case Diagram",
         "The Use Case Diagram below shows the interactions between the two primary actors "
         "(Deloitte Employee and System Administrator) and the five identified use cases. "
         "\u201cSearch for Information Within Documents\u201d extends the resource search since both "
         "share the same retrieval pipeline but differ in intent (finding a document vs. "
         "finding content inside a document). \u201cFilter and Refine Results\u201d also extends the "
         "search use cases as an optional post-search step.",
         "usecase", 440,
         "The Deloitte Employee interacts with the system through three use cases: searching "
         "for a known resource by name or topic (UC1), searching for specific information "
         "contained within documents without knowing the source (UC2), and filtering/refining "
         "results from either search type (UC3). UC2 extends UC1 because both use the same "
         "hybrid retrieval pipeline but UC2 emphasizes chunk-level content matching and passage "
         "highlighting rather than document-level matching. UC3 extends both UC1 and UC2 as an "
         "optional post-search step. The System Administrator manages backend operations: "
         "ingesting documents into the searchable index (UC4) and configuring query boundaries "
         "and security rules (UC5)."),
        ("5. Activity Diagram: Search for Resources",
         "The Activity Diagram models the workflow of the \u201cSearch for Resources\u201d use case, "
         "showing the sequence of actions from query entry to result display, including "
         "decision points for validation and result quality.",
         "activity", 380,
         "The activity begins when a Deloitte employee enters a query. The system first "
         "validates the input\u2014rejecting queries that violate length limits, language "
         "constraints, or content policies\u2014and provides guidance for reformulation. Valid "
         "queries proceed through intent classification, embedding generation, and parallel "
         "hybrid retrieval (keyword + semantic). Results are merged via Reciprocal Rank "
         "Fusion, filtered by metadata and RBAC permissions, and displayed to the user. If "
         "no results are found, the system offers suggestions. The user may refine the query, "
         "apply filters, or select a result to view the full document. All interactions are logged."),
        ("6. Sequence Diagram: Search for Resources",
         "The Sequence Diagram shows the object-level interactions that occur when a user "
         "performs a search, illustrating the messages exchanged between the frontend, backend "
         "API, NLP engine, vector store, metadata store, and ranking service.",
         "sequence", 480,
         "The sequence begins when the user enters a query in the React frontend, which sends "
         "an HTTP POST request to the FastAPI backend. The backend first validates the input "
         "through the Input Validator. If validation fails, an error with guidance is returned "
         "to the user. On success, the backend calls the NLP Engine to classify the user\u2019s "
         "intent and generate a vector embedding of the query. Two retrieval paths execute in "
         "parallel: the Vector Store (Pinecone) performs semantic similarity search while the "
         "Metadata Store (PostgreSQL) performs BM25 keyword search. Both result sets are passed "
         "to the Ranking Service, which merges them using Reciprocal Rank Fusion and applies "
         "any metadata filters. The ranked results are returned to the frontend for display. "
         "The query is logged in PostgreSQL for analytics and audit purposes."),
        ("7. Component Diagram",
         "The Component Diagram shows the high-level software components of the system "
         "and their dependencies.",
         "component", 440,
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
         "and stores everything with cross-referenced document IDs)."),
        ("8. Deployment Diagram",
         "The Deployment Diagram shows the physical architecture\u2014how software components "
         "are deployed across hardware nodes and how they communicate.",
         "deployment", 440,
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
         "via SQL/ORM and with Pinecone via its REST/gRPC API."),
    ]

    for h, intro, img_key, w, desc in sections:
        heading2(h, 1)
        body2(intro)
        text2("\n")
        img2(img_key, w)
        text2("\n")
        body2(desc)
        text2("\n")

    heading2("9. Summary", 1)
    body2(
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

    docs.documents().batchUpdate(documentId=doc_id, body={"requests": reqs2}).execute()

    print("\n" + "=" * 60)
    print("  DONE!")
    print(f"  https://docs.google.com/document/d/{doc_id}/edit")
    print("=" * 60)


if __name__ == "__main__":
    main()
