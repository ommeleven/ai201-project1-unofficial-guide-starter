import os
from groq import Groq
from embed import retrieve, embed_and_store
from ingest import ingest_all
import gradio as gr

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a helpful unofficial guide for DePaul University students.
You answer questions about professors and courses using ONLY the student reviews and posts provided to you as context.

Rules you must follow:
1. Answer ONLY from the provided context. Do not use your general training knowledge about universities, teaching, or professors.
2. If the context does not contain enough information to answer the question, say exactly: "I don't have enough information in my documents to answer that."
3. Always cite which source document(s) your answer draws from (e.g., "According to prof_brown_math.txt...").
4. Be direct and specific — students need actionable information.
5. Do not speculate or generalize beyond what the reviews explicitly say."""


def build_prompt(question, retrieved_chunks):
    context_blocks = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        context_blocks.append(
            f"[Document {i} | Source: {chunk['source']}]\n{chunk['text']}"
        )
    context = "\n\n".join(context_blocks)
    return f"""Here are relevant excerpts from student reviews and posts about DePaul University:

{context}

---
Using ONLY the information above, answer this question:
{question}

Remember: cite the source document(s) in your answer. If the documents don't cover this topic, say so explicitly."""


def ask(question, k=5):
    chunks = retrieve(question, k=k)
    if not chunks:
        return {
            "answer": "I couldn't retrieve any relevant documents for that question.",
            "sources": [],
            "retrieved_chunks": []
        }
    prompt = build_prompt(question, chunks)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=600
    )
    answer = response.choices[0].message.content.strip()
    sources = list(dict.fromkeys(c["source"] for c in chunks))
    return {"answer": answer, "sources": sources, "retrieved_chunks": chunks}


def handle_query(question):
    if not question.strip():
        return "Please enter a question.", ""
    result = ask(question)
    sources_text = "\n".join(f"• {s}" for s in result["sources"])
    return result["answer"], sources_text


def ensure_vector_store():
    import os, json
    chk_file = os.path.join("chroma_store", "chunks.json")
    if not os.path.exists(chk_file):
        print("Vector store empty — building now...")
        chunks = ingest_all()
        embed_and_store(chunks)
    else:
        with open(chk_file) as f:
            existing = json.load(f)
        print(f"Vector store ready ({len(existing)} chunks loaded)")


# --- Gradio UI ---
with gr.Blocks(title="DePaul Unofficial Guide") as demo:
    gr.Markdown("""
# 🎓 DePaul University Unofficial Guide
**Ask questions about professors and courses — answers are grounded in real student reviews.**
    """)
    with gr.Row():
        with gr.Column(scale=3):
            question_box = gr.Textbox(
                label="Your question",
                placeholder='e.g. "Is Professor Brown a good math teacher?" or "How hard are Zimmerman\'s exams?"',
                lines=2
            )
            ask_btn = gr.Button("Ask", variant="primary")
    with gr.Row():
        with gr.Column(scale=3):
            answer_box = gr.Textbox(label="Answer", lines=10, interactive=False)
        with gr.Column(scale=1):
            sources_box = gr.Textbox(label="Retrieved from", lines=10, interactive=False)

    gr.Examples(
        examples=[
            ["What do students say about Professor Brown's exams?"],
            ["Is there a professor at DePaul who curves grades?"],
            ["What courses have a heavy workload?"],
            ["Which professor should I avoid and why?"],
        ],
        inputs=question_box
    )

    ask_btn.click(handle_query, inputs=question_box, outputs=[answer_box, sources_box])
    question_box.submit(handle_query, inputs=question_box, outputs=[answer_box, sources_box])


if __name__ == "__main__":
    ensure_vector_store()
    demo.launch()