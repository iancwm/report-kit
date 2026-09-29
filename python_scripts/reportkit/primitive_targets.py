"""Reviewed primitive roles by publication target (agent reasoning loop spec §4.5)."""
from __future__ import annotations

from typing import Any, Literal

from .publications import PUBLICATION_TYPES

Role = Literal["native", "allowed", "discouraged", "absent"]
ROLES: tuple[str, ...] = ("native", "allowed", "discouraged", "absent")


def _target_roles(default: Role = "absent", **roles: Role) -> dict[str, Role]:
    """Return one explicit role for every registered publication type."""
    unknown = set(roles) - set(PUBLICATION_TYPES)
    if unknown:
        raise ValueError(f"unknown publication type in role table: {sorted(unknown)[0]}")
    result = {publication_type: default for publication_type in PUBLICATION_TYPES}
    result.update(roles)
    return result


# Families follow the source module (.sty for TeX, chart module for Python).
# The defaults keep target slices small; deliberate exceptions live in the
# per-name override table below. Every family carries all six explicit roles.
_FAMILY_MEMBERS: dict[str, dict[str, frozenset[str]]] = {
    "charts/composition": {"chart": frozenset("donut_chart waterfall_chart treemap_chart tornado_chart".split())},
    "charts/relationships": {"chart": frozenset("bar_chart distribution scatter_plot heatmap bubble_matrix".split())},
    "charts/timeseries": {"chart": frozenset("timeseries drawdown_chart risk_reward_chart timeline_chart".split())},
    "reportkit-algorithm-dp": {
        "command": frozenset("dpcell currentcell dependencycell solvedcell".split()),
        "figure": frozenset({"dptable"}),
    },
    "reportkit-algorithm-graph": {
        "command": frozenset("graphnode graphedge gridcell dagnode dependency readyqueue".split()),
        "figure": frozenset("graphstate gridstate dagstate".split()),
    },
    "reportkit-algorithm-linear": {
        "command": frozenset("push enqueue".split()),
        "figure": frozenset("stackstate queuestate".split()),
    },
    "reportkit-algorithm-order": {
        "command": frozenset("interval merged current".split()),
        "figure": frozenset("intervalstate heapstate".split()),
    },
    "reportkit-algorithm-p3": {
        "command": frozenset("joininput hashbucket joinmatch joinunmatched joinoutput ufnode parent union findpath listnode nextlink head tail recursionnode recursionedge".split()),
        "figure": frozenset("joinstate unionfindstate linkedliststate recursiontree".split()),
    },
    "reportkit-algorithm-viz": {
        "command": frozenset("cell row pointer range annotation values window entering leaving snapshot tracetransition".split()),
        "figure": frozenset("arraystate windowstate algorithmtrace".split()),
    },
    "reportkit-algorithms": {
        "command": frozenset("AlgorithmInput AlgorithmOutput".split()),
        "composition": frozenset({"algorithmblock"}),
    },
    "reportkit-book": {
        "command": frozenset("bookpart bookdetail bookappendix glossaryterm".split()),
        "composition": frozenset("bookdetails bookreferences bookglossary".split()),
    },
    "reportkit-boxes": {
        "callout": frozenset("principle decisionpoint researchproblem assumption redflag evidencenote limitationnote tipnote deliverablenote evidence limitation tip metric".split()),
    },
    "reportkit-code": {"composition": frozenset("codeblock outputblock".split())},
    "reportkit-core": {"command": frozenset("RKLink RKDiagramSection RKDiagramSubsection".split())},
    "reportkit-diagrams": {
        "command": frozenset("RKNode RKNodeRel RKEdge RKMatrixSetup RKMatrix RKMatrixCell RKSwimlaneSetup RKLane RKLaneNode RKLayerSetup RKLayer RKStackSetup RKStackTier RKCycleSetup RKCycleNode RKCycleEdge RKFunnelSetup RKFunnelStage evidencetier cyclestage cycleedge funnelstage".split()),
        "composition": frozenset({"diagram"}),
        "figure": frozenset("evidencestack reportcycle reportfunnel".split()),
    },
    "reportkit-equity-research": {
        "command": frozenset("ratingitem sidebarrow change rkscenario bullcase basecase bearcase".split()),
        "composition": frozenset("researchfrontpage ratingstrip researchmain researchsidebar analystblock marketdatablock estimatesblock whatschanged financialmodelpage".split()),
    },
    "reportkit-executive-brief": {
        "command": frozenset("briefmeta briefaction".split()),
        "composition": frozenset("briefheader briefactions briefsources".split()),
    },
    "reportkit-exhibits": {
        "command": frozenset({"exhibitpane"}),
        "composition": frozenset("financialtable exhibit fullwidthexhibit exhibitgrid exhibitpair".split()),
    },
    "reportkit-feature-article": {
        "command": frozenset("featureheadline featuredeck featurebyline imagecredit dropcap pullquote featuresection".split()),
        "composition": frozenset("featureopening openingvisual featurecolumns featuresidebar featureexhibit featuretable featurereferences".split()),
    },
    "reportkit-grammar": {
        "command": frozenset("state terminalstate stateat terminalstateat transition selfloop panel panelitem transformarrow event skewarrow watermark".split()),
        "figure": frozenset("reportstate reportcompare reporttimeline".split()),
    },
    "reportkit-longform": {
        "command": frozenset("RKTitlePage RKPath".split()),
        "composition": frozenset({"RKShortListing"}),
    },
    "reportkit-presentation": {
        "command": frozenset("referenceitem carditem comparisoncolumn threepartcolumn".split()),
        "composition": frozenset("titleslide sectiondivider appendixdivider messageslide assertionslide referenceslide evidenceslide cardgrid visualtext chartslide tableslide fullvisual architectureslide comparison threepart herometric closingslide".split()),
    },
    "reportkit-process": {
        "command": frozenset("step stepat flowedge branch merge lanestep handoff laneflow networknode networkedge causalnode causaledge".split()),
        "figure": frozenset("reportflow reportswimlane reportnetwork causalloop".split()),
    },
    "reportkit-spatial": {
        "command": frozenset("quadrant point risk".split()),
        "figure": frozenset("reportmatrix riskheatmap".split()),
    },
    "reportkit-structure": {
        "figure": frozenset("reportarchitecture reportroadmap strategicpillars maturitymodel continuum capabilitymap reporttree".split()),
    },
    "reportkit-theme-default": {"callout": frozenset({"execsummary"})},
    "reportkit-class": {"command": frozenset({"maketitle"})},
}

ROLE_TABLE: dict[str, Any] = {
    "charts/composition": {"members": _FAMILY_MEMBERS["charts/composition"], "roles": _target_roles(), "overrides": {}},
    "charts/relationships": {"members": _FAMILY_MEMBERS["charts/relationships"], "roles": _target_roles(), "overrides": {}},
    "charts/timeseries": {"members": _FAMILY_MEMBERS["charts/timeseries"], "roles": _target_roles(), "overrides": {}},
    "reportkit-algorithm-dp": {"members": _FAMILY_MEMBERS["reportkit-algorithm-dp"], "roles": _target_roles(), "overrides": {}},
    "reportkit-algorithm-graph": {"members": _FAMILY_MEMBERS["reportkit-algorithm-graph"], "roles": _target_roles(), "overrides": {}},
    "reportkit-algorithm-linear": {"members": _FAMILY_MEMBERS["reportkit-algorithm-linear"], "roles": _target_roles(), "overrides": {}},
    "reportkit-algorithm-order": {"members": _FAMILY_MEMBERS["reportkit-algorithm-order"], "roles": _target_roles(), "overrides": {}},
    "reportkit-algorithm-p3": {"members": _FAMILY_MEMBERS["reportkit-algorithm-p3"], "roles": _target_roles(), "overrides": {}},
    "reportkit-algorithm-viz": {"members": _FAMILY_MEMBERS["reportkit-algorithm-viz"], "roles": _target_roles(), "overrides": {}},
    "reportkit-algorithms": {"members": _FAMILY_MEMBERS["reportkit-algorithms"], "roles": _target_roles(**{"technical-report": "native"}), "overrides": {}},
    "reportkit-book": {"members": _FAMILY_MEMBERS["reportkit-book"], "roles": _target_roles(book="native"), "overrides": {}},
    "reportkit-boxes": {"members": _FAMILY_MEMBERS["reportkit-boxes"], "roles": _target_roles(book="allowed", **{"technical-report": "native", "equity-research": "allowed", "executive-brief": "allowed", "feature-article": "discouraged"}), "overrides": {}},
    "reportkit-code": {"members": _FAMILY_MEMBERS["reportkit-code"], "roles": _target_roles(**{"technical-report": "native"}), "overrides": {}},
    "reportkit-core": {"members": _FAMILY_MEMBERS["reportkit-core"], "roles": _target_roles(**{"technical-report": "allowed"}), "overrides": {}},
    "reportkit-diagrams": {"members": _FAMILY_MEMBERS["reportkit-diagrams"], "roles": _target_roles(), "overrides": {}},
    "reportkit-equity-research": {"members": _FAMILY_MEMBERS["reportkit-equity-research"], "roles": _target_roles(**{"equity-research": "native"}), "overrides": {}},
    "reportkit-executive-brief": {"members": _FAMILY_MEMBERS["reportkit-executive-brief"], "roles": _target_roles(**{"executive-brief": "native"}), "overrides": {}},
    "reportkit-exhibits": {"members": _FAMILY_MEMBERS["reportkit-exhibits"], "roles": _target_roles(**{"equity-research": "native", "executive-brief": "native"}), "overrides": {}},
    "reportkit-feature-article": {"members": _FAMILY_MEMBERS["reportkit-feature-article"], "roles": _target_roles(**{"feature-article": "native"}), "overrides": {}},
    "reportkit-grammar": {"members": _FAMILY_MEMBERS["reportkit-grammar"], "roles": _target_roles(), "overrides": {}},
    "reportkit-longform": {"members": _FAMILY_MEMBERS["reportkit-longform"], "roles": _target_roles(), "overrides": {}},
    "reportkit-presentation": {"members": _FAMILY_MEMBERS["reportkit-presentation"], "roles": _target_roles(presentation="native"), "overrides": {}},
    "reportkit-process": {"members": _FAMILY_MEMBERS["reportkit-process"], "roles": _target_roles(), "overrides": {}},
    "reportkit-spatial": {"members": _FAMILY_MEMBERS["reportkit-spatial"], "roles": _target_roles(), "overrides": {}},
    "reportkit-structure": {"members": _FAMILY_MEMBERS["reportkit-structure"], "roles": _target_roles(), "overrides": {}},
    "reportkit-theme-default": {"members": _FAMILY_MEMBERS["reportkit-theme-default"], "roles": _target_roles(), "overrides": {}},
    "reportkit-class": {"members": _FAMILY_MEMBERS["reportkit-class"], "roles": _target_roles(**{"technical-report": "native"}), "overrides": {}},
}


def _set_override(kind: str, name: str, **roles: Role) -> None:
    key = (kind, name)
    family = next((family for family, members in _FAMILY_MEMBERS.items() if name in members.get(kind, frozenset())), None)
    if family is None:
        raise KeyError(f"primitive override {kind}:{name} has no source family")
    merged = ROLE_TABLE[family]["overrides"].setdefault(key, dict(ROLE_TABLE[family]["roles"]))
    for publication_type, role in roles.items():
        if publication_type not in PUBLICATION_TYPES:
            raise ValueError(f"unknown publication type in role override: {publication_type!r}")
        merged[publication_type] = role


# The class entry point is public authoring syntax but is outside the .sty
# registry scan. Keep it explicit: only the generic technical report uses it.
_set_override("command", "maketitle", **{"technical-report": "native"})
_set_override("callout", "execsummary", **{
    "technical-report": "native", "equity-research": "allowed", "feature-article": "discouraged",
})
_set_override("composition", "RKShortListing", **{"technical-report": "native"})
_set_override("command", "RKTitlePage", book="native")
_set_override("command", "RKPath", book="native")
_set_override("composition", "featuretable", **{"feature-article": "allowed"})
_set_override("composition", "diagram", **{"technical-report": "native", "feature-article": "allowed"})
_set_override("command", "RKDiagramSection", **{"technical-report": "absent"})
_set_override("command", "RKDiagramSubsection", **{"technical-report": "absent"})
_set_override("command", "step", **{"technical-report": "allowed", "feature-article": "allowed"})
_set_override("command", "flowedge", **{"technical-report": "allowed", "feature-article": "allowed"})
_set_override("figure", "dptable", **{"technical-report": "native"})
_set_override("figure", "graphstate", **{"technical-report": "allowed"})

# Native or curated high-level diagram roles. Low-level drawing commands stay
# out of target slices unless a canonical example uses them directly.
for _name in ("reportflow", "reportmatrix", "reporttimeline", "reportcycle"):
    _set_override("figure", _name, **{"technical-report": "native"})
for _name in ("reportflow", "reportcycle"):
    _set_override("figure", _name, **{"feature-article": "allowed"})
for _name in ("reportflow", "reportcycle"):
    _set_override("figure", _name, book="allowed")
for _name in ("reportmatrix", "riskheatmap"):
    _set_override("figure", _name, **{"equity-research": "allowed"})
for _name in ("reportflow", "reporttimeline"):
    _set_override("figure", _name, **{"executive-brief": "allowed"})

# A chart slice is a concise, editorially useful sampler for each target.
_CHARTS_BY_TARGET = {
    "technical-report": ("bar_chart", "timeseries", "distribution"),
    "equity-research": ("bar_chart", "risk_reward_chart"),
    "executive-brief": ("bar_chart", "timeseries"),
    "feature-article": ("donut_chart", "timeseries"),
    "book": ("bar_chart",),
    "presentation": ("bar_chart",),
}
for _publication_type, _names in _CHARTS_BY_TARGET.items():
    for _name in _names:
        _set_override("chart", _name, **{_publication_type: "allowed"})

# Callouts stay available as a small semantic set on report targets. Feature
# articles explicitly discourage the report-style callout grammar.
_CALLOUTS_BY_TARGET = {
    "technical-report": ("principle", "decisionpoint", "limitationnote"),
    "equity-research": ("decisionpoint", "metric"),
    "executive-brief": ("decisionpoint", "metric", "limitationnote"),
}
for _name in _FAMILY_MEMBERS["reportkit-boxes"]["callout"]:
    _set_override("callout", _name, **{
        publication_type: ("allowed" if _name in selected else "absent")
        for publication_type, selected in _CALLOUTS_BY_TARGET.items()
    }, **{"feature-article": "discouraged"})

_NAME_TO_FAMILY: dict[tuple[str, str], str] = {}
for _family, _record in ROLE_TABLE.items():
    for _kind, _names in _record["members"].items():
        for _name in _names:
            _key = (_kind, _name)
            if _key in _NAME_TO_FAMILY:
                raise RuntimeError(f"primitive {_key!r} belongs to multiple source families")
            _NAME_TO_FAMILY[_key] = _family


def role_for(primitive_name: str, kind: str, publication_type: str) -> Role:
    """Return a primitive's explicitly reviewed role for one publication type."""
    if publication_type not in PUBLICATION_TYPES:
        raise ValueError(f"unknown publication type {publication_type!r}")
    family = _NAME_TO_FAMILY.get((kind, primitive_name))
    if family is None:
        raise KeyError(f"primitive {kind}:{primitive_name} has no explicit source-family role")
    override = ROLE_TABLE[family]["overrides"].get((kind, primitive_name))
    if override is not None:
        return override[publication_type]
    return ROLE_TABLE[family]["roles"][publication_type]
