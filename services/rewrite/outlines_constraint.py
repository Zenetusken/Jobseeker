"""
Outlines Constraint — Pre-generation JSON schema enforcement.
Compiles a Pydantic model into a regex FSM that gates vLLM token generation,
making malformed JSON mathematically impossible.
"""
from typing import Type
from pydantic import BaseModel
from loguru import logger

from services.rewrite.schema import RewriteOutput


def validate_schema_self_contained(schema: dict) -> None:
    """
    Verify that every JSON Schema $ref inside `schema` resolves to a key in
    schema["$defs"]. Raises ValueError if any reference is dangling.

    This is a pre-flight guard: if this raises, the Outlines FSM cannot compile
    and guided decoding would silently fall back to free-form generation.
    """
    defs = schema.get("$defs", {})

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if ref is not None:
                # Only handle local JSON-pointer refs of the form #/$defs/<name>
                if ref.startswith("#/$defs/"):
                    def_name = ref[len("#/$defs/"):]
                    if def_name not in defs:
                        raise ValueError(
                            f"JSON Schema $ref '{ref}' has no matching entry in "
                            f"$defs. Available: {list(defs.keys())}"
                        )
                else:
                    raise ValueError(
                        f"JSON Schema $ref '{ref}' is not a local #/$defs/ "
                        "reference and cannot be resolved at runtime."
                    )
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(schema)


def build_json_schema_description(model: Type[BaseModel]) -> str:
    """
    Build a JSON schema description string for the prompt.
    This tells the LLM exactly what structure to produce.
    Outlines will additionally enforce this at the token level.

    Resolves $ref items against $defs so the nested structure is visible to
    the LLM (not just to the FSM).
    """
    schema = model.model_json_schema()
    defs = schema.get("$defs", {})
    properties = schema.get("properties", {})

    def _describe_ref(ref: str) -> str:
        """Return a compact inline description of a $ref target."""
        if not ref.startswith("#/$defs/"):
            return "{}"
        def_name = ref[len("#/$defs/"):]
        def_schema = defs.get(def_name, {})
        def_props = def_schema.get("properties", {})
        required = def_schema.get("required", [])
        parts = []
        for pname, pinfo in def_props.items():
            ptype = pinfo.get("type", "string")
            req_marker = "" if pname in required else "?"
            if ptype == "array":
                sub_items = pinfo.get("items", {})
                if "$ref" in sub_items:
                    sub_desc = _describe_ref(sub_items["$ref"])
                    parts.append(f'"{pname}"{req_marker}: [{sub_desc}, ...]')
                else:
                    parts.append(f'"{pname}"{req_marker}: ["string", ...]')
            else:
                parts.append(f'"{pname}"{req_marker}: "{ptype}"')
        return "{" + ", ".join(parts) + "}"

    lines = ["{"]
    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get("type", "string")
        if prop_type == "array":
            items = prop_info.get("items", {})
            if "$ref" in items:
                inline = _describe_ref(items["$ref"])
                lines.append(f'  "{prop_name}": [{inline}, ...],')
            else:
                lines.append(f'  "{prop_name}": ["string", ...],')
        elif prop_type == "object":
            lines.append(f'  "{prop_name}": {{ /* nested object */ }},')
        else:
            lines.append(f'  "{prop_name}": "{prop_type}",')
    lines.append("}")

    return "\n".join(lines)


def get_json_schema_for_prompt() -> str:
    """Get the JSON schema description to include in the LLM prompt."""
    return build_json_schema_description(RewriteOutput)


def apply_outlines_constraint_to_request(request_kwargs: dict) -> dict:
    """
    Add Outlines JSON constraint to the vLLM API request.
    Uses OpenAI's `guided_json` (supported by vLLM) for pre-generation
    schema enforcement.

    Validates that the schema is self-contained before attaching it so a
    broken schema never reaches vLLM silently.
    """
    json_schema = RewriteOutput.model_json_schema()

    # Pre-flight: raise immediately if $refs are dangling — a broken schema
    # would cause Outlines to silently skip guided decoding.
    validate_schema_self_contained(json_schema)

    # vLLM supports guided_json via its OpenAI-compatible endpoint
    request_kwargs["extra_body"] = {
        "guided_json": json_schema,
        "guided_decoding_backend": "outlines",
    }

    return request_kwargs
