# ===============================
# Step 0 — Setup
# ===============================

import asyncio
import json
import os

from dotenv import load_dotenv
from pageindex import PageIndexClient
import pageindex.utils as utils
from openai import AsyncOpenAI

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("pageindex_api_key")

pi_client = PageIndexClient(api_key=PAGEINDEX_API_KEY)

# Ollama client
client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)


# ===============================
# LLM function
# ===============================

async def call_llm(prompt, model="llama3:latest", temperature=0):

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=200
    )

    return response.choices[0].message.content.strip()


# ===============================
# Main pipeline
# ===============================

async def main():

    # ---------------------------
    # Step 1 — Load PDF
    # ---------------------------

    pdf_path = "/Users/abhisheksingh/Desktop/vector_less_RAG/data/entropy-22-00193.pdf"

    # doc_id = pi_client.submit_document(pdf_path)["doc_id"]


    doc_id = "pi-cmn8hr1r0007z0bphbw0fvjj1"
    print("Document submitted:", doc_id)


    # ---------------------------
    # Step 2 — Wait until ready
    # ---------------------------

    if not pi_client.is_retrieval_ready(doc_id):

        print("Document still processing. Run again shortly.")
        return

    tree = pi_client.get_tree(
        doc_id,
        node_summary=True
    )["result"]

    print("\nDocument Structure:\n")

    utils.print_tree(tree)


    # ---------------------------
    # Step 3 — Tree search
    # ---------------------------

    query = "What are the conclusions in this document?"

    tree_without_text = utils.remove_fields(
        tree.copy(),
        fields=["text"]
    )

    TREE_CHAR_LIMIT = 6000

    tree_json_str = json.dumps(
        tree_without_text,
        indent=2
    )[:TREE_CHAR_LIMIT]


    search_prompt = f"""
    Return ONLY valid JSON.

    Select up to 3 nodes that likely contain the answer.

    Question:
    {query}

    Tree:
    {tree_json_str}

    Output format:
    {{
    "node_list": ["id1","id2","id3"]
    }}

    Return JSON only.
    Do not include explanation.
    """


    print("\nSearching nodes...\n")
    tree_search_result = await call_llm(search_prompt)

    print("\nRaw LLM output:\n")
    print(tree_search_result)


    def extract_json(text):

        import re

        # try to extract JSON block
        match = re.search(r'\{.*\}', text, re.DOTALL)

        if match:
            json_str = match.group()
            return json.loads(json_str)

        return None


    tree_search_result_json = extract_json(tree_search_result)

    if not tree_search_result_json:

        print("\n⚠ LLM did not return valid JSON. Using fallback retrieval.\n")

        # fallback: just pick first 3 nodes
        node_list = [
            child["node_id"]
            for child in tree["children"][:3]
        ]

    else:

        node_list = tree_search_result_json.get("node_list", [])[:3]


    # ---------------------------
    # Step 4 — Extract context
    # ---------------------------

    node_map = utils.create_node_mapping(tree)

    MAX_NODES = 3
    MAX_CONTEXT_CHARS = 3500

    node_list = node_list[:MAX_NODES]

    relevant_content = "\n\n".join(

        node_map[node_id]["text"]

        for node_id in node_list

    )

    relevant_content = relevant_content[:MAX_CONTEXT_CHARS]


    print("\nRetrieved Nodes:\n")

    for node_id in node_list:

        node = node_map[node_id]

        print(
            f"Node ID: {node['node_id']} | "
            f"Page: {node['page_index']} | "
            f"Title: {node['title']}"
        )


    print("\nContext Preview:\n")

    utils.print_wrapped(
        relevant_content[:800] + "..."
    )


    # ---------------------------
    # Step 5 — Generate answer
    # ---------------------------

    answer_prompt = f"""
Answer using ONLY the context.

Question:
{query}

Context:
{relevant_content}

Provide concise answer.
"""


    print("\nGenerating answer...\n")

    answer = await call_llm(answer_prompt)

    utils.print_wrapped(answer)


    # debug info

    print("\nDebug:")
    print("nodes used:", len(node_list))
    print("context length:", len(relevant_content))


# ===============================
# run
# ===============================

asyncio.run(main())