# -*- coding: utf-8 -*-
"""Formato plano: todos los campos de una actividad se completan en la misma fila."""
from collections import OrderedDict
from ckanext.theme_ejemplo import ihpix_bulk_schema as legacy
from ckanext.theme_ejemplo.ihpix_bulk_schema import (
    INDICATORS,
    INDICATOR_LABELS,
    LABELS,
    DATA_ROW,
    translator,
    label,
)


def _(text):
    return text


VERSION = "IHP-IX/3"
FLAT = True
COMMON = ()
GROUPS = [
    (_("Activity"), legacy.SHEETS["Activities"][1:]),
    (_("Reporting details"), legacy.SHEETS["Institutions"][1:]),
    (legacy.SHEET_LABELS["Scope"], legacy.SHEETS["Scope"][1:]),
] + [
    (INDICATOR_LABELS[code], tuple(fields.values()))
    for code, fields in INDICATORS.items()
]
SHEETS = OrderedDict(
    [
        ("Activities", tuple(field for _, fields in GROUPS for field in fields)),
        *[
            (key, legacy.SHEETS[key])
            for key in ("Contributions", "Supporters", "Partners", "Resources")
        ],
    ]
)
SHEET_LABELS = {
    key: legacy.SHEET_LABELS[key] for key in ("Start", *SHEETS, "Reference")
}
SHEET_LABELS["Start"] = _("Quick guide")
GUIDE = _(
    "One activity per row. Enter its details and indicators on this sheet. Leave unanswered fields blank."
)
EXTRA_GUIDE = _(
    "Optional. Choose the activity by its title. Use this sheet only for additional contributions, support, organizations or resources."
)

SHEET_LABELS.update(
    {
        "Contributions": _("Extra contributions"),
        "Supporters": _("Extra Member State support"),
        "Partners": _("Extra partner organizations"),
        "Resources": _("Extra resources"),
    }
)
