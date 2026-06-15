from __future__ import annotations

from app.models.simulation import ResourceCatalogEntry

DEFAULT_ACTIVE_RESOURCE_IDS = [
    "doctor",
    "nurse",
    "observation_bed",
    "resuscitation_room",
    "vital_sign_monitor",
    "laboratory",
]

RESOURCE_CLINICAL_GUIDANCE: dict[str, str] = {
    "doctor": "general medical assessment and clinical decision-making",
    "nurse": "monitoring, medication support, bedside care, and procedural assistance",
    "observation_bed": "patient observation or non-critical monitored waiting",
    "resuscitation_room": "unstable or life-threatening emergency management",
    "vital_sign_monitor": "continuous or frequent vital-sign monitoring",
    "laboratory": "blood tests, infection markers, metabolic panels, and cardiac markers",
    "xray_room": "trauma, suspected fracture, chest imaging, or bone injury assessment",
    "ct_scanner": "neurological deficit, head trauma, stroke-like symptoms, or severe trauma imaging",
    "ultrasound_room": "abdominal pain, pregnancy-related concerns, or internal bleeding screening",
    "isolation_room": "suspected contagious infectious disease or respiratory infection requiring isolation",
    "pharmacy": "medication-related, toxicology, overdose, drug reconciliation, or urgent medication preparation",
    "specialist": "complex cases requiring specialist consultation or advanced clinical input",
}

DEFAULT_RESOURCE_PROMPT = """
You are a clinical enrichment engine for an educational emergency room simulator.
This output is for simulation and academic planning only.
Do not provide diagnosis, treatment instructions, or real-world clinical advice.
Extract only structured triage-planning variables for the simulator.
Required resources are simulation resources, not real clinical instructions.
Be conservative when symptoms suggest high acuity.
Always include doctor in required_resources.
The explanation field is mandatory and must be a short operational justification.
Base explanation only on complaint, free-text description, acuity clues, pain clues, and vital-sign clues if present.
Explanation must justify the assigned risk, category, deterioration, waiting time, service time, and resources.
Explanation must not be a diagnosis.
Explanation must not be treatment advice.
Explanation should be one or two sentences.
Return only a schema-conforming object.
""".strip()

CLINICAL_ENRICHMENT_JSON_TEMPLATE = """{
  "key_symptoms": ["symptom"],
  "textual_risk_score": 3,
  "clinical_category": "category",
  "deterioration_rate": 0.05,
  "max_wait_time": 30,
  "estimated_service_time": 45,
  "required_resources": ["doctor"],
  "explanation": "Short operational justification linked to risk, deterioration, waiting time, service time, and resources."
}""".strip()

USER_PROMPT_TEMPLATE = """
Chief complaint: {chief_complaint}
Clinical description: {clinical_description}

Extract the following simulation fields:
- key_symptoms
- textual_risk_score from 1 to 5
- clinical_category
- deterioration_rate
- max_wait_time
- estimated_service_time
- required_resources: array/list of active resource ids, never a single string
- explanation: non-empty short operational justification, not a diagnosis, not treatment advice
""".strip()

CLINICAL_RESOURCE_SELECTION_GUIDANCE = """
Clinical resource-selection guidance:
- Cardiac chest pain or unstable cardiac symptoms: doctor, nurse, vital_sign_monitor, resuscitation_room if high risk or unstable, laboratory if blood tests or cardiac markers are relevant.
- Respiratory distress, severe dyspnea, or hypoxia: doctor, nurse, vital_sign_monitor, resuscitation_room if severe or unstable, isolation_room if contagious respiratory infection is suspected, xray_room if chest imaging is clinically relevant.
- Trauma, fall, or suspected fracture: doctor, nurse, vital_sign_monitor if moderate or high risk, xray_room if fracture or chest or bone injury is suspected, ct_scanner if head trauma or neurological signs or severe trauma are present, resuscitation_room if unstable.
- Neurological symptoms, stroke-like symptoms, seizure, or altered mental status: doctor, nurse, vital_sign_monitor, ct_scanner if enabled, resuscitation_room if unstable or high risk, specialist if complex neurological assessment is needed.
- Infectious symptoms or fever with respiratory or systemic symptoms: doctor, nurse, vital_sign_monitor if moderate or high risk, laboratory if infection markers are relevant, isolation_room if contagious infection is suspected.
- Abdominal pain, pregnancy-related concerns, or suspected internal bleeding: doctor, nurse, laboratory if blood tests are relevant, ultrasound_room if abdominal or pregnancy or internal bleeding screening is relevant, ct_scanner if severe abdominal trauma or complex high-risk presentation is present.
- Medication issue, overdose, toxicology, or drug reaction: doctor, nurse, vital_sign_monitor if moderate or high risk, pharmacy if enabled, laboratory if toxicology or metabolic tests are relevant, resuscitation_room if unstable.
- Complex high-risk cases: specialist if enabled and specialty input is clinically relevant.
""".strip()


def _resource_entry_to_dict(resource: ResourceCatalogEntry | dict[str, object]) -> dict[str, object]:
    if isinstance(resource, ResourceCatalogEntry):
        return resource.model_dump(mode="json")
    return dict(resource)


def normalize_active_resource_catalog(
    active_resource_catalog: dict[str, ResourceCatalogEntry | dict[str, object]] | None = None,
    *,
    allowed_resources: list[str] | None = None,
) -> list[dict[str, object]]:
    normalized_catalog: list[dict[str, object]] = []
    if active_resource_catalog:
        for resource_id, resource in active_resource_catalog.items():
            entry = _resource_entry_to_dict(resource)
            enabled = bool(entry.get("enabled", True))
            capacity = int(entry.get("capacity", 0) or 0)
            if not enabled:
                continue
            normalized_catalog.append(
                {
                    "id": str(entry.get("id", resource_id)).strip().lower(),
                    "capacity": capacity,
                    "enabled": True,
                    "label": str(entry.get("id", resource_id)).strip().replace("_", " "),
                    "meaning": RESOURCE_CLINICAL_GUIDANCE.get(
                        str(entry.get("id", resource_id)).strip().lower(),
                        "specialized simulation resource relevant only when clinically justified",
                    ),
                    "availability_note": "currently unavailable / zero capacity" if capacity == 0 else "available",
                }
            )
    else:
        for resource_id in allowed_resources or DEFAULT_ACTIVE_RESOURCE_IDS:
            normalized_catalog.append(
                {
                    "id": resource_id.strip().lower(),
                    "capacity": "unknown",
                    "enabled": True,
                    "label": resource_id.strip().replace("_", " "),
                    "meaning": RESOURCE_CLINICAL_GUIDANCE.get(
                        resource_id.strip().lower(),
                        "specialized simulation resource relevant only when clinically justified",
                    ),
                    "availability_note": "availability unknown",
                }
            )

    deduped: list[dict[str, object]] = []
    seen: set[str] = set()
    for entry in normalized_catalog:
        resource_id = str(entry["id"])
        if resource_id in seen:
            continue
        seen.add(resource_id)
        deduped.append(entry)
    return deduped


def extract_active_resource_ids(
    active_resource_catalog: dict[str, ResourceCatalogEntry | dict[str, object]] | None = None,
    *,
    allowed_resources: list[str] | None = None,
) -> list[str]:
    return [str(entry["id"]) for entry in normalize_active_resource_catalog(active_resource_catalog, allowed_resources=allowed_resources)]


def build_system_prompt(
    allowed_resources: list[str] | None = None,
    *,
    active_resource_catalog: dict[str, ResourceCatalogEntry | dict[str, object]] | None = None,
) -> str:
    catalog_entries = normalize_active_resource_catalog(
        active_resource_catalog,
        allowed_resources=allowed_resources,
    )
    resource_block = "\n".join(
        f"- {entry['id']}: enabled={entry['enabled']}, capacity={entry['capacity']}, use={entry['meaning']}, note={entry['availability_note']}"
        for entry in catalog_entries
    )
    active_ids = ", ".join(entry["id"] for entry in catalog_entries)
    return (
        f"{DEFAULT_RESOURCE_PROMPT}\n"
        "Available active resources:\n"
        f"{resource_block}\n\n"
        "Resource selection rules:\n"
        f"- You must choose required_resources only from these active resource ids: {active_ids}.\n"
        "- required_resources must be an array of resource ids.\n"
        "- Always include doctor.\n"
        "- Include nurse when bedside care, monitoring, medication, or assistance is required.\n"
        "- Include optional resources when clinically relevant.\n"
        "- Do not invent resource ids.\n"
        "- Do not include disabled resources.\n"
        "- Enabled resources with capacity 0 are clinically valid but currently unavailable; include them when they are truly needed, because they may represent a bottleneck.\n"
        "- Do not include resources as decoration; include them only if they are needed to start or safely manage the case.\n"
        "- If a clinically ideal resource is not available in the active catalog, use the closest active resource and explain the limitation briefly.\n\n"
        f"{CLINICAL_RESOURCE_SELECTION_GUIDANCE}"
    )


def build_user_prompt(
    chief_complaint: str,
    clinical_description: str,
    *,
    allowed_resources: list[str] | None = None,
    active_resource_catalog: dict[str, ResourceCatalogEntry | dict[str, object]] | None = None,
) -> str:
    catalog_entries = normalize_active_resource_catalog(
        active_resource_catalog,
        allowed_resources=allowed_resources,
    )
    resource_hint = ", ".join(entry["id"] for entry in catalog_entries)
    return USER_PROMPT_TEMPLATE.format(
        chief_complaint=chief_complaint.strip(),
        clinical_description=(
            f"{clinical_description.strip()}\n"
            f"Active resource ids for this run: {resource_hint}"
        ),
    )


def build_structured_output_retry_prompt(
    previous_payload: dict,
    *,
    allowed_resources: list[str] | None = None,
    active_resource_catalog: dict[str, ResourceCatalogEntry | dict[str, object]] | None = None,
    validation_error: str | None = None,
    missing_fields: list[str] | None = None,
) -> str:
    catalog_entries = normalize_active_resource_catalog(
        active_resource_catalog,
        allowed_resources=allowed_resources,
    )
    resource_block = "\n".join(
        f"- {entry['id']}: enabled={entry['enabled']}, capacity={entry['capacity']}, use={entry['meaning']}, note={entry['availability_note']}"
        for entry in catalog_entries
    )
    supported_resources = ", ".join(entry["id"] for entry in catalog_entries)
    missing_fields_block = ""
    if missing_fields:
        missing_fields_block = f"Missing or invalid fields: {', '.join(missing_fields)}.\n"
    validation_error_block = ""
    if validation_error:
        validation_error_block = f"Validation error: {validation_error}\n"
    return (
        "Your previous response did not match the required schema.\n"
        f"{validation_error_block}"
        f"{missing_fields_block}"
        "Return the full JSON object again.\n"
        "Return valid JSON only.\n"
        "Do not use markdown.\n"
        "Keep all prior fields unless a correction is required for schema validity.\n"
        "Your output must contain exactly this object shape and must not omit any key.\n"
        "required_resources must be an array of resource ids, never a single string.\n"
        f"Use only these active resource ids: {supported_resources}.\n"
        "Always include doctor.\n"
        "If optional active resources are clinically relevant, include them.\n"
        "Do not invent or reuse disabled resources.\n"
        "Enabled resources with capacity 0 remain valid choices when clinically necessary and may indicate blocking.\n"
        "The explanation field must be a non-empty operational justification based only on complaint, description, acuity, pain, and vital-sign clues.\n"
        "If you return only required_resources and explanation, the output is invalid.\n"
        "Do not provide diagnosis or treatment advice.\n"
        "Required JSON template:\n"
        f"{CLINICAL_ENRICHMENT_JSON_TEMPLATE}\n"
        "Active resource catalog:\n"
        f"{resource_block}\n"
        "No markdown.\n"
        f"Previous JSON: {previous_payload}"
    )


SYSTEM_PROMPT = build_system_prompt()
