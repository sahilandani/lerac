import os
from groq import Groq

# Initialize Groq client using environment variable
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# -------------------------------
# Resolve conflicts + generate answer
# -------------------------------
def resolve_conflicts_and_reason(chunks, query):
    if not chunks:
        return "No relevant data found."

    context = "\n\n".join([c["content"] for c in chunks])

    prompt = f"""
You are an AI assistant helping SMEs.

Rules:
- Use ONLY the provided context
- If multiple sources conflict, explain both clearly
- Do NOT hallucinate
- Be concise and structured

Context:
{context}

Question:
{query}
"""

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error generating answer: {str(e)}"


# -------------------------------
# Intent classification
# -------------------------------
def classify_intent(query):
    prompt = f"""
Classify the user query into ONE category:

Options:
- Pricing
- Policy
- Communication
- General

Return ONLY the category name.

Query: {query}
"""

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content.strip()

    except Exception:
        return "General"


# -------------------------------
# Supporting snippets finder
# -------------------------------
def find_supporting_snippets(chunks, query):
    if not chunks:
        return []

    context = "\n\n".join([c["content"] for c in chunks])

    prompt = f"""
From the context below, extract the most relevant supporting lines
that help answer the question.

Return 3–5 short bullet points.

Context:
{context}

Question:
{query}
"""

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        text = response.choices[0].message.content.strip()
        return text.split("\n")

    except Exception:
        return []