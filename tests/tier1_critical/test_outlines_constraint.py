"""
Tier 1 — Critical pure-logic tests for outlines_constraint.py.
Tests JSON schema building and request constraint application.
"""
import json
import pytest
from pydantic import BaseModel
from services.rewrite.outlines_constraint import (
    build_json_schema_description,
    get_json_schema_for_prompt,
    apply_outlines_constraint_to_request,
)
from services.rewrite.schema import RewriteOutput


class TestBuildJsonSchemaDescription:
    def test_returns_non_empty_string(self):
        result = build_json_schema_description(RewriteOutput)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_all_top_level_keys(self):
        result = build_json_schema_description(RewriteOutput)
        assert "tailored_summary" in result
        assert "experience" in result
        assert "skills_highlighted" in result
        assert "certifications_emphasized" in result
        assert "overall_rationale" in result

    def test_starts_with_brace(self):
        result = build_json_schema_description(RewriteOutput)
        assert result.strip().startswith("{")

    def test_ends_with_brace(self):
        result = build_json_schema_description(RewriteOutput)
        assert result.strip().endswith("}")

    def test_array_fields_have_array_hint(self):
        result = build_json_schema_description(RewriteOutput)
        assert "array" in result.lower() or "[" in result

    def test_simple_model(self):
        class SimpleModel(BaseModel):
            name: str
            age: int

        result = build_json_schema_description(SimpleModel)
        assert "name" in result
        assert "age" in result


class TestGetJsonSchemaForPrompt:
    def test_returns_string(self):
        result = get_json_schema_for_prompt()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_expected_keys(self):
        result = get_json_schema_for_prompt()
        # Should describe the RewriteOutput schema
        assert "tailored_summary" in result or "experience" in result


class TestApplyOutlinesConstraintToRequest:
    def test_adds_extra_body(self):
        kwargs = {"model": "test", "messages": []}
        result = apply_outlines_constraint_to_request(kwargs)
        assert "extra_body" in result

    def test_extra_body_has_guided_json(self):
        kwargs = {"model": "test", "messages": []}
        result = apply_outlines_constraint_to_request(kwargs)
        assert "guided_json" in result["extra_body"]

    def test_extra_body_has_outlines_backend(self):
        kwargs = {"model": "test", "messages": []}
        result = apply_outlines_constraint_to_request(kwargs)
        assert result["extra_body"]["guided_decoding_backend"] == "outlines"

    def test_guided_json_is_valid_schema(self):
        kwargs = {"model": "test", "messages": []}
        result = apply_outlines_constraint_to_request(kwargs)
        schema = result["extra_body"]["guided_json"]
        # Should be a valid JSON schema dict
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert schema.get("type") == "object" or "type" in schema

    def test_preserves_existing_kwargs(self):
        kwargs = {"model": "test-model", "messages": [{"role": "user", "content": "hi"}], "temperature": 0.0}
        result = apply_outlines_constraint_to_request(kwargs)
        assert result["model"] == "test-model"
        assert result["temperature"] == 0.0
        assert len(result["messages"]) == 1

    def test_rewrite_output_schema_is_valid(self):
        """Verify RewriteOutput produces a valid JSON schema."""
        schema = RewriteOutput.model_json_schema()
        assert schema["type"] == "object"
        assert "tailored_summary" in schema["properties"]
        assert "experience" in schema["properties"]
        assert "skills_highlighted" in schema["properties"]
        assert "certifications_emphasized" in schema["properties"]
        assert "overall_rationale" in schema["properties"]
