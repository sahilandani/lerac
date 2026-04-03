import os
from groq import Groq


# -------------------------------
# Safe client initializer
# -------------------------------
def get_client():
    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY not set in environment variables")

    return Groq(api_key=api_key)


# -------------------------------
# Intent classification
# -------------------------------
def classify_intent(query):
    q = query.lower()

    if any(word in q for word in ["price", "cost", "charge", "fee"]):
        return "Pricing"
    elif any(word in q for word in ["policy", "rule", "refund"]):
        return "Policy"
    elif any(word in q for word in ["email", "message", "conversation"]):
        return "Communication"
    else:
        return "General"


# -------------------------------
# Find supporting snippets
# -------------------------------
def find_supporting_snippets(chunks):
    snippets = []

    for c in chunks:
        snippets.append(
            f"[{c.get('source_name', 'unknown')}] {c.get('content', '')[:200]}"
        )

    return "\n".join(snippets)


# -------------------------------
# Main reasoning function
# -------------------------------
def resolve_conflicts_and_reason(chunks, query):
    try:
        client = get_client()
    except Exception as e:
        return f"❌ Error: {str(e)}"

    context = "\n\n".join(
        f"Source: {c.get('source_name')}\nContent: {c.get('content')}"
        for c in chunks
    )

    prompt = f"""
You are an intelligent assistant.

Answer the question based ONLY on the provided sources.
If there are conflicting answers, analyze and resolve them logically.

Question:
{query}

Sources:
{context}

Give a clear final answer.
"""

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"❌ LLM Error: {str(e)}"