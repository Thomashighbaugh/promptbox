"""
Utilities for parsing and handling template variables in prompt strings.
This version correctly handles the user-specified [[variable]] format.
"""

import re

def extract_variables(text: str) -> list[str]:
    """
    Extracts all unique variables formatted as [[variable_name]] from a string.
    """
    if not text:
        return []
    # This regex finds all occurrences of [[...]] and captures the content inside.
    # It's made unique by converting to a set, then sorted for consistent order.
    variables = re.findall(r"\[\[\s*(\w+)\s*\]\]", text)
    return sorted(list(set(variables)))


def substitute_variables(text: str, context: dict[str, str]) -> str:
    """
    Substitutes [[variable_name]] in a string with values from a context dictionary.
    """
    if not text or not context:
        return text

    # Iteratively replace each variable found in the context.
    for var_name, var_value in context.items():
        # Build the pattern to find for this specific variable, e.g., [[my_var]]
        pattern = r"\[\[\s*" + re.escape(var_name) + r"\s*\]\]"
        text = re.sub(pattern, var_value, text)
        
    return text
