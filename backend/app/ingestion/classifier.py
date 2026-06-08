"""
Content Classifier — classifies document content into ITX knowledge categories.
"""
import re
from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ITX Knowledge Categories with keyword patterns
ITX_CATEGORIES = {
    "type_tree": {
        "keywords": [
            "type tree", "typetree", "type definition", "field definition",
            "data type", "group", "item", "component", "root type",
            "delimiter", "field length", "repetition", "cardinality",
            "input card", "output card", "input type", "output type",
        ],
        "description": "Type Tree definitions, data types, field structures",
    },
    "mapping_rules": {
        "keywords": [
            "mapping", "map rule", "source to target", "field mapping",
            "transformation rule", "map logic", "mapping rule",
            "source field", "target field", "map design",
        ],
        "description": "Mapping rules, source-target field mappings",
    },
    "functions": {
        "keywords": [
            "function", "SUM", "COUNT", "CHOOSE", "EXISTS", "LOOKUP",
            "SUBSTRING", "CONCAT", "TRIM", "LENGTH", "ROUND",
            "DATE", "TIME", "FORMAT", "CONVERT", "CAST",
            "functional map", "built-in function", "function reference",
        ],
        "description": "ITX built-in functions and function references",
    },
    "cards": {
        "keywords": [
            "card", "input card", "output card", "map card",
            "adapter card", "card properties", "card settings",
            "card configuration",
        ],
        "description": "Cards (input, output, map, adapter)",
    },
    "validation": {
        "keywords": [
            "validation", "validate", "constraint", "restriction",
            "rule check", "data validation", "error check",
            "validation rule", "integrity",
        ],
        "description": "Validation rules and data integrity checks",
    },
    "launcher": {
        "keywords": [
            "launcher", "command line", "execution", "runtime",
            "invoke", "launch", "schedule", "batch", "automation",
            "itxlaunch", "dtxlaunch",
        ],
        "description": "Launcher configuration and execution",
    },
    "trace_logs": {
        "keywords": [
            "trace", "trace log", "debug trace", "execution trace",
            "audit trail", "log file", "trace output", "trace level",
            "trace option",
        ],
        "description": "Trace logs and debugging output",
    },
    "syntax": {
        "keywords": [
            "syntax", "expression", "operator", "statement",
            "code", "script", "formula", "notation",
        ],
        "description": "Syntax rules and expressions",
    },
    "examples": {
        "keywords": [
            "example", "sample", "demo", "tutorial", "walkthrough",
            "how to", "step by step", "use case", "scenario",
        ],
        "description": "Examples, tutorials, and walkthroughs",
    },
    "error_docs": {
        "keywords": [
            "error", "exception", "failure", "fault", "issue",
            "troubleshoot", "problem", "fix", "resolve", "workaround",
            "error code", "error message",
        ],
        "description": "Error documentation and troubleshooting",
    },
    "configuration": {
        "keywords": [
            "configuration", "config", "setting", "parameter",
            "property", "environment", "setup", "install",
            "prerequisite", "requirement",
        ],
        "description": "Configuration and setup documentation",
    },
}


class ContentClassifier:
    """Classifies document content into ITX knowledge categories."""

    def classify(self, text: str, heading: Optional[str] = None) -> str:
        """
        Classify text content into an ITX category.
        Returns the category with highest keyword match score.
        """
        # Combine heading and content for classification
        combined = f"{heading or ''} {text}".lower()

        scores = {}
        for category, info in ITX_CATEGORIES.items():
            score = 0
            for keyword in info["keywords"]:
                # Count occurrences, weighted by specificity
                count = combined.count(keyword.lower())
                weight = len(keyword.split())  # Multi-word keywords get higher weight
                score += count * weight

            if score > 0:
                scores[category] = score

        if not scores:
            return "general"

        # Return category with highest score
        return max(scores, key=scores.get)

    def classify_batch(self, texts: list[str], headings: list[Optional[str]] = None) -> list[str]:
        """Classify a batch of texts."""
        if headings is None:
            headings = [None] * len(texts)
        return [self.classify(text, heading) for text, heading in zip(texts, headings)]

    @staticmethod
    def get_all_categories() -> list[str]:
        """Return all available categories."""
        return list(ITX_CATEGORIES.keys())

    @staticmethod
    def get_category_info(category: str) -> dict:
        """Get info about a category."""
        return ITX_CATEGORIES.get(category, {"keywords": [], "description": "Unknown category"})


# Singleton
content_classifier = ContentClassifier()
