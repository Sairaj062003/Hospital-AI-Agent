"""PII detection, redaction, and contact extraction for intake messages."""

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

from src.state.models import AgentState, PatientContact

# Built once and reused - constructing an AnalyzerEngine is expensive.
_analyzer = None

# DATE_TIME is deliberately excluded - phrases like "this morning" are
# clinically relevant, not PII, and we don't need date-of-birth extraction
# for this assignment. Everything else the analyzer supports stays allowed.
_EXCLUDED_ENTITIES = {"DATE_TIME"}


def get_analyzer() -> AnalyzerEngine:
    global _analyzer
    if _analyzer is None:
        _analyzer = AnalyzerEngine()
    return _analyzer


def detect_pii(raw_message: str) -> list:
    analyzer = get_analyzer()
    entities_to_detect = [
        entity for entity in analyzer.get_supported_entities() if entity not in _EXCLUDED_ENTITIES
    ]
    return analyzer.analyze(text=raw_message, language="en", entities=entities_to_detect)


def redact_message(raw_message: str, entities: list) -> str:
    anonymizer = AnonymizerEngine()
    result = anonymizer.anonymize(text=raw_message, analyzer_results=entities)
    return result.text


def extract_contact(raw_message: str, entities: list) -> PatientContact:
    full_name = None
    phone_number = None

    for entity in entities:
        value = raw_message[entity.start : entity.end]

        if entity.entity_type == "PERSON" and full_name is None:
            full_name = value
        elif entity.entity_type == "PHONE_NUMBER" and phone_number is None:
            phone_number = value

    return PatientContact(full_name=full_name, phone_number=phone_number)


def run_pii_redaction(state: AgentState) -> dict:
    raw_message = state.raw_message
    entities = detect_pii(raw_message)

    contact = extract_contact(raw_message, entities)
    redacted_raw_message = redact_message(raw_message, entities)

    return {"contact": contact, "redacted_raw_message": redacted_raw_message}
