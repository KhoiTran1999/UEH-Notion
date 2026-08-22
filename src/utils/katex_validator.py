import re

# List of LaTeX commands that MUST be enclosed within math delimiters ($...$ or $$...$$)
RAW_LATEX_CMD_PATTERN = re.compile(
    r'\\(text|times|div|frac|sqrt|implies|Leftrightarrow|Leftrightarrow|iff|cdot|left|right|alpha|beta|gamma|delta|Delta|pi|sigma|sum|prod|int|le|ge|neq|approx|pm|mp|to|infty)\b'
)

# Pattern for Vietnamese accented prose characters
VN_ACCENT_PATTERN = re.compile(
    r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]',
    re.I
)

# Splitting pattern for $...$ and $$...$$
MATH_BLOCK_PATTERN = re.compile(r'(\$\$.*?\$\$|\$.*?\$)', re.DOTALL)

def validate_katex_formatting(text: str) -> tuple[bool, list[str]]:
    """Strictly validates if a text field correctly adheres to KaTeX rendering rules.

    Returns:
        (is_valid: bool, error_messages: list[str])
    """
    if not isinstance(text, str) or not text.strip():
        return True, []

    errors = []

    # Rule 1: Dollar count symmetry (must be even, no unclosed $)
    if text.count('$') % 2 != 0:
        errors.append(f"Unmatched '$' math delimiter (total count = {text.count('$')})")

    # Split text into math blocks ($...$, $$...$$) vs plain text
    parts = MATH_BLOCK_PATTERN.split(text)

    for part in parts:
        if not part:
            continue

        if part.startswith('$'):
            # INSIDE MATH DELIMITER
            inner = part.strip('$').strip()

            if not inner:
                errors.append("Empty math delimiter ($$)")
                continue

            # Rule 2: Math block should not enclose long Vietnamese prose
            # (Exceptions: \text{...} inside math is allowed, but prose outside \text{} is invalid)
            # Remove \text{...} blocks before checking for raw prose
            inner_no_text = re.sub(r'\\text\s*\{[^{}]*\}', '', inner)
            if VN_ACCENT_PATTERN.search(inner_no_text):
                errors.append(f"Vietnamese prose incorrectly enclosed in math mode: '{part}'")

        else:
            # OUTSIDE MATH DELIMITER
            # Rule 3: Raw LaTeX math commands must not appear outside $...$ or $$...$$
            match = RAW_LATEX_CMD_PATTERN.search(part)
            if match:
                errors.append(
                    f"Unwrapped raw LaTeX command '\\{match.group(1)}' found outside math delimiters in segment: '{part.strip()}'"
                )

    return len(errors) == 0, errors

