#!/usr/bin/env python3
"""
Fix common Markdown math issues from copied chat logs.

This script:
- Converts bracket-style display math blocks ("[" ... "]") to $$ ... $$.
- Converts inline math written as "(...)" into $ ... $ when it looks like TeX.
- Converts inline math written as "\\( ... \\)" into $ ... $.
- Collapses separator lines like "====" inside display math into "=".
- Fixes common TeX typos such as "\sum*{", "\bar{y}*i", and "$...$^2".
- Strips stray leading "#" markers inside display math blocks.
#
# Comment:
# - Double-click runs against raw.md in the same folder.
# - For all .md files in the folder (PowerShell):
#   Get-ChildItem -Filter *.md | ForEach-Object { python md_math_fix.py $_.FullName }
# - Batch mode (Python example, uncomment to use):
#   # for md_path in Path(".").glob("*.md"):
#   #     fixed, _, _ = fix_markdown(md_path.read_text(encoding="utf-8", errors="replace"))
#   #     default_output_path(md_path).write_text(fixed, encoding="utf-8")

It writes <stem>.fixed.md by default and prints a brief report.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, List, Tuple


BLOCKQUOTE_RE = re.compile(r"^(\s*(?:>\s*)*)(.*)$")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
LINK_RE = re.compile(r"!?\[[^\]]*]\([^)]+\)")
INLINE_MATH_RE = re.compile(r"\\\([^\\]*?\\\)")
INLINE_MATH_BRACKET_RE = re.compile(r"\\\[[^\\]*?\\\]")
PAREN_RE = re.compile(r"(?<!\\)\(([^()]+)\)")
INLINE_BACKSLASH_RE = re.compile(r"\\\((.*?)\\\)")
MATH_HINT_RE = re.compile(r"(\\[A-Za-z]+|[_^])")
EQUALS_LINE_RE = re.compile(r"^=+\s*$")
SUM_STAR_RE = re.compile(r"\\sum\*{")
BAR_STAR_RE = re.compile(r"\\bar\{([^}]+)\}\*([A-Za-z0-9])")
HAT_I_RE = re.compile(r"\\hat_i\b")
SUM_EMPTY_RE = re.compile(r"\\sum_\^")
BOXED2_LINE_RE = re.compile(r"^(\s*(?:>\s*)*)\\boxed\^2\s*$")
PAREN_DOLLAR_EXP_RE = re.compile(r"\(\$([^$]+)\$(\^\{?[^{}\s]+\}?)\)")
INLINE_DOLLAR_EXP_RE = re.compile(r"\$([^$]+?)\$(\^\{?[^{}\s]+\}?)")
SUM_ONLY_LINE_RE = re.compile(r"^\s*\\sum_\^\s*$")
FRAC_ONLY_LINE_RE = re.compile(r"^\s*\\frac\s*$")


def split_blockquote(line: str) -> Tuple[str, str]:
    match = BLOCKQUOTE_RE.match(line)
    if not match:
        return "", line
    return match.group(1), match.group(2)


def normalize_bracket_delim(line: str) -> str | None:
    prefix, rest = split_blockquote(line)
    stripped = rest.strip()
    if stripped.startswith("#"):
        stripped = stripped.lstrip("#").strip()
    if stripped in {"[", "]"}:
        return f"{prefix}$$"
    return None


def is_display_delim(line: str) -> bool:
    _, rest = split_blockquote(line)
    stripped = rest.strip()
    return stripped in {"$$", "\\[", "\\]"}


def strip_leading_hash_in_math(line: str) -> str:
    prefix, rest = split_blockquote(line)
    rest_lstrip = rest.lstrip()
    if rest_lstrip.startswith("#"):
        rest_lstrip = rest_lstrip[1:].lstrip()
        return f"{prefix}{rest_lstrip}"
    return line


def find_dollar_spans(line: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    i = 0
    length = len(line)
    while i < length:
        if line[i] == "\\":
            i += 2
            continue
        if line[i] == "$":
            if i + 1 < length and line[i + 1] == "$":
                j = line.find("$$", i + 2)
                if j == -1:
                    break
                spans.append((i, j + 2))
                i = j + 2
                continue
            j = i + 1
            while j < length:
                if line[j] == "\\":
                    j += 2
                    continue
                if line[j] == "$":
                    spans.append((i, j + 1))
                    i = j + 1
                    break
                j += 1
            else:
                break
        i += 1
    return spans


def collect_protected_spans(line: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    for regex in (INLINE_CODE_RE, LINK_RE, INLINE_MATH_RE, INLINE_MATH_BRACKET_RE):
        for match in regex.finditer(line):
            spans.append((match.start(), match.end()))
    spans.extend(find_dollar_spans(line))
    spans.sort()
    return spans


def collect_nonmath_spans(line: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    for regex in (INLINE_CODE_RE, LINK_RE, INLINE_MATH_BRACKET_RE):
        for match in regex.finditer(line):
            spans.append((match.start(), match.end()))
    spans.extend(find_dollar_spans(line))
    spans.sort()
    return spans


def collect_code_link_spans(line: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    for regex in (INLINE_CODE_RE, LINK_RE):
        for match in regex.finditer(line):
            spans.append((match.start(), match.end()))
    spans.sort()
    return spans


def is_in_spans(spans: Iterable[Tuple[int, int]], index: int) -> bool:
    for start, end in spans:
        if start <= index < end:
            return True
    return False


def replace_outside_spans(
    line: str,
    spans: Iterable[Tuple[int, int]],
    regex: re.Pattern[str],
    replacement,
) -> Tuple[str, int]:
    count = 0

    def apply(match: re.Match[str]) -> str:
        nonlocal count
        if is_in_spans(spans, match.start()):
            return match.group(0)
        count += 1
        if callable(replacement):
            return replacement(match)
        return replacement

    return regex.sub(apply, line), count


def fix_inline_parentheses(line: str) -> Tuple[str, int]:
    spans = collect_protected_spans(line)
    converted = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal converted
        if is_in_spans(spans, match.start()):
            return match.group(0)
        content = match.group(1)
        if "$" in content:
            return match.group(0)
        if not MATH_HINT_RE.search(content):
            return match.group(0)
        converted += 1
        return "$" + content + "$"

    return PAREN_RE.sub(replace, line), converted


def fix_inline_backslash_math(line: str) -> Tuple[str, int]:
    spans = collect_nonmath_spans(line)
    converted = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal converted
        if is_in_spans(spans, match.start()):
            return match.group(0)
        content = match.group(1)
        if "$" in content:
            return match.group(0)
        converted += 1
        return "$" + content + "$"

    return INLINE_BACKSLASH_RE.sub(replace, line), converted


def fix_inline_dollar_exponent(line: str) -> Tuple[str, int, int]:
    paren_fixed = 0
    inline_fixed = 0
    spans = collect_code_link_spans(line)

    def replace_paren(match: re.Match[str]) -> str:
        nonlocal paren_fixed
        if is_in_spans(spans, match.start()):
            return match.group(0)
        paren_fixed += 1
        content = match.group(1)
        exponent = match.group(2)
        return "$(" + content + ")" + exponent + "$"

    line = PAREN_DOLLAR_EXP_RE.sub(replace_paren, line)
    spans = collect_code_link_spans(line)

    def replace_inline(match: re.Match[str]) -> str:
        nonlocal inline_fixed
        if is_in_spans(spans, match.start()):
            return match.group(0)
        inline_fixed += 1
        return "$" + match.group(1) + match.group(2) + "$"

    line = INLINE_DOLLAR_EXP_RE.sub(replace_inline, line)
    return line, paren_fixed, inline_fixed


def fix_common_math_tokens(line: str) -> Tuple[str, dict]:
    stats = {
        "sum_star_fixed": 0,
        "bar_star_fixed": 0,
        "hat_i_fixed": 0,
        "sum_empty_fixed": 0,
    }

    spans = collect_code_link_spans(line)
    line, count = replace_outside_spans(line, spans, SUM_STAR_RE, r"\\sum_{")
    stats["sum_star_fixed"] += count

    spans = collect_code_link_spans(line)
    line, count = replace_outside_spans(
        line,
        spans,
        BAR_STAR_RE,
        lambda m: f"\\bar{{{m.group(1)}}}_{m.group(2)}",
    )
    stats["bar_star_fixed"] += count

    spans = collect_code_link_spans(line)
    line, count = replace_outside_spans(line, spans, HAT_I_RE, r"\\hat{y}_i")
    stats["hat_i_fixed"] += count

    spans = collect_code_link_spans(line)
    line, count = replace_outside_spans(line, spans, SUM_EMPTY_RE, r"\\sum_{i=1}^{N}")
    stats["sum_empty_fixed"] += count

    return line, stats


def is_equals_line(line: str) -> bool:
    _, rest = split_blockquote(line)
    return bool(EQUALS_LINE_RE.match(rest.strip()))


def fix_equals_line(line: str) -> Tuple[str, int]:
    prefix, rest = split_blockquote(line)
    if EQUALS_LINE_RE.match(rest.strip()):
        return f"{prefix}=", 1
    return line, 0


def fix_boxed2_line(line: str) -> Tuple[str, int]:
    match = BOXED2_LINE_RE.match(line)
    if not match:
        return line, 0
    prefix = match.group(1)
    return f"{prefix}\\boxed{{\\hat{{\\sigma}}^2", 1


def default_output_path(path: Path) -> Path:
    if path.suffix.lower() == ".md":
        return path.with_name(f"{path.stem}.fixed.md")
    return path.with_name(f"{path.name}.fixed.md")


def fix_markdown(text: str) -> Tuple[str, dict, list]:
    lines = text.splitlines()
    out_lines: List[str] = []
    in_code_block = False
    in_display_math = False
    stats = {
        "display_brackets_converted": 0,
        "display_dollar_delims_seen": 0,
        "inline_parentheses_converted": 0,
        "inline_backslash_converted": 0,
        "inline_paren_exponent_fixed": 0,
        "inline_exponent_fixed": 0,
        "math_hash_stripped": 0,
        "display_math_closed": 0,
        "equals_lines_collapsed": 0,
        "equals_lines_skipped": 0,
        "sum_star_fixed": 0,
        "bar_star_fixed": 0,
        "hat_i_fixed": 0,
        "sum_empty_fixed": 0,
        "boxed2_fixed": 0,
        "placeholder_sum_removed": 0,
        "placeholder_frac_removed": 0,
    }
    warnings: List[str] = []
    skip_next_equals = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            out_lines.append(line)
            continue

        if not in_code_block:
            replacement = normalize_bracket_delim(line)
            if replacement is not None:
                out_lines.append(replacement)
                stats["display_brackets_converted"] += 1
                in_display_math = not in_display_math
                continue

            if is_display_delim(line):
                out_lines.append(line)
                stats["display_dollar_delims_seen"] += 1
                in_display_math = not in_display_math
                continue

        if in_display_math and not in_code_block:
            if skip_next_equals and is_equals_line(line):
                stats["equals_lines_skipped"] += 1
                skip_next_equals = False
                continue

            boxed_line, boxed_count = fix_boxed2_line(line)
            if boxed_count:
                stats["boxed2_fixed"] += boxed_count
            line = boxed_line

            equals_line, equals_count = fix_equals_line(line)
            if equals_count:
                stats["equals_lines_collapsed"] += equals_count
            line = equals_line

            prefix, rest = split_blockquote(line)
            if SUM_ONLY_LINE_RE.match(rest.strip()):
                stats["placeholder_sum_removed"] += 1
                continue
            if FRAC_ONLY_LINE_RE.match(rest.strip()):
                stats["placeholder_frac_removed"] += 1
                skip_next_equals = True
                continue

            cleaned = strip_leading_hash_in_math(line)
            if cleaned != line:
                stats["math_hash_stripped"] += 1
            line = cleaned

        if not in_code_block:
            line, token_stats = fix_common_math_tokens(line)
            stats["sum_star_fixed"] += token_stats["sum_star_fixed"]
            stats["bar_star_fixed"] += token_stats["bar_star_fixed"]
            stats["hat_i_fixed"] += token_stats["hat_i_fixed"]
            stats["sum_empty_fixed"] += token_stats["sum_empty_fixed"]

        if not in_code_block and not in_display_math:
            line, count = fix_inline_backslash_math(line)
            stats["inline_backslash_converted"] += count
            line, count = fix_inline_parentheses(line)
            stats["inline_parentheses_converted"] += count
            line, paren_count, inline_count = fix_inline_dollar_exponent(line)
            stats["inline_paren_exponent_fixed"] += paren_count
            stats["inline_exponent_fixed"] += inline_count

        out_lines.append(line)

    if in_display_math:
        out_lines.append("$$")
        stats["display_math_closed"] += 1
        warnings.append("Unclosed display math block; appended '$$'.")

    fixed = "\n".join(out_lines)
    if text.endswith("\n"):
        fixed += "\n"
    return fixed, stats, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fix common Markdown math issues and write a .fixed.md file."
    )
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=None,
        help="Path to the Markdown file (default: raw.md).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: <stem>.fixed.md).",
    )
    args = parser.parse_args()

    in_path = args.path if args.path else Path("raw.md")

    if not in_path.exists():
        print(f"Input file not found: {in_path}")
        return 2

    text = in_path.read_text(encoding="utf-8", errors="replace")
    fixed, stats, warnings = fix_markdown(text)

    out_path = args.out if args.out else default_output_path(in_path)
    out_path.write_text(fixed, encoding="utf-8")

    print(f"Wrote: {out_path}")
    print("Report:")
    print(f"- display brackets converted: {stats['display_brackets_converted']}")
    print(f"- display $$ delims seen: {stats['display_dollar_delims_seen']}")
    print(f"- inline parentheses converted: {stats['inline_parentheses_converted']}")
    print(f"- inline \\\\(...\\\\) converted: {stats['inline_backslash_converted']}")
    print(f"- inline paren + $...$^ fixed: {stats['inline_paren_exponent_fixed']}")
    print(f"- inline $...$^ fixed: {stats['inline_exponent_fixed']}")
    print(f"- equals lines collapsed: {stats['equals_lines_collapsed']}")
    if stats["equals_lines_skipped"]:
        print(f"- equals lines skipped: {stats['equals_lines_skipped']}")
    print(f"- \\sum*{{}} fixed: {stats['sum_star_fixed']}")
    print(f"- \\bar{{}}*x fixed: {stats['bar_star_fixed']}")
    print(f"- \\hat_i fixed: {stats['hat_i_fixed']}")
    print(f"- \\sum_^ fixed: {stats['sum_empty_fixed']}")
    print(f"- \\boxed^2 fixed: {stats['boxed2_fixed']}")
    if stats["placeholder_sum_removed"]:
        print(f"- placeholder \\sum_^ removed: {stats['placeholder_sum_removed']}")
    if stats["placeholder_frac_removed"]:
        print(f"- placeholder \\frac removed: {stats['placeholder_frac_removed']}")
    print(f"- math lines with leading '#': {stats['math_hash_stripped']}")
    if stats["display_math_closed"]:
        print(f"- display math blocks auto-closed: {stats['display_math_closed']}")
    for warning in warnings:
        print(f"Warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
