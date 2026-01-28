"""
Simple NER module using HuggingFace Inference API
Model: dslim/bert-base-NER

Takes custom prompt and response text
Performs Named Entity Recognition (NER)
"""

import os
import requests
from typing import List, Dict
from dotenv import load_dotenv

# =========================
# Load Environment Variables
# =========================

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise EnvironmentError(
        "HF_TOKEN not found. Set it using export HF_TOKEN=your_token"
    )

# =========================
# HuggingFace Configuration
# =========================

HF_API_URL = "https://router.huggingface.co/hf-inference/models/dslim/bert-base-NER"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json",
}

# =========================
# NER Function
# =========================


def perform_ner(text: str) -> List[Dict]:
    """
    Perform Named Entity Recognition on input text.
    """

    if not text or len(text.strip()) < 3:
        return []

    payload = {"inputs": text[:512]}  # HF inference safety limit

    response = requests.post(HF_API_URL, headers=HEADERS, json=payload, timeout=10)

    if response.status_code != 200:
        raise RuntimeError(f"HF API Error {response.status_code}: {response.text}")
    print("\n\nResponse from llm: ", response)
    entities = response.json()
    print("\n\nEntities from llm: ", entities)
    results = []

    for entity in entities:
        results.append(
            {
                "entity": entity.get("entity_group"),
                "value": entity.get("word"),
                "confidence": round(entity.get("score", 0), 4),
            }
        )

    return results


# =========================
# Prompt + Response Scanner
# =========================


def ner_on_prompt_and_response(prompt: str, response: str) -> Dict:
    """
    Perform NER separately on prompt and response.
    """

    return {"prompt_ner": perform_ner(prompt), "response_ner": perform_ner(response)}


# =========================
# Example Usage
# =========================

if __name__ == "__main__":

    prompt = "Hello, my name is John Smith and I live in New York. My email is john.smith@example.com and my phone number is 555-123-4567."
    response = "name is ashutos, reach me on 911234567890, i can be found at lucknow, up. my credit card number is 12234245245435"

    ner_result = ner_on_prompt_and_response(prompt, response)

    print("\n====== NER RESULTS ======")
    print("\nPrompt Entities:")
    for item in ner_result["prompt_ner"]:
        print(item)

    print("\nResponse Entities:")
    for item in ner_result["response_ner"]:
        print(item)
