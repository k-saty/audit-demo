"""
PII Detection module using HuggingFace Router Inference API.
Model: dslim/bert-base-NER
Requires HF_TOKEN environment variable.
"""

import os
import re
import requests
from typing import List, Dict, Any


from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ==============================
# HuggingFace API Configuration
# ==============================

HF_API_TOKEN = os.getenv("HF_TOKEN")


HF_API_URL = "https://router.huggingface.co/hf-inference/models/dslim/bert-base-NER"

HEADERS = {
    "Authorization": f"Bearer {HF_API_TOKEN}",
    "Content-Type": "application/json",
}

if not HF_API_TOKEN:
    print("⚠️  Warning: HF_TOKEN environment variable not set.")
    print("   PII detection via NER will be disabled.")


# ==============================
# Risk Classification
# ==============================

PII_RISK_LEVELS = {
    "high": [
        "email",
        "phone",
        "ssn",
        "credit_card",
        "PERSON",
        "PER",
        "B-PER",
        "I-PER",
    ],
    "medium": [
        "ipv4",
        "DATE",
        "ORG",
        "B-ORG",
        "I-ORG",
        "B-LOC",
        "I-LOC",
        "LOCATION",
        "LOC",
        "GPE",
        "B-GPE",
        "I-GPE",
    ],
    "low": ["MISC", "B-MISC", "I-MISC", "OTHER"],
}


def get_risk_level(pii_type: str) -> str:
    """Map PII type to risk level."""
    for level, types in PII_RISK_LEVELS.items():
        if pii_type in types:
            return level
    return "low"


# ==============================
# HuggingFace NER Call
# ==============================


def query_hf_ner(text: str) -> tuple:
    """
    Call HuggingFace Router Inference API for Named Entity Recognition.
    Returns (findings, raw_response) tuple
    """
    if not HF_API_TOKEN or not text or len(text) < 5:
        return [], None

    payload = {"inputs": text[:512]}  # Hard limit for inference safety

    try:
        response = requests.post(
            HF_API_URL,
            headers=HEADERS,
            json=payload,
            timeout=10,
        )

        print("\n\nResponse from llm: ", response)

        if response.status_code != 200:
            print(f"HF API Error {response.status_code}: {response.text}")
            return [], None

        entities = response.json()

        print("\n\nEntities from llm: ", entities)

        if not isinstance(entities, list):
            return [], entities  # Return raw response even if not a list

        findings = []

        # IMPORTANT: Include ALL entity types from NER model, not just whitelist
        # This ensures consistency between raw NER response and detected items
        # Risk classification still applies to all entity types
        for entity in entities:
            entity_type = entity.get("entity_group", "").upper()
            entity_score = entity.get("score", 0.0)

            # Skip very low confidence predictions (< 0.7) to avoid false positives
            if entity_score < 0.7:
                continue

            findings.append(
                {
                    "type": entity_type,
                    "value": entity.get("word", ""),
                    "score": entity_score,
                    "risk_level": get_risk_level(entity_type),
                }
            )

        return findings, entities

    except requests.exceptions.Timeout:
        print("HF API timeout")
        return [], None
    except Exception as e:
        print(f"NER API error: {e}")
        return [], None


# ==============================
# Regex-Based PII Detection
# ==============================

PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "phone": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "ssn": r"\b(?!000)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "ipv4": r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
}


def detect_pii_regex(text: str) -> List[Dict[str, Any]]:
    """Detect PII using regex rules."""
    findings = []

    for pattern_name, pattern in PATTERNS.items():
        for match in re.finditer(pattern, text):
            findings.append(
                {
                    "type": pattern_name,
                    "value": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "risk_level": get_risk_level(pattern_name),
                }
            )

    return findings


# ==============================
# Unified PII Inspection
# ==============================


def inspect_text_for_pii(text: str) -> tuple:
    """
    Detect PII using both regex and NER.
    Returns (findings, ner_response) tuple
    """
    if not text or len(text) < 3:
        return [], None

    findings = []

    findings.extend(detect_pii_regex(text))
    ner_findings, ner_response = query_hf_ner(text)
    findings.extend(ner_findings)

    print(f"\n>>> inspect_text_for_pii DEBUG:")
    print(f"    Regex findings: {[f for f in findings if f.get('type') not in ['PERSON', 'PER', 'LOC', 'ORG', 'DATE', 'MISC', 'GPE']]}")
    print(f"    NER findings: {ner_findings}")
    print(f"    Total before dedup: {len(findings)}")

    # Deduplicate findings
    unique = {}
    for item in findings:
        key = (item["type"], item["value"].lower())
        if key not in unique:
            unique[key] = item

    print(f"    Total after dedup: {len(unique)}")
    print(f"    Unique items: {list(unique.keys())}")

    # Sort by risk level
    sorted_findings = sorted(
        unique.values(),
        key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(
            x.get("risk_level", "low"), 3
        ),
    )

    print(f"    Final sorted findings: {sorted_findings}\n")

    return sorted_findings, ner_response


# ==============================
# Audit Log Scanner
# ==============================


def scan_audit_log_for_pii(prompt: str, response: str) -> Dict[str, Any]:
    """
    Scan prompt and response text for PII.
    """
    prompt_pii, prompt_ner_response = inspect_text_for_pii(prompt)
    response_pii, response_ner_response = inspect_text_for_pii(response)

    all_pii = []

    for item in prompt_pii:
        item["field"] = "prompt"
        all_pii.append(item)

    for item in response_pii:
        item["field"] = "response"
        all_pii.append(item)

    high_risk = [p for p in all_pii if p["risk_level"] == "high"]

    # DEBUG: Log what we found
    print(f"\n=== PII SCAN RESULTS ===")
    print(f"Total PII found: {len(all_pii)}")
    print(f"All PII items: {all_pii}")
    print(f"High risk items: {len(high_risk)}")
    print("=======================\n")

    return {
        "total_pii_found": len(all_pii),
        "high_risk_count": len(high_risk),
        "has_high_risk": len(high_risk) > 0,
        "fields_scanned": ["prompt", "response"],
        "pii_list": all_pii,
        "ner_response_prompt": prompt_ner_response,
        "ner_response_response": response_ner_response,
    }
