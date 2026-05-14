"""
Outlines Constraint — Pre-generation JSON schema enforcement.
Compiles a Pydantic model into a regex FSM that gates vLLM token generation,
making malformed JSON mathematically impossible.
"""
from typing import Type
from pydantic import BaseModel
from loguru import logger

from services.rewrite.schema import RewriteOutput


def build_json_schema_description(model: Type[BaseModel]) -> str:
    """
    Build a JSON schema description string for the prompt.
    This tells the LLM exactly what structure to produce.
    Outlines will additionally enforce this at the token level.
    """
    schema = model.model_json_schema()
    properties = schema.get("properties", {})

    lines = ["{"]
    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get("type", "string")
        if prop_type == "array":
            items = prop_info.get("items", {})
            if "$ref" in items:
                lines.append(f'  "{prop_name}": [/* array of objects */],')
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
    """
    json_schema = RewriteOutput.model_json_schema()
    
    # vLLM supports guided_json via its OpenAI-compatible endpoint
    request_kwargs["extra_body"] = {
        "guided_json": json_schema,
        "guided_decoding_backend": "outlines",
    }
    
    return request_kwargs
