# DePaul University Unofficial Guide
> A RAG-powered search system for student reviews of DePaul professors and courses.

---

## Domain and Document Sources

**Domain:** Professor and course reviews for DePaul University. Students must make high-stakes decisions each quarter about which professors to take, but official channels (course catalogs, department websites, advisors) only describe course content — never teaching quality, grading fairness, exam difficulty, or actual workload. This knowledge exists but is scattered across Rate My Professors, Reddit threads, and word-of-mouth. This system makes it searchable and synthesized.

**Sources (10 documents, all in `docs/`):**

| File | Source | Description |
|------|--------|-------------|
| `prof_brown_math.txt` | Rate My Professors | Student reviews of Prof. Brown (Math) |
| `prof_dabrowska_acc.txt` | Rate My Professors | Student reviews of Prof. Dabrowska (Accounting) |
| `prof_shimada_bio.txt` | Rate My Professors | Student reviews of Prof. Shimada (Biology) |
| `prof_steingburg_rel.txt` | Rate My Professors | Student reviews of Prof. Steingburg (Religion) |
| `prof_zimmerman_psy.txt` | Rate My Professors | Student reviews of Prof. Zimmerman (Psychology) |
| `reddit_1.txt` | r/DePaul | Professor recommendations thread |
| `reddit_2.txt` | r/DePaul | Course advice and professor experiences |
| `reddit_3.txt` | r/DePaul | CS/academic department discussion |
| `reddit_4.txt` | r/DePaul | Difficult courses and grading thread |
| `reddit_5.txt` | r/DePaul | General DePaul academic tips |

---

## Chunking Strategy and Reasoning

**Chunk size:** 400 characters
**Overlap:** 80 characters

RMP reviews are short and opinion-dense — typically 2–5 sentences covering one professor. A 400-character chunk captures roughly one complete review without merging unrelated opinions from different reviewers, keeping each embedding focused on a single perspective. Overlap of 80 characters (~1 sentence) ensures that a key fact at a chunk boundary — for example, "curves heavily" or "never responds to email" — isn't orphaned if it bleeds into the next chunk.

Chunks smaller than ~200 characters fragment individual sentences, producing embeddings with too little semantic signal. Chunks larger than ~600 characters blend opinions about exam style, teaching quality, and workload into one diluted embedding that matches nothing precisely in retrieval.

---

## Sample Chunks

**Chunk 1** — `prof_shimada_bio.txt` (chunk_index: 2)
```
Dr. Shimada is very knowledgeable but his teaching strategy is difficult. It's all lecture, and you need to do a lot of outside work to actually conceptualize the material. GET READY TO READ.
```

**Chunk 2** — `prof_dabrowska_acc.txt` (chunk_index: 0)
```
She is so good at teaching and her professionalism is great! AMAZING LECTURES. CLEAR GRADING CRITERIA. One of the best accounting professors at DePaul. She cares about her students learning.
```

**Chunk 3** — `prof_brown_math.txt` (chunk_index: 1)
```
Hands down best teacher at DePaul. Don't pay attention to all the other reviews. Most assignments are simple and exams are online multiple choice. Grade: A. Would Take Again: Yes.
```

**Chunk 4** — `reddit_2.txt` (chunk_index: 0)
```
The English teacher who flunked me for being tardy by less than 5 minutes the 3rd time to her 8:30am class. This was my 1st semester Freshman year, I was trending towards an A- and she auto F'd me.
```

**Chunk 5** — `prof_zimmerman_psy.txt` (chunk_index: 3)
```
Zimmerman is hit or miss. Some students love his style and find it engaging, others feel the course moves too fast. Attendance is mandatory and participation counts toward your grade.
```

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`

This model runs entirely locally with no API key or rate limits, producing 384-dimensional embeddings well-suited for short, opinion-based text. It was the right choice for a local prototype.

**Production tradeoff reflection:**
For a real deployment I would weigh several alternatives:
- **OpenAI text-embedding-3-small**: Higher accuracy on domain-specific phrasing (e.g., "curved," "TAs graded," "attendance policy") but adds API cost, latency, and a network dependency.
- **multilingual-e5-large**: Useful if the student population writes in multiple languages, but much larger and slower locally.
- **Context length**: `all-MiniLM-L6-v2` has a 256-token limit per input. At 400-character chunks (~90–120 tokens) this is fine, but longer documents would require a different model.
- **Latency vs. accuracy**: A larger model like `bge-large-en-v1.5` improves retrieval precision on short queries but adds ~3–4x inference time, which matters at scale.

---

## Retrieval Test Results

**Query 1:** "What do students say about Professor Brown's exams?"

Top returned chunks:
- `prof_brown_math.txt` (dist=0.49) — *"Most assignments are simple and exams are online multiple choice..."*
- `prof_shimada_bio.txt` (dist=0.51) — *"Dr. Shimada is very knowledgeable but his teaching strategy is difficult..."*
- `prof_zimmerman_psy.txt` (dist=0.54) — *"Zimmerman is hit or miss..."*

**Why relevant:** The top result directly mentions Brown's exam format (online multiple choice). The other two are pulled in because they also discuss professor difficulty and teaching style — semantically related even without exact word overlap on "exams."

---

**Query 2:** "How heavy is the workload for Professor Shimada's class?"

Top returned chunks:
- `prof_shimada_bio.txt` (dist=0.48) — *"It's all lecture, and you need to do a lot of outside work... GET READY TO READ."*
- `prof_shimada_bio.txt` (dist=0.50) — *"LECTURE HEAVY. TEST HEAVY. Outside reading required every week."*
- `prof_dabrowska_acc.txt` (dist=0.55) — *"She cares about her students learning..."*

**Why relevant:** The top two results are directly from Shimada's reviews and explicitly describe workload with phrases like "LECTURE HEAVY" and "outside work." The third result is less relevant — it matches on general professor-quality language rather than workload specifics, which is a retrieval imprecision at k=5.

---

**Query 3:** "Does any professor at DePaul curve grades?"

Top returned chunks:
- `prof_shimada_bio.txt` (dist=0.47) — *"Professor Shimada does not curve grades."*
- `prof_brown_math.txt` (dist=0.51) — *"Grade: A. Would Take Again: Yes."*
- `prof_dabrowska_acc.txt` (dist=0.53) — *"CLEAR GRADING CRITERIA."*

**Why relevant:** The top result directly answers the curving question for Shimada. The other two match on grading-related language semantically (grades, grading criteria) even though they don't explicitly mention curving — demonstrating how semantic search finds topically adjacent content without exact keyword matches.

---

## Grounded Generation

Grounding is enforced through the system prompt passed to `llama-3.3-70b-versatile` on every request:

```
You answer questions about professors and courses using ONLY the student reviews
and posts provided to you as context.

Rules:
1. Answer ONLY from the provided context. Do not use your general training knowledge.
2. If the context does not contain enough information, say exactly:
   "I don't have enough information in my documents to answer that."
3. Always cite which source document(s) your answer draws from.
```

Retrieved chunks are injected into the user prompt as labeled context blocks (`[Document N | Source: filename]`). The model is explicitly told not to use outside knowledge, and source citation is required in every response. This makes it structurally impossible for the model to give an answer without referencing the provided documents.

---

## Example Responses

**Example 1 — Grounded answer with source citation:**

> Query: *"How heavy is the workload for Professor Shimada's class?"*
>
> Response: *"According to prof_shimada_bio.txt (Documents 1, 2, and 3), the workload for Professor Shimada's class is described as 'LECTURE HEAVY' and 'TEST HEAVY', indicating a significant amount of work required. Document 2 states that 'you need to do a lot of outside work to actually conceptualize the material', suggesting that the workload extends beyond lectures and tests. Document 3 also mentions 'GET READY TO READ', implying a substantial reading requirement."*
>
> Sources: `prof_shimada_bio.txt`, `prof_zimmerman_psy.txt`

---

**Example 2 — Grounded answer with appropriate uncertainty:**

> Query: *"Is Professor Dabrowska good for beginners?"*
>
> Response: *"According to prof_dabrowska_acc.txt, Professor Dabrowska is described as an 'amazing teacher' who made learning easy and is considered 'one of the best accounting professors at DePaul.' While these reviews do not explicitly state that she is good for beginners, they suggest she is a skilled and effective teacher. I don't have enough information in my documents to answer that specifically."*
>
> Sources: `prof_dabrowska_acc.txt`, `prof_steingburg_rel.txt`

---

**Example 3 — Out-of-scope refusal:**

> Query: *"What is the best pizza place near DePaul?"*
>
> Response: *"I don't have enough information in my documents to answer that. The provided documents only contain student reviews of DePaul professors and courses, and do not include information about restaurants or food options near campus."*
>
> Sources: (none cited)

---

## Query Interface

**Input fields:**
- `Your question` — a free-text textbox where the user types any question about DePaul professors or courses

**Output fields:**
- `Answer` — the LLM's grounded response citing source documents
- `Retrieved from` — a list of source filenames that were retrieved and passed as context

**Sample interaction transcript:**

```
User: What do students say about Professor Brown's exams?

Answer: According to prof_brown_math.txt (Documents 2 and 4), students say that
Professor Brown's exams are online multiple choice. One student mentions that most
assignments are simple, but does not specifically comment on the exams being easy
or hard. No other documents provide additional detail about exam difficulty.

Retrieved from:
• prof_shimada_bio.txt
• prof_brown_math.txt
• prof_zimmerman_psy.txt
```

---

## Evaluation Report

| # | Question | Expected Answer | System Response | Accuracy |
|---|----------|-----------------|-----------------|----------|
| 1 | What do students say about Professor Brown's exams? | Mentions format, difficulty, and what material is tested | Correctly identified online multiple choice format; noted limited detail on difficulty | **Partially accurate** |
| 2 | Is Professor Dabrowska good for beginners? | References teaching clarity and approachability from reviews | Cited positive reviews accurately; correctly flagged no explicit beginner-specific info | **Partially accurate** |
| 3 | How heavy is the workload for Professor Shimada's class? | Cites reading load, lecture density, outside work from reviews | Accurately cited "LECTURE HEAVY," "TEST HEAVY," and outside reading requirement | **Accurate** |
| 4 | Does any professor at DePaul curve grades? | Names a professor with clear curving policy from reviews | Correctly stated Shimada does not curve, with no false claims about others | **Accurate** |
| 5 | Which professor should I avoid and why? | Names a professor with consistently negative reviews and specific complaints | Drew from Shimada's difficult teaching style reviews with specific supporting detail | **Accurate** |

---

## Failure Case Analysis

**Question 1** ("What do students say about Professor Brown's exams?") returned a partially accurate response.

**What went wrong:** The retrieved chunks for Brown contained RMP metadata artifacts — text like `"Rating Distribution / Awesome 5 / Great 4"` and `"I'm Professor Brown"` — that survived the cleaning step. These artifact-heavy chunks occupied retrieval slots that should have gone to substantive review text. As a result, the LLM had limited real review content to work with and could only confirm the exam format (online multiple choice) without providing detail on difficulty or content focus.

**Pipeline cause:** The cleaning function in `ingest.py` strips Reddit UI artifacts but does not fully handle RMP page structure, which includes rating widgets, comparison headers, and professor self-description text embedded in the copy-pasted content. The chunk that returned `"I'm Professor Brown / Rating Distribution / Awesome 5..."` is a cleaning failure — it should have been filtered out entirely. A fix would be to add RMP-specific cleaning patterns (e.g., strip lines matching `"Rating Distribution"`, `"Awesome \d"`, `"Similar Professors"`) before chunking.

---

## Spec Reflection

**One way the spec helped:** Writing the chunking strategy section of `planning.md` before any code forced a concrete decision about chunk size and overlap before seeing the actual documents. This meant that when I later printed sample chunks and saw a fragment like `"nd this professor! She is so good"` (a chunk starting mid-word due to a boundary landing on a copy-paste artifact), I had a clear spec to compare against and knew immediately the cleaning step needed improvement — rather than just accepting the output.

**One way implementation diverged from the spec:** The spec called for ChromaDB as the vector store. On Apple Silicon with Python 3.13, ChromaDB caused a segmentation fault on import due to a PyTorch compatibility issue. The implementation was changed to a lightweight numpy-based store (saving embeddings as `.npy` and chunk metadata as `.json`, with cosine similarity computed manually). This divergence had no effect on retrieval quality — cosine similarity is cosine similarity — but it simplified the dependency stack and eliminated the environment conflict.

---

## AI Usage

**Instance 1 — Generating `ingest.py` and `embed.py`:**
I provided Claude with the Chunking Strategy and Retrieval Approach sections of `planning.md` and asked it to implement `ingest.py` (load .txt files, clean Reddit artifacts, split into 400-char chunks with 80-char overlap) and `embed.py` (embed with all-MiniLM-L6-v2, store with cosine similarity, implement `retrieve(query, k)`). Claude generated both files. I overrode the ChromaDB dependency after a segmentation fault on Apple Silicon and directed Claude to rewrite `embed.py` using numpy arrays instead, which I verified by checking that cosine similarity scores matched expected ranges (below 0.5 for relevant results).

**Instance 2 — Fixing the `get_collection` import error in `app.py`:**
After replacing `embed.py` with the numpy version, `app.py` still imported `get_collection`, a function that no longer existed. I gave Claude the error traceback and asked it to rewrite `app.py` to remove the dependency on `get_collection` and update `ensure_vector_store()` to check for the `.json` chunk file instead. I reviewed the generated fix to confirm the startup check correctly detected an existing store and skipped re-embedding, then tested it end-to-end before accepting it.