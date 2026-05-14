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
    validate_schema_self_contained,
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

    def test_prompt_description_shows_nested_experience_fields(self):
        """Prompt hint must expose TailoredExperience and TailoredBullet fields
        so the LLM knows the structure the FSM will enforce."""
        result = get_json_schema_for_prompt()
        assert "title" in result
        assert "company" in result
        assert "bullets" in result
        assert "original" in result
        assert "tailored" in result


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

    def test_schema_self_contained_in_request(self):
        """The guided_json schema must have no dangling $refs."""
        kwargs = {"model": "test", "messages": []}
        result = apply_outlines_constraint_to_request(kwargs)
        schema = result["extra_body"]["guided_json"]
        # Should not raise — all $refs must resolve within $defs
        validate_schema_self_contained(schema)


class TestSchemaValidity:
    """Structural validation of the RewriteOutput JSON schema.

    These tests prove that the schema passed to the Outlines FSM is
    well-formed and self-contained — a prerequisite for the FSM to compile
    and for malformed JSON to be truly impossible.
    """

    def test_schema_passes_jsonschema_draft7_validation(self):
        """The schema must be a valid JSON Schema (Draft 7)."""
        import jsonschema
        schema = RewriteOutput.model_json_schema()
        # check_schema raises SchemaError if the schema itself is invalid
        jsonschema.Draft7Validator.check_schema(schema)

    def test_all_refs_resolve_within_defs(self):
        """Every $ref in the schema resolves to an entry in $defs."""
        schema = RewriteOutput.model_json_schema()
        defs = schema.get("$defs", {})

        def _collect_refs(node, refs=None):
            if refs is None:
                refs = []
            if isinstance(node, dict):
                if "$ref" in node:
                    refs.append(node["$ref"])
                for v in node.values():
                    _collect_refs(v, refs)
            elif isinstance(node, list):
                for item in node:
                    _collect_refs(item, refs)
            return refs

        refs = _collect_refs(schema)
        for ref in refs:
            assert ref.startswith("#/$defs/"), f"Non-local $ref found: {ref}"
            name = ref[len("#/$defs/"):]
            assert name in defs, f"$ref '{ref}' has no matching $defs entry"

    def test_schema_is_self_contained(self):
        """validate_schema_self_contained must not raise for RewriteOutput."""
        schema = RewriteOutput.model_json_schema()
        # Should not raise
        validate_schema_self_contained(schema)

    def test_valid_rewrite_output_validates_against_schema(self):
        """A known-good RewriteOutput instance must validate against the schema."""
        import jsonschema
        from services.rewrite.schema import TailoredExperience, TailoredBullet

        schema = RewriteOutput.model_json_schema()
        instance = RewriteOutput(
            tailored_summary="Senior security engineer summary",
            experience=[
                TailoredExperience(
                    title="Security Analyst",
                    company="Corp",
                    bullets=[
                        TailoredBullet(
                            original="Managed Splunk",
                            tailored="Architected Splunk SIEM",
                            rationale="Added architecture scope",
                        )
                    ],
                )
            ],
            skills_highlighted=["SIEM", "Splunk"],
            certifications_emphasized=["CISSP"],
            overall_rationale="Strong alignment",
        )
        # jsonschema requires a resolver to follow $refs within the same document
        resolver = jsonschema.RefResolver.from_schema(schema)
        jsonschema.validate(
            instance=json.loads(instance.model_dump_json()),
            schema=schema,
            resolver=resolver,
        )

    def test_invalid_structure_fails_schema_validation(self):
        """A payload with missing required fields must fail schema validation."""
        import jsonschema

        schema = RewriteOutput.model_json_schema()
        # experience items require 'title', 'company', 'bullets' — omit 'title'
        bad_instance = {
            "tailored_summary": "ok",
            "experience": [
                {"company": "Corp", "bullets": []}  # missing 'title'
            ],
            "skills_highlighted": [],
            "certifications_emphasized": [],
            "overall_rationale": "test",
        }
        resolver = jsonschema.RefResolver.from_schema(schema)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                instance=bad_instance,
                schema=schema,
                resolver=resolver,
            )

    def test_dangling_ref_raises_value_error(self):
        """validate_schema_self_contained raises ValueError for a dangling $ref."""
        broken_schema = {
            "type": "object",
            "properties": {
                "foo": {"$ref": "#/$defs/NonExistent"}
            },
            "$defs": {},
        }
        with pytest.raises(ValueError, match="NonExistent"):
            validate_schema_self_contained(broken_schema)

    def test_non_local_ref_raises_value_error(self):
        """validate_schema_self_contained raises ValueError for an external $ref."""
        broken_schema = {
            "type": "object",
            "properties": {
                "foo": {"$ref": "https://example.com/schema#/definitions/Foo"}
            },
        }
        with pytest.raises(ValueError, match="not a local"):
            validate_schema_self_contained(broken_schema)
