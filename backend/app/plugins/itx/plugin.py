"""
IBM ITX Plugin — main plugin implementation.
Routes intents to specialized ITX sub-modules.
"""
from app.plugins.base import BasePlugin, PluginResponse
from app.core.ai_provider import get_ai_provider
from app.core.embeddings import get_embedding_provider
from app.core.vector_store import vector_store
from app.plugins.itx.prompts.function_prompts import (
    FUNCTION_EXPLAINER_SYSTEM, FUNCTION_EXPLAINER_USER,
    TYPE_TREE_SYSTEM, MAPPING_SYSTEM, DEBUG_SYSTEM,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ITXPlugin(BasePlugin):
    """IBM Sterling Transformation Extender (ITX) Plugin."""

    @property
    def name(self) -> str:
        return "itx"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "IBM Sterling Transformation Extender — AI-powered ITX engineering assistant"

    def get_capabilities(self) -> list[str]:
        return [
            "explain_function",
            "build_type_tree",
            "suggest_mapping",
            "generate_rule",
            "debug_trace",
            "generate_test_data",
            "compare_artifacts",
        ]

    def get_system_prompt(self) -> str:
        return (
            "You are an expert IBM ITX (Sterling Transformation Extender) engineer. "
            "Provide precise, technical, production-quality answers about ITX type trees, "
            "mapping rules, functions, cards, validation, launcher, trace analysis, and debugging."
        )

    async def process(self, intent: str, payload: dict) -> PluginResponse:
        """Route to the appropriate sub-module based on intent."""
        handlers = {
            "explain_function": self._explain_function,
            "build_type_tree": self._build_type_tree,
            "suggest_mapping": self._suggest_mapping,
            "generate_rule": self._generate_rule,
            "debug_trace": self._debug_trace,
            "generate_test_data": self._generate_test_data,
            "compare_artifacts": self._compare_artifacts,
        }

        handler = handlers.get(intent)
        if not handler:
            return PluginResponse(
                content=f"Unknown intent: {intent}",
                confidence=0.0,
            )

        return await handler(payload)

    async def _get_context(self, query: str, category: str = None, n_results: int = 5) -> str:
        """Retrieve relevant context from the knowledge base."""
        try:
            embedding_provider = get_embedding_provider()
            query_embedding = await embedding_provider.embed_text(query)
            where_filter = {"category": category} if category else None
            results = await vector_store.query(
                query_embedding=query_embedding,
                n_results=n_results,
                where=where_filter,
            )
            if results["documents"]:
                return "\n\n---\n\n".join(results["documents"])
        except Exception as e:
            logger.warning(f"Context retrieval failed: {e}")
        return "No specific documentation found in the knowledge base."

    async def _explain_function(self, payload: dict) -> PluginResponse:
        """Module 3: Explain an ITX function."""
        function_name = payload.get("function_name", payload.get("query", ""))
        context = await self._get_context(f"ITX function {function_name}", category="functions")

        ai = get_ai_provider()
        user_prompt = FUNCTION_EXPLAINER_USER.format(
            function_name=function_name, context=context
        )
        response = await ai.generate(
            system_prompt=FUNCTION_EXPLAINER_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.2,
        )

        return PluginResponse(content=response, confidence=0.8, metadata={"function": function_name})

    async def _build_type_tree(self, payload: dict) -> PluginResponse:
        """Module 4: Build type tree from sample data."""
        import re
        import json
        import uuid
        from app.models.artifact import Artifact

        sample_data = payload.get("sample_data", "")
        requirements = payload.get("requirements", "")
        db = payload.get("db")
        user_id = payload.get("user_id")

        context = await self._get_context("ITX type tree definition structure", category="type_tree")

        ai = get_ai_provider()
        user_prompt = f"""Analyze this sample data and generate an ITX type tree definition:

## Sample Data:
```
{sample_data}
```

## Requirements:
{requirements}

## Reference Documentation:
{context}

Generate a complete type tree with root type, groups, items, field definitions, delimiters, repetition rules, and validation suggestions. 
Always include a JSON representation of the tree inside a ```json ``` block, and a valid Type Tree Maker XML script (.mts) inside a ```xml ``` block."""

        response = await ai.generate(
            system_prompt=TYPE_TREE_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=3000,
        )

        def extract_code(content: str, lang: str) -> str:
            pattern = rf"```{lang}\s*([\s\S]*?)```"
            match = re.search(pattern, content, re.IGNORECASE)
            return match.group(1).strip() if match else ""

        json_str = extract_code(response, "json")
        xml_str = extract_code(response, "xml")

        json_schema = {}
        if json_str:
            try:
                json_schema = json.loads(json_str)
            except Exception as e:
                logger.warning(f"Failed to parse generated type tree JSON: {e}")

        artifact_id = None
        if xml_str and db and user_id:
            try:
                artifact = Artifact(
                    id=str(uuid.uuid4()),
                    name=f"type_tree_{uuid.uuid4().hex[:8]}.mts",
                    artifact_type="type_tree",
                    content=xml_str,
                    format="mts",
                    user_id=user_id
                )
                db.add(artifact)
                await db.flush()
                artifact_id = artifact.id
            except Exception as e:
                logger.error(f"Failed to save type tree artifact: {e}")

        metadata = {
            "type": "type_tree",
            "json_schema": json_schema,
            "artifact_id": artifact_id,
            "mts_script": xml_str
        }

        return PluginResponse(content=response, confidence=0.75, metadata=metadata)

    async def _suggest_mapping(self, payload: dict) -> PluginResponse:
        """Module 5: Suggest mapping logic."""
        import re
        import uuid
        from app.models.artifact import Artifact

        source = payload.get("source_data", "")
        target = payload.get("target_data", "")
        requirements = payload.get("requirements", "")
        db = payload.get("db")
        user_id = payload.get("user_id")

        context = await self._get_context("ITX mapping rules logic", category="mapping_rules")

        ai = get_ai_provider()
        user_prompt = f"""Generate ITX mapping logic for the following:

## Source Structure:
```
{source}
```

## Target Structure:
```
{target}
```

## Business Requirements:
{requirements}

## Reference Documentation:
{context}

Generate complete mapping suggestions including field mappings, loop logic, conditional rules (IF/CHOOSE), aggregation (SUM), lookups (LOOKUP), filtering, and transformation logic.
Always enclose the Map Source definition script (.mms) inside a ```mms ``` block."""

        response = await ai.generate(
            system_prompt=MAPPING_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=3000,
        )

        def extract_code(content: str, lang: str) -> str:
            pattern = rf"```{lang}\s*([\s\S]*?)```"
            match = re.search(pattern, content, re.IGNORECASE)
            return match.group(1).strip() if match else ""

        mms_script = extract_code(response, "mms")

        artifact_id = None
        if mms_script and db and user_id:
            try:
                artifact = Artifact(
                    id=str(uuid.uuid4()),
                    name=f"mapping_{uuid.uuid4().hex[:8]}.mms",
                    artifact_type="mapping_doc",
                    content=mms_script,
                    format="mms",
                    user_id=user_id
                )
                db.add(artifact)
                await db.flush()
                artifact_id = artifact.id
            except Exception as e:
                logger.error(f"Failed to save mapping artifact: {e}")

        metadata = {
            "type": "mapping",
            "artifact_id": artifact_id,
            "mms_script": mms_script
        }

        return PluginResponse(content=response, confidence=0.7, metadata=metadata)

    async def _generate_rule(self, payload: dict) -> PluginResponse:
        """Module 6: Generate ITX rule syntax."""
        rule_type = payload.get("rule_type", "")
        description = payload.get("description", payload.get("query", ""))
        context = await self._get_context(f"ITX {rule_type} rule syntax", category="functions")

        ai = get_ai_provider()
        user_prompt = f"""Generate ITX rule syntax for:

## Rule Type: {rule_type}
## Description: {description}

## Reference Documentation:
{context}

Provide:
1. Complete syntax example
2. Explanation of each part
3. Practical usage scenario
4. Common variations"""

        response = await ai.generate(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            temperature=0.2,
        )

        return PluginResponse(content=response, confidence=0.8, metadata={"rule_type": rule_type})

    async def _debug_trace(self, payload: dict) -> PluginResponse:
        """Module 7: Debug trace/error logs."""
        trace_content = payload.get("trace_content", "")
        error_message = payload.get("error_message", "")
        context = await self._get_context("ITX error troubleshooting trace", category="error_docs")

        ai = get_ai_provider()
        user_prompt = f"""Analyze this ITX trace/error log and provide debugging assistance:

## Trace Log:
```
{trace_content}
```

## Error Message:
{error_message}

## Reference Documentation:
{context}

Provide root cause analysis, exact issue location, suggested fix, confidence score, and related documentation references."""

        response = await ai.generate(
            system_prompt=DEBUG_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=2500,
        )

        return PluginResponse(content=response, confidence=0.7, metadata={"type": "debug"})

    async def _generate_test_data(self, payload: dict) -> PluginResponse:
        """Module 8: Generate test data."""
        structure = payload.get("structure", "")
        test_type = payload.get("test_type", "valid")  # valid | invalid | edge | malformed
        count = payload.get("count", 5)

        ai = get_ai_provider()
        user_prompt = f"""Generate {count} {test_type} test data records based on this structure:

## Data Structure:
```
{structure}
```

## Test Type: {test_type}
- valid: Properly formatted records that pass all validations
- invalid: Records with validation errors
- edge: Edge cases (empty fields, max lengths, special characters)
- malformed: Badly formatted records (wrong delimiters, missing fields)

Generate the test data records and explain what each tests."""

        response = await ai.generate(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=2000,
        )

        return PluginResponse(content=response, confidence=0.8, metadata={"test_type": test_type})

    async def _compare_artifacts(self, payload: dict) -> PluginResponse:
        """Module 10: Compare two artifacts."""
        artifact_a = payload.get("artifact_a", "")
        artifact_b = payload.get("artifact_b", "")

        ai = get_ai_provider()
        user_prompt = f"""Compare these two ITX artifacts and identify differences:

## Artifact A:
```
{artifact_a}
```

## Artifact B:
```
{artifact_b}
```

Analyze and report:
1. Structural differences
2. Rule changes
3. Missing mappings
4. Changed logic
5. Validation differences
6. Summary of changes"""

        response = await ai.generate(
            system_prompt=self.get_system_prompt(),
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=2500,
        )

        return PluginResponse(content=response, confidence=0.75, metadata={"type": "comparison"})
