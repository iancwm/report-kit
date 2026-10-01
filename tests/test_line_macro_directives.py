"""AC9: Markdown line-macro directives render the same TeX as the hand-written form.

Pure Python: neither a TeX toolchain nor a render is needed. The golden TeX
below is the hand-written form from the Operator spec section 5.3.
"""
from __future__ import annotations

import pytest

from reportkit.markdown_directives import parse_markdown
from reportkit.registry import generate_registry
from reportkit.tex_renderer import render_node

TERMINAL_MD = """```reportkit terminalblock
title: Metered credits vs direct API
content: |
  # invoice = F + max(0, N*c - A)
  $ atlas cost --attempts 80
  Total: $212.40 (credit cap reached at attempt 64)
```
"""

TERMINAL_TEX = r"""\begin{terminalblock}[Metered credits vs direct API]
\termcomment{invoice = F + max(0, N*c - A)}
\termprompt{atlas cost --attempts 80}
\termline{Total: \$212.40 (credit cap reached at attempt 64)}
\end{terminalblock}"""

DIFF_MD = """```reportkit diffblock
title: src/auth/session.ts
content: |
  @@ -12,3 +12,3 @@
  - const token = req.headers['x-token'];
  + const token = verifyJWT(req.headers.authorization);
  if (!token) return deny(res);
```
"""

DIFF_TEX = r"""\begin{diffblock}[src/auth/session.ts]
\diffhunk{@@ -12,3 +12,3 @@}
\diffdel{const token = req.headers['x-token'];}
\diffadd{const token = verifyJWT(req.headers.authorization);}
\diffctx{if (!token) return deny(res);}
\end{diffblock}"""

GRID_MD = """```reportkit capabilitygrid
columns: Local,Remote,Plan,MCP,Sub-agents,Worktree,Headless,Permissions,Hooks
content: |
  Atlas CLI | first-party | DDDDUDDDD
  Beacon | open-source | DUDDUUDUU
```
"""

GRID_TEX = r"""\begin{capabilitygrid}[]{Local,Remote,Plan,MCP,Sub-agents,Worktree,Headless,Permissions,Hooks}
\capabilityrow[first-party]{Atlas CLI}{DDDDUDDDD}
\capabilityrow[open-source]{Beacon}{DUDDUUDUU}
\end{capabilitygrid}"""


def _render(markdown: str) -> str:
    parsed = parse_markdown(markdown, source_file="manuscript/ch.md")
    assert not parsed.diagnostics, parsed.diagnostics
    assert len(parsed.directives) == 1
    return render_node(parsed.directives[0])


def _record_constraint(name: str) -> dict:
    record = generate_registry()["primitives"]["composition"][name]
    found = [c for c in record["constraints"] if c.get("code") == "line_macros"]
    assert len(found) == 1
    return found[0]


# --------------------------------------------------------------- contract


def test_contract_declares_frozen_line_macro_constraints() -> None:
    terminal = _record_constraint("terminalblock")
    assert terminal["prefixes"] == [["$ ", "termprompt"], ["# ", "termcomment"]]
    assert terminal["default"] == "termline"
    diff = _record_constraint("diffblock")
    assert diff["prefixes"] == [["@@", "diffhunk"], ["+", "diffadd"], ["-", "diffdel"]]
    assert diff["preserve_prefixes"] == ["@@"]
    assert diff["default"] == "diffctx"
    grid = _record_constraint("capabilitygrid")
    assert grid["split"] == "|" and grid["macro"] == "capabilityrow"


# ----------------------------------------------------------------- goldens


def test_terminalblock_matches_hand_written_tex() -> None:
    assert _render(TERMINAL_MD) == TERMINAL_TEX


def test_diffblock_matches_hand_written_tex() -> None:
    assert _render(DIFF_MD) == DIFF_TEX


def test_capabilitygrid_matches_hand_written_tex() -> None:
    assert _render(GRID_MD) == GRID_TEX


def test_capabilitygrid_row_without_tag_has_empty_optional_tag() -> None:
    rendered = _render(GRID_MD.replace("Beacon | open-source | DUDDUUDUU", "Beacon | DUDDUUDUU"))
    assert r"\capabilityrow[]{Beacon}{DUDDUUDUU}" in rendered


@pytest.mark.xfail(
    strict=True,
    reason=(
        "discrepancy: spec section 5.3 shows a context line indented two spaces beyond "
        "the block indent and says it renders as the hand-written \\diffctx{if (!token) "
        "return deny(res);}; the renderer keeps the spaces as ~~ because only the +/-/@@ "
        "prefixes are stripped, so no single leading context-gutter space is removed"
    ),
)
def test_diff_context_line_with_leading_space_matches_spec_example() -> None:
    markdown = DIFF_MD.replace("  if (!token)", "    if (!token)")
    assert _render(markdown) == DIFF_TEX


# ----------------------------------------------------------- metacharacters


@pytest.mark.parametrize(
    ("raw", "escaped"),
    [
        ("$", r"\$"),
        ("_", r"\_"),
        ("%", r"\%"),
        ("#", r"\#"),
        ("&", r"\&"),
        ("\\", r"\textbackslash{}"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ],
)
def test_every_metacharacter_is_escaped_in_terminal_and_diff_lines(raw: str, escaped: str) -> None:
    terminal = _render(f"```reportkit terminalblock\ncontent: |\n  a{raw}b\n```\n")
    assert f"\\termline{{a{escaped}b}}" in terminal
    diff = _render(f"```reportkit diffblock\ncontent: |\n  + a{raw}b\n  - a{raw}b\n```\n")
    assert f"\\diffadd{{a{escaped}b}}" in diff
    assert f"\\diffdel{{a{escaped}b}}" in diff


def test_prefix_payload_with_metacharacters_is_escaped_after_prefix_removal() -> None:
    rendered = _render(
        "```reportkit terminalblock\ncontent: |\n  $ echo 100% > out_file # x & y\n  # {note}\n```\n"
    )
    assert r"\termprompt{echo 100\% > out\_file \# x \& y}" in rendered
    assert r"\termcomment{\{note\}}" in rendered


def test_no_raw_metacharacter_survives_outside_macro_names() -> None:
    rendered = _render(
        "```reportkit terminalblock\ncontent: |\n  $ a_b % c # d & e \\ {f} ~ ^ $x\n```\n"
    )
    body = rendered.split("\n")[1]
    assert body == (
        r"\termprompt{a\_b \% c \# d \& e \textbackslash{} \{f\} "
        r"\textasciitilde{} \textasciicircum{} \$x}"
    )


# --------------------------------------------------------------- whitespace


def test_blank_lines_are_kept_as_empty_line_macros() -> None:
    rendered = _render("```reportkit terminalblock\ncontent: |\n  $ one\n\n  two\n```\n")
    assert rendered.split("\n")[1:4] == [r"\termprompt{one}", r"\termline{}", r"\termline{two}"]


def test_first_line_indentation_survives() -> None:
    rendered = _render("```reportkit terminalblock\ncontent: |\n    indented first\n  plain\n```\n")
    assert rendered.split("\n")[1] == r"\termline{~~indented first}"


def test_indentation_after_prefix_becomes_tildes() -> None:
    rendered = _render("```reportkit diffblock\ncontent: |\n  +   deeper\n```\n")
    assert r"\diffadd{~~deeper}" in rendered


def test_diff_hunk_marker_is_preserved() -> None:
    rendered = _render("```reportkit diffblock\ncontent: |\n  @@ -1 +1 @@ fn\n```\n")
    assert r"\diffhunk{@@ -1 +1 @@ fn}" in rendered


# ----------------------------------------------------------- parse diagnostics


def _codes(markdown: str) -> list[str]:
    return [item["code"] for item in parse_markdown(markdown, source_file="m.md").diagnostics]


def test_capabilitygrid_wrong_field_count_is_a_directive_diagnostic_with_line() -> None:
    markdown = "```reportkit capabilitygrid\ncolumns: A,B\ncontent: |\n  ok | DD\n  a | b | c | DD\n```\n"
    parsed = parse_markdown(markdown, source_file="m.md")
    assert [d["code"] for d in parsed.diagnostics] == ["RK_AUTHORING_CAPABILITY_FIELDS"]
    assert parsed.diagnostics[0]["source"]["line"] == 5
    assert parsed.diagnostics[0]["source"]["file"] == "m.md"


def test_capabilitygrid_name_only_row_is_rejected() -> None:
    markdown = "```reportkit capabilitygrid\ncolumns: A\ncontent: |\n  only-a-name\n```\n"
    assert _codes(markdown) == ["RK_AUTHORING_CAPABILITY_FIELDS"]


def test_capabilitygrid_invalid_cell_characters_are_diagnosed() -> None:
    markdown = "```reportkit capabilitygrid\ncolumns: A,B\ncontent: |\n  X | DQ\n```\n"
    parsed = parse_markdown(markdown, source_file="m.md")
    assert [d["code"] for d in parsed.diagnostics] == ["RK_AUTHORING_CAPABILITY_CELLS"]
    assert parsed.diagnostics[0]["source"]["line"] == 4
    assert parsed.diagnostics[0]["details"]["invalid_characters"] == ["Q"]


def test_renderer_refuses_invalid_cells_even_without_the_parser() -> None:
    parsed = parse_markdown(
        "```reportkit capabilitygrid\ncolumns: A\ncontent: |\n  X | D\n```\n", source_file="m.md"
    )
    node = parsed.directives[0]
    from dataclasses import replace

    with pytest.raises(ValueError, match="only D, U, or -"):
        render_node(replace(node, content="X | DZ"))


# ----------------------------------------------------------- non-regression


def test_existing_callout_directive_renders_unchanged() -> None:
    rendered = _render("```reportkit redflag\ntitle: Weak\ncontent: Risk $5 & more_text\n```\n")
    assert rendered == "\\begin{redflag}[Weak]\nRisk \\$5 \\& more\\_text\n\\end{redflag}"


def test_ordinary_content_is_still_stripped_and_not_line_split() -> None:
    rendered = _render("```reportkit redflag\ncontent: |\n  first\n  second\n```\n")
    assert rendered == "\\begin{redflag}\nfirst\nsecond\n\\end{redflag}"
