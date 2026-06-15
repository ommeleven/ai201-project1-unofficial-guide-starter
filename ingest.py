import os
import re

def load_documents(docs_dir="docs"):
    """Load all .txt files from docs_dir, return list of {text, source}."""
    documents = []
    for filename in os.listdir(docs_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(docs_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                raw = f.read()
            cleaned = clean_text(raw)
            if cleaned.strip():
                documents.append({"text": cleaned, "source": filename})
    print(f"Loaded {len(documents)} documents from '{docs_dir}'")
    return documents


def clean_text(text):
    """Remove Reddit UI artifacts and normalize whitespace."""
    # Remove Reddit voting/action buttons that appear in copy-pasted text
    noise_patterns = [
        r'\bUpvote\b', r'\bDownvote\b', r'\bReply\b', r'\bAward\b',
        r'\bShare\b', r'\bReport\b', r'\bSave\b', r'\bFollow\b',
        r'\bOP\b', r'•', r'\d+[yd]r?\s+ago',   # "3y ago", "2d ago"
        r'CollegeSnitch',                          # username artifacts
        r'Posted by u/\S+',
        r'r/\w+ +•',
        r'View all comments',
        r'Add a comment',
        r'Sort by:?\s*(Best|Top|New|Controversial)',
        r'\[\+\]', r'\[-\]',
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Collapse multiple blank lines into one
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.splitlines()]
    # Remove lines that are just numbers (vote counts)
    lines = [l for l in lines if not re.fullmatch(r'\d+', l)]
    # Remove empty lines that are now isolated
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def chunk_text(text, source, chunk_size=400, overlap=80):
    """
    Split text into chunks of ~chunk_size characters with overlap.
    Returns list of dicts: {text, source, chunk_index}
    """
    chunks = []
    start = 0
    chunk_index = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size

        # If not at the end, try to break at a sentence boundary
        if end < text_len:
            # Look for sentence-ending punctuation followed by whitespace
            boundary = -1
            for punct in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                idx = text.rfind(punct, start, end)
                if idx != -1 and idx > boundary:
                    boundary = idx + len(punct)
            if boundary != -1 and boundary > start + (chunk_size // 2):
                end = boundary
            # Otherwise fall back to word boundary
            else:
                space = text.rfind(' ', start, end)
                if space != -1 and space > start:
                    end = space + 1

        chunk = text[start:end].strip()
        if len(chunk) > 20:  # skip tiny fragments
            chunks.append({
                "text": chunk,
                "source": source,
                "chunk_index": chunk_index
            })
            chunk_index += 1

        start = end - overlap  # move back by overlap for next chunk
        if start >= text_len:
            break

    return chunks


def ingest_all(docs_dir="docs", chunk_size=400, overlap=80):
    """Full pipeline: load → clean → chunk all documents."""
    documents = load_documents(docs_dir)
    all_chunks = []
    for doc in documents:
        chunks = chunk_text(doc["text"], doc["source"], chunk_size, overlap)
        all_chunks.extend(chunks)
    print(f"Produced {len(all_chunks)} total chunks across {len(documents)} documents")
    return all_chunks


if __name__ == "__main__":
    import random
    chunks = ingest_all()
    print(f"\n--- 5 random sample chunks ---\n")
    samples = random.sample(chunks, min(5, len(chunks)))
    for i, c in enumerate(samples, 1):
        print(f"[Chunk {i} | source: {c['source']} | index: {c['chunk_index']}]")
        print(c['text'])
        print()
