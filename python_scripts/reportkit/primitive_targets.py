"""Reviewed publication-type roles for public authoring primitives.

The table is deliberately independent of theme styling: a primitive's role is
part of a publication type's structure, while the theme only changes its look.
It implements the target-scoped context contract in agent reasoning loop spec
§4.5. New registry entries fail closed until they are added here.
"""
from __future__ import annotations

from typing import Any, Literal

from .publications import PUBLICATION_TYPES

Role = Literal["native", "allowed", "discouraged", "absent"]
ROLES: tuple[str, ...] = ("native", "allowed", "discouraged", "absent")
_PUBLICATION_TYPES = tuple(PUBLICATION_TYPES)


def _roles(
    *, native: tuple[str, ...] = (), allowed: tuple[str, ...] = (),
    discouraged: tuple[str, ...] = (),
) -> dict[str, Role]:
    """Expand concise family policy into an explicit role for every target."""
    result: dict[str, Role] = {target: "absent" for target in _PUBLICATION_TYPES}
    for target in native:
        result[target] = "native"
    for target in allowed:
        result[target] = "allowed"
    for target in discouraged:
        result[target] = "discouraged"
    return result


def _family(
    *,
    members: dict[str, tuple[str, ...]],
    native: tuple[str, ...] = (),
    allowed: tuple[str, ...] = (),
    discouraged: tuple[str, ...] = (),
    overrides: dict[str, dict[str, Role]] | None = None,
) -> dict[str, Any]:
    return {
        "members": members,
        "roles": _roles(native=native, allowed=allowed, discouraged=discouraged),
        "overrides": overrides or {},
    }


_REPORT = ("technical-report",)
_RESEARCH = ("equity-research",)
_BRIEF = ("executive-brief",)
_FEATURE = ("feature-article",)
_BOOK = ("book",)
_PRESENTATION = ("presentation",)
_PAGED_GENERAL = ("technical-report", "equity-research", "executive-brief", "book")
_IDENTITY_COMMANDS = (
    "productchip", "productavatar", "pricepill", "statusdot", "capdocumented",
    "capunestablished", "capabilityrow",
)
_EXECUTION_COMMANDS = ("termline", "termprompt", "termcomment", "diffadd", "diffdel", "diffctx", "diffhunk")
_REFERENCES_COMMANDS = ("RKBibliography", "RKContents")
_IDENTITY_COMPOSITIONS = ("capabilitygrid",)
_EXECUTION_COMPOSITIONS = ("terminalblock", "diffblock")
_OPERATOR_CHARTS = ("stacked_bar_chart", "line_chart")

# Keys are source families (LaTeX package or chart module). Each family lists
# its complete current public inventory by kind; name overrides keep shared
# packages curated where a publication uses only a small part of their grammar.
# Roles for all six publication types are explicit after _roles() expansion.
ROLE_TABLE: dict[str, Any] = {
    "reportkit-identity.sty": _family(
        members={"composition": _IDENTITY_COMPOSITIONS, "command": _IDENTITY_COMMANDS},
        native=(*_REPORT, *_BOOK), allowed=(*_RESEARCH, *_BRIEF),
    ),
    "reportkit-execution.sty": _family(
        members={"composition": _EXECUTION_COMPOSITIONS, "command": _EXECUTION_COMMANDS},
        native=(*_REPORT, *_BOOK), allowed=(*_RESEARCH, *_BRIEF),
    ),
    "operator.py": _family(
        members={"chart": _OPERATOR_CHARTS},
        native=(*_REPORT, *_BOOK), allowed=(*_RESEARCH, *_BRIEF),
    ),
    "reportkit-boxes.sty": _family(
        members={"callout": (
            "principle", "decisionpoint", "researchproblem", "assumption", "redflag",
            "evidencenote", "limitationnote", "tipnote", "deliverablenote",
            "evidence", "limitation", "tip", "metric",
        )},
        native=(*_REPORT, *_BOOK), allowed=(*_RESEARCH, *_BRIEF), discouraged=_FEATURE,
    ),
    "reportkit-theme-default.sty": _family(
        members={"callout": ("execsummary",)}, native=_REPORT,
    ),
    "reportkit-algorithm-dp.sty": _family(
        members={"figure": ("dptable",), "command": ("dpcell", "currentcell", "dependencycell", "solvedcell")},
        native=(*_REPORT, *_BOOK),
    ),
    "reportkit-algorithm-graph.sty": _family(
        members={"figure": ("graphstate", "gridstate", "dagstate"), "command": (
            "graphnode", "graphedge", "gridcell", "dagnode", "dependency", "readyqueue",
        )}, native=(*_REPORT, *_BOOK),
    ),
    "reportkit-algorithm-linear.sty": _family(
        members={"figure": ("stackstate", "queuestate"), "command": ("push", "enqueue")},
        native=(*_REPORT, *_BOOK),
    ),
    "reportkit-algorithm-order.sty": _family(
        members={"figure": ("intervalstate", "heapstate"), "command": ("interval", "merged", "current")},
        native=(*_REPORT, *_BOOK),
    ),
    "reportkit-algorithm-p3.sty": _family(
        members={"figure": ("joinstate", "unionfindstate", "linkedliststate", "recursiontree"), "command": (
            "joininput", "hashbucket", "joinmatch", "joinunmatched", "joinoutput", "ufnode", "parent",
            "union", "findpath", "listnode", "nextlink", "head", "tail", "recursionnode", "recursionedge",
        )}, native=(*_REPORT, *_BOOK),
    ),
    "reportkit-algorithm-viz.sty": _family(
        members={"figure": ("arraystate", "windowstate", "algorithmtrace"), "command": (
            "cell", "row", "pointer", "range", "annotation", "values", "window", "entering", "leaving",
            "snapshot", "tracetransition",
        )}, native=(*_REPORT, *_BOOK),
    ),
    "reportkit-algorithms.sty": _family(
        members={"composition": ("algorithmblock",), "command": ("AlgorithmInput", "AlgorithmOutput")},
        native=(*_REPORT, *_BOOK),
    ),
    "reportkit-code.sty": _family(
        members={"composition": ("codeblock", "outputblock")}, native=(*_REPORT, *_BOOK),
        allowed=(*_RESEARCH, *_BRIEF),
    ),
    "reportkit-diagrams.sty": _family(
        members={"figure": ("evidencestack", "reportcycle", "reportfunnel"), "composition": ("diagram",), "command": (
            "RKNode", "RKNodeRel", "RKEdge", "RKMatrixSetup", "RKMatrix", "RKMatrixCell", "RKSwimlaneSetup",
            "RKLane", "RKLaneNode", "RKLayerSetup", "RKLayer", "RKStackSetup", "RKStackTier", "RKCycleSetup",
            "RKCycleNode", "RKCycleEdge", "RKFunnelSetup", "RKFunnelStage", "evidencetier", "cyclestage",
            "cycleedge", "funnelstage",
        )}, native=_PAGED_GENERAL,
        allowed=_PRESENTATION,
        overrides={"diagram": {"feature-article": "allowed"}, "reportcycle": {"presentation": "allowed"}},
    ),
    "reportkit-grammar.sty": _family(
        members={"figure": ("reportstate", "reportcompare", "reporttimeline"), "command": (
            "state", "terminalstate", "stateat", "terminalstateat", "transition", "selfloop", "panel", "panelitem",
            "transformarrow", "event", "skewarrow", "watermark",
        )}, native=_PAGED_GENERAL, allowed=_PRESENTATION,
    ),
    "reportkit-process.sty": _family(
        members={"figure": ("reportflow", "reportswimlane", "reportnetwork", "causalloop"), "command": (
            "step", "stepat", "flowedge", "branch", "merge", "lanestep", "handoff", "laneflow", "networknode",
            "networkedge", "causalnode", "causaledge",
        )}, native=_PAGED_GENERAL, allowed=_PRESENTATION,
        overrides={
            "reportflow": {"feature-article": "allowed"},
            "step": {"feature-article": "allowed"},
            "flowedge": {"feature-article": "allowed"},
        },
    ),
    "reportkit-spatial.sty": _family(
        members={"figure": ("reportmatrix", "riskheatmap"), "command": ("quadrant", "point", "risk")},
        native=_PAGED_GENERAL, allowed=_PRESENTATION,
    ),
    "reportkit-structure.sty": _family(
        members={"figure": (
            "capabilitymap", "continuum", "maturitymodel", "reportarchitecture", "reportroadmap",
            "strategicpillars", "reporttree",
        )}, native=(*_REPORT, *_BOOK), allowed=(*_RESEARCH, *_BRIEF, *_PRESENTATION),
    ),
    "composition.py": _family(
        members={"chart": ("donut_chart", "waterfall_chart", "treemap_chart", "tornado_chart")},
        native=_PAGED_GENERAL, allowed=(*_FEATURE, *_PRESENTATION),
    ),
    "relationships.py": _family(
        members={"chart": ("bar_chart", "distribution", "scatter_plot", "heatmap", "bubble_matrix")},
        native=_PAGED_GENERAL, allowed=(*_FEATURE, *_PRESENTATION),
    ),
    "timeseries.py": _family(
        members={"chart": ("timeseries", "drawdown_chart", "risk_reward_chart", "timeline_chart")},
        native=_PAGED_GENERAL, allowed=(*_FEATURE, *_PRESENTATION),
        overrides={"risk_reward_chart": {"feature-article": "absent", "presentation": "absent"}},
    ),
    "reportkit-core.sty": _family(
        members={"command": ("RKLink", "RKDiagramSection", "RKDiagramSubsection")}, native=_PAGED_GENERAL,
        overrides={"RKLink": {"feature-article": "allowed", "presentation": "allowed"}},
    ),
    "reportkit-longform.sty": _family(
        members={"composition": ("RKShortListing",), "command": ("RKPath", "RKTitlePage")},
        native=(*_REPORT, *_BOOK),
        overrides={"RKPath": {"book": "native"}, "RKTitlePage": {"book": "native"}},
    ),
    "reportkit-book.sty": _family(
        members={"composition": ("bookdetails", "bookreferences", "bookglossary"), "command": (
            "bookpart", "bookdetail", "bookappendix", "glossaryterm",
        )}, native=_BOOK,
    ),
    "reportkit-equity-research.sty": _family(
        members={"composition": (
            "researchfrontpage", "ratingstrip", "researchmain", "researchsidebar", "analystblock",
            "marketdatablock", "estimatesblock", "whatschanged", "financialmodelpage",
        ), "command": ("ratingitem", "sidebarrow", "change", "rkscenario", "bullcase", "basecase", "bearcase")},
        native=_RESEARCH,
    ),
    "reportkit-executive-brief.sty": _family(
        members={"composition": ("briefheader", "briefactions", "briefsources"), "command": ("briefmeta", "briefaction")},
        native=_BRIEF,
    ),
    "reportkit-exhibits.sty": _family(
        members={"composition": ("financialtable", "exhibit", "fullwidthexhibit", "exhibitgrid", "exhibitpair"),
                 "command": ("exhibitpane",)}, native=(*_RESEARCH, *_BRIEF),
    ),
    "reportkit-feature-article.sty": _family(
        members={"composition": (
            "featureopening", "openingvisual", "featurecolumns", "featuresidebar", "featureexhibit", "featuretable",
            "featurereferences",
        ), "command": (
            "featureheadline", "featuredeck", "featurebyline", "imagecredit", "dropcap", "pullquote", "featuresection",
        )}, native=_FEATURE,
    ),
    "reportkit-presentation.sty": _family(
        members={"composition": (
            "titleslide", "sectiondivider", "appendixdivider", "messageslide", "assertionslide", "referenceslide",
            "agendaslide",
            "evidenceslide", "cardgrid", "visualtext", "chartslide", "tableslide", "fullvisual",
            "architectureslide", "comparison", "threepart", "herometric", "closingslide",
        ), "command": ("referenceitem", "carditem", "comparisoncolumn", "threepartcolumn")},
        native=_PRESENTATION,
    ),
    "references_and_contents": _family(
        members={"command": ("RKBibliography", "RKContents")},
        native=_PUBLICATION_TYPES,
    ),
    # The core class command is not emitted by the source registry, but giving
    # it a role makes the canonical template policy explicit too.
    "@document": _family(
        members={"command": ("maketitle",)}, native=_REPORT,
    ),
}


# The context slice has an enforced 8k estimate. This reviewed per-target
# shortlist keeps high-level structures and their commonly needed commands;
# the complete public inventory remains in primitive-contract.md. The family
# table above still accounts for every primitive, and this matrix assigns a
# role to every family member for every publication type (including absent).
_CALLOUTS = (
    "principle", "decisionpoint", "researchproblem", "assumption", "redflag",
    "evidencenote", "limitationnote", "tipnote", "deliverablenote", "metric",
)
_NATIVE: dict[str, dict[str, tuple[str, ...]]] = {
    "technical-report": {
        "callout": (*_CALLOUTS, "execsummary"),
        "figure": ("evidencestack", "reportcycle", "reporttimeline", "reportflow", "reportmatrix", "riskheatmap", "reportarchitecture", "reportroadmap"),
        "chart": ("bar_chart", "timeseries", "waterfall_chart", "scatter_plot", "timeline_chart", *_OPERATOR_CHARTS),
        "composition": ("algorithmblock", "codeblock", "outputblock", "diagram", "RKShortListing", *_IDENTITY_COMPOSITIONS, *_EXECUTION_COMPOSITIONS),
        "command": ("AlgorithmInput", "AlgorithmOutput", "RKLink", "maketitle", "step", "flowedge", "quadrant", "point", "event", *_IDENTITY_COMMANDS, *_EXECUTION_COMMANDS, *_REFERENCES_COMMANDS),
    },
    "equity-research": {
        "callout": ("researchproblem", "assumption", "redflag", "metric"),
        "figure": ("reportflow", "reportmatrix", "reporttimeline", "reportarchitecture"),
        "chart": ("bar_chart", "timeseries", "drawdown_chart", "risk_reward_chart", "scatter_plot", "waterfall_chart"),
        "composition": (
            "codeblock", "outputblock", "diagram", "researchfrontpage", "ratingstrip", "researchmain",
            "researchsidebar", "analystblock", "marketdatablock", "estimatesblock", "whatschanged",
            "financialmodelpage", "financialtable", "exhibit", "fullwidthexhibit", "exhibitgrid", "exhibitpair",
        ),
        "command": ("ratingitem", "sidebarrow", "change", "rkscenario", "bullcase", "basecase", "bearcase", "exhibitpane", *_REFERENCES_COMMANDS),
    },
    "executive-brief": {
        "callout": ("principle", "decisionpoint", "assumption", "redflag", "metric"),
        "figure": ("reportflow", "reportmatrix", "reporttimeline", "reportarchitecture"),
        "chart": ("bar_chart", "timeseries", "waterfall_chart", "timeline_chart"),
        "composition": (
            "codeblock", "outputblock", "diagram", "briefheader", "briefactions", "briefsources",
            "financialtable", "exhibit", "fullwidthexhibit", "exhibitgrid", "exhibitpair",
        ),
        "command": ("briefmeta", "briefaction", "exhibitpane", *_REFERENCES_COMMANDS),
    },
    "feature-article": {
        "figure": (),
        "chart": ("bar_chart", "timeseries", "waterfall_chart", "scatter_plot", "timeline_chart"),
        "composition": (
            "diagram", "featureopening", "openingvisual", "featurecolumns", "featuresidebar", "featureexhibit",
            "featuretable", "featurereferences",
        ),
        "command": (
            "RKLink", "step", "flowedge", "featureheadline", "featuredeck", "featurebyline", "imagecredit",
            "dropcap", "pullquote", "featuresection", *_REFERENCES_COMMANDS,
        ),
    },
    "book": {
        "figure": ("reportcycle", "reporttimeline", "reportflow", "reportmatrix", "reportarchitecture", "reportroadmap"),
        "chart": ("bar_chart", "timeseries", "waterfall_chart", "timeline_chart", *_OPERATOR_CHARTS),
        "composition": (
            "codeblock", "outputblock", "diagram", "RKShortListing", "bookdetails", "bookreferences", "bookglossary", *_IDENTITY_COMPOSITIONS, *_EXECUTION_COMPOSITIONS,
        ),
        "command": (
            "RKLink", "RKPath", "RKTitlePage", "step", "flowedge", "quadrant", "point", "event",
            "bookpart", "bookdetail", "bookappendix", "glossaryterm", *_IDENTITY_COMMANDS, *_EXECUTION_COMMANDS,
            *_REFERENCES_COMMANDS,
        ),
    },
    "presentation": {
        "chart": ("bar_chart", "timeseries", "waterfall_chart", "scatter_plot", "timeline_chart"),
        "composition": (
            "diagram", "titleslide", "sectiondivider", "appendixdivider", "messageslide", "assertionslide",
            "referenceslide", "agendaslide", "evidenceslide", "cardgrid", "visualtext", "chartslide", "tableslide", "fullvisual",
            "architectureslide", "comparison", "threepart", "herometric", "closingslide",
        ),
        "command": ("referenceitem", "carditem", "comparisoncolumn", "threepartcolumn", *_REFERENCES_COMMANDS),
    },
}
_ALLOWED: dict[str, dict[str, tuple[str, ...]]] = {
    "equity-research": {
        "chart": _OPERATOR_CHARTS,
        "composition": (*_IDENTITY_COMPOSITIONS, *_EXECUTION_COMPOSITIONS),
        "command": (*_IDENTITY_COMMANDS, *_EXECUTION_COMMANDS),
    },
    "executive-brief": {
        "chart": _OPERATOR_CHARTS,
        "composition": (*_IDENTITY_COMPOSITIONS, *_EXECUTION_COMPOSITIONS),
        "command": (*_IDENTITY_COMMANDS, *_EXECUTION_COMMANDS),
    },
    "feature-article": {
        "callout": _CALLOUTS,
        "figure": ("reportflow",),
        "chart": _NATIVE["feature-article"]["chart"],
        "composition": ("diagram", "featuretable"),
        "command": ("RKLink", "step", "flowedge"),
    },
    "book": {
        "callout": ROLE_TABLE["reportkit-boxes.sty"]["members"]["callout"],
    },
    "presentation": {
        "chart": _NATIVE["presentation"]["chart"],
        "composition": ("diagram",),
    },
}
_DISCOURAGED: dict[str, dict[str, tuple[str, ...]]] = {
    "feature-article": {"callout": ROLE_TABLE["reportkit-boxes.sty"]["members"]["callout"]},
}

for _family_name, _family_record in ROLE_TABLE.items():
    for _kind, _names in _family_record["members"].items():
        for _name in _names:
            _name_roles: dict[str, Role] = {target: "absent" for target in _PUBLICATION_TYPES}
            for _target, _kinds in _NATIVE.items():
                if _name in _kinds.get(_kind, ()):
                    _name_roles[_target] = "native"
            for _target, _kinds in _ALLOWED.items():
                if _name in _kinds.get(_kind, ()):
                    _name_roles[_target] = "allowed"
            for _target, _kinds in _DISCOURAGED.items():
                if _name in _kinds.get(_kind, ()):
                    _name_roles[_target] = "discouraged"
            _family_record["overrides"][_name] = _name_roles


_FAMILY_FOR: dict[tuple[str, str], str] = {}
_ROLES_FOR_NAME: dict[tuple[str, str], dict[str, Role]] = {}
for _family_name, _record in ROLE_TABLE.items():
    for _kind, _names in _record["members"].items():
        for _name in _names:
            _key = (_kind, _name)
            _FAMILY_FOR[_key] = _family_name
            _ROLES_FOR_NAME[_key] = dict(_record["roles"])
            _ROLES_FOR_NAME[_key].update(_record["overrides"].get(_name, {}))


def role_for(primitive_name: str, kind: str, publication_type: str) -> Role:
    """Return a primitive's reviewed role for a registered publication type.

    Unknown names and publication types fail closed as ``absent``. The family
    inventory is explicit so a new registry entry does not silently inherit an
    ``allowed`` role.
    """
    if publication_type not in PUBLICATION_TYPES:
        return "absent"
    return _ROLES_FOR_NAME.get((kind, primitive_name), {}).get(publication_type, "absent")


def targets_for(primitive_name: str, kind: str) -> dict[str, Role]:
    """Return the explicit reviewed role for every publication type."""
    return {
        publication_type: role_for(primitive_name, kind, publication_type)
        for publication_type in _PUBLICATION_TYPES
    }


def unmapped_primitives(registry: dict[str, Any]) -> list[str]:
    """Report registry primitives missing from the reviewed family inventory."""
    return sorted(
        f"{kind}:{name} ({record.get('source', {}).get('file', 'unknown source')})"
        for kind, records in registry.get("primitives", {}).items()
        for name, record in records.items()
        if (kind, name) not in _FAMILY_FOR
    )
