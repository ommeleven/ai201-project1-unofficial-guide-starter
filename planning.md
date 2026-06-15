# Project 1 Planning: The Unofficial Guide
> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

Professor and course reviews for DePaul University. Students at DePaul must make high-stakes decisions about which professors to take each quarter — but official channels (the course catalog, department websites, academic advisors) only describe course content, never teaching quality, grading fairness, exam difficulty, or actual workload. This knowledge exists but is scattered across Rate My Professors, Reddit threads, and word-of-mouth. An unofficial guide makes it searchable and synthesized in one place.

---

## Documents

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Rate My Professors | Reviews for Kenshu Shimada | https://www.ratemyprofessors.com/professor/363670 |
| 2 | Rate My Professors | Reviews for DePaul Jennifer Zimmerman | https://www.ratemyprofessors.com/professor/1415753 |
| 3 | Rate My Professors | Reviews for DePaul Joanna Dabrowska | https://www.ratemyprofessors.com/professor/1849878 |
| 4 | Rate My Professors | Reviews for DePaul Naomi Steinberg | https://www.ratemyprofessors.com/professor/371794 |
| 5 | Rate My Professors | Reviews for DePaul Marshall Brown | https://www.ratemyprofessors.com/professor/2479484 |
| 6 | Reddit | DePaul professor recommendations thread | docs/reddit_1.txt |
| 7 | Reddit | DePaul course advice megathread | docs/reddit_2.txt |
| 8 | Reddit | DePaul CS department discussion | docs/reddit_3.txt |
| 9 | Reddit | DePaul difficult courses thread | docs/reddit_4.txt |
| 10 | Reddit | General DePaul academic tips thread | docs/reddit_5.txt |

> Note: Rate My Professors blocks automated scraping. All documents are collected manually by copy-pasting review text into local .txt files under docs/. Files are named prof_lastname_dept.txt (e.g., prof_smith_cs.txt) and reddit_N.txt.

---

## Chunking Strategy

**Chunk size:** 400 characters

**Overlap:** 80 characters

**Reasoning:**
RMP reviews are short and opinion-dense — typically 2–5 sentences covering one professor. A 400-character chunk captures roughly one complete review without merging unrelated opinions from different reviewers. This keeps each embedding focused on a single perspective, which improves retrieval precision.

Overlap of 80 characters (roughly one sentence) ensures that a key fact appearing at the end of one chunk — for example, "curves heavily" or "never responds to email" — isn't orphaned if it bleeds into the next chunk boundary. Without overlap, a review that mentions exam difficulty in its first half and grading policy in its second half could split such that neither chunk alone answers a grading question.

Chunks smaller than ~200 characters risk fragmenting a single sentence, producing embeddings with too little semantic signal. Chunks larger than ~600 characters risk blending opinions about exam style, teaching quality, and workload into one diluted embedding that matches nothing precisely in retrieval.

---

## Retrieval Approach

**Embedding model:** all-MiniLM-L6-v2 via sentence-transformers

**Top-k:** 5 chunks per query

**Production tradeoff reflection:**
all-MiniLM-L6-v2 runs entirely locally with no API key or rate limits, making it ideal for a prototype. It produces 384-dimensional embeddings and handles short, opinion-based text well.

For a real deployment, I would weigh several tradeoffs:
- **OpenAI text-embedding-3-small**: Higher accuracy on domain-specific phrasing (e.g., academic jargon like "curved," "TAs graded," "attendance policy"), but adds API cost, latency, and a network dependency.
- **multilingual-e5-large**: Useful if the student population writes reviews in multiple languages, but much larger and slower to run locally.
- **Context length**: all-MiniLM-L6-v2 has a 256-token limit per input. At 400-character chunks this is fine (~90–120 tokens), but longer documents would require a different model.

Top-k of 5 gives the LLM enough review variety to synthesize a grounded answer. Fewer than 3 risks missing the most relevant review entirely; more than 8 starts introducing loosely related content that can dilute the response or pull the model off-topic.

---

## Evaluation Plan

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What do students say about [Professor A]'s exams? | Should mention difficulty level, whether they're curved, and what material is tested (lecture vs. textbook) |
| 2 | Is [Professor B] a good professor for someone new to the subject? | Should reference teaching clarity, pace for beginners, and approachability based on reviews |
| 3 | How heavy is the workload for [Course Name or Number]? | Should cite weekly hours, assignment volume, or project count mentioned in reviews |
| 4 | Does [Professor C] curve grades? | Should give a clear yes/no with supporting evidence quoted or paraphrased from reviews |
| 5 | Which professors in the CS department should I avoid and why? | Should name at least one professor with consistently negative reviews and explain the specific complaints |

> Note: Replace bracketed professor/course names with actual names from your collected documents before running evaluation.

---

## Anticipated Challenges

1. **Chunk boundary splits on multi-topic reviews**: Some reviews discuss exam difficulty, grading fairness, and teaching style all in one paragraph. A 400-character chunk may split such that the grading comment appears in one chunk and the exam comment in another — neither chunk alone is sufficient to answer a question that requires both facts. The 80-character overlap partially mitigates this but does not fully solve it.

2. **Professor name variations**: Students write "Prof. Smith," "Smith," "Dr. Smith," "John Smith," and even nicknames. The embedding model treats these as different tokens and may not unify them semantically. A query for "Professor Smith" could miss reviews that only refer to "Dr. Smith" or just "Smith." This could cause retrieval to return low-relevance chunks for name-specific queries.

---

## Architecture

```
[docs/*.txt files on disk]
           |
           v
  ┌─────────────────────┐
  │  Document Ingestion │  ingest.py — Python file I/O (os.listdir + open)
  └─────────────────────┘
           |
           v
  ┌─────────────────────┐
  │ Cleaning + Chunking │  ingest.py — strip whitespace/artifacts,
  └─────────────────────┘  split into 400-char chunks, 80-char overlap
           |
           v
  ┌──────────────────────────┐
  │ Embedding + Vector Store │  embed.py — all-MiniLM-L6-v2 (sentence-transformers)
  └──────────────────────────┘             → ChromaDB (local persistent store)
           |
           v
  ┌─────────────────────┐
  │     Retrieval       │  embed.py — retrieve(query, k=5) returns top-k chunks
  └─────────────────────┘             with source metadata
           |
           v
  ┌─────────────────────┐
  │     Generation      │  app.py — Groq llama-3.3-70b-versatile
  └─────────────────────┘           grounded prompt: answer from context only
           |
           v
  ┌─────────────────────┐
  │   Gradio Interface  │  app.py — localhost:7860
  └─────────────────────┘           inputs: query textbox
                                    outputs: answer + sources textbox
```

---

## AI Tool Plan

**Milestone 3 — Ingestion and chunking:**
Tool: Claude. Input: the Documents section (file naming convention, .txt format, manual collection method) and the Chunking Strategy section (400-char chunks, 80-char overlap, reasoning about review length). Ask Claude to implement `ingest.py` with a `load_documents(docs_dir)` function that reads all .txt files, cleans whitespace and non-content artifacts, and a `chunk_text(text, chunk_size=400, overlap=80)` function that returns a list of dicts with keys `text`, `source`, and `chunk_index`. Verify output by printing 5 random chunks and checking each is readable, self-contained, and correctly attributed to its source file.

**Milestone 4 — Embedding and retrieval:**
Tool: Claude. Input: the Retrieval Approach section (all-MiniLM-L6-v2, top-k=5, ChromaDB) and the output format of `ingest.py` (list of dicts with `text`, `source`, `chunk_index`). Ask Claude to implement `embed.py` with an `embed_and_store(chunks)` function that initializes ChromaDB with a persistent local path, embeds each chunk using SentenceTransformer, and stores it with source metadata. Also implement `retrieve(query, k=5)` that returns top-k chunks with their source filenames and distance scores. Verify by running 3 evaluation queries and confirming returned chunks are topically relevant and distance scores are below 0.5.

**Milestone 5 — Generation and interface:**
Tool: Claude. Input: the grounding requirement (LLM must answer only from retrieved context, must cite sources, must decline if context is insufficient), the output format of `retrieve()`, and the Gradio skeleton from the spec. Ask Claude to implement `app.py` that calls `retrieve()`, builds a prompt that passes retrieved chunks as context with an explicit instruction to not use outside knowledge, calls Groq llama-3.3-70b-versatile, and returns a response with source filenames appended. Verify grounding by checking that responses reference specific details from retrieved chunks and that an out-of-scope query triggers a refusal rather than a hallucinated answer.