# -*- coding: utf-8 -*-
"""Esquema de presentación XLSX; las claves estables no dependen del idioma."""
from collections import OrderedDict
from pathlib import Path
import gettext

VERSION = "IHP-IX/2"
DATA_ROW = 5
COMMON = (
    "focal_point_name",
    "contact_email",
    "institution",
    "institution_org_id",
    "institution_type",
    "institution_type_other",
    "country",
    "biennium",
)
SHEETS = OrderedDict(
    [
        (
            "Activities",
            (
                "row_ref",
                "title",
                "start_date",
                "end_date",
                "description",
                "outcomes",
                "priority_area",
                "output",
                "key_activity_code",
                "key_activity",
                "link",
            ),
        ),
        (
            "Institutions",
            ("row_ref",) + COMMON + ("partners", "unesco_secretariat_participation"),
        ),
        (
            "Scope",
            (
                "row_ref",
                "has_member_state_support",
                "supporting_member_state",
                "has_flagship",
                "flagships",
                "cross_cutting_wg",
                "has_synergies",
                "synergies",
                "regions_benefit",
                "regions",
                "member_states",
                "additional_notes",
                "image_url",
            ),
        ),
        (
            "Indicators",
            (
                "row_ref",
                "indicator",
                "answer",
                "quantity",
                "youth",
                "female",
                "types",
                "other",
                "group_names",
            ),
        ),
        (
            "Contributions",
            ("row_ref", "relation", "priority_area", "output", "key_activity_code"),
        ),
        ("Supporters", ("row_ref", "country", "financial", "in_kind", "hosting")),
        ("Partners", ("row_ref", "organization_id")),
        (
            "Resources",
            (
                "row_ref",
                "link_type",
                "title",
                "url",
                "description",
                "event_date",
                "target_kind",
                "target_id",
            ),
        ),
    ]
)
# Cada indicador se conserva en los campos originales del formulario.
INDICATORS = OrderedDict(
    [
        (
            "1a",
            {
                "answer": "kpi_1a_active",
                "quantity": "num_knowledge_products",
                "types": "knowledge_product_type",
                "other": "knowledge_product_type_other",
            },
        ),
        (
            "1b",
            {
                "answer": "kpi_1b_active",
                "quantity": "num_scientific_products",
                "types": "scientific_product_type",
            },
        ),
        (
            "2",
            {
                "answer": "kpi_2_active",
                "quantity": "stakeholders_knowledge",
                "youth": "stakeholders_knowledge_youth",
                "female": "stakeholders_knowledge_female",
                "types": "knowledge_activity_type",
                "other": "knowledge_activity_type_other",
            },
        ),
        (
            "3",
            {
                "answer": "kpi_3_active",
                "quantity": "num_training_materials",
                "types": "training_type",
                "other": "training_type_other",
            },
        ),
        ("4", {"answer": "kpi_4_active", "quantity": "num_curricula"}),
        (
            "5",
            {
                "answer": "kpi_5_active",
                "quantity": "stakeholders_awareness",
                "youth": "stakeholders_awareness_youth",
                "female": "stakeholders_awareness_female",
            },
        ),
        ("6", {"answer": "kpi_6_active", "quantity": "num_transboundary_ms"}),
        (
            "8",
            {
                "answer": "kpi_8_active",
                "quantity": "num_stakeholder_groups",
                "types": "stakeholder_group_type",
                "other": "stakeholder_group_type_other",
                "group_names": "stakeholder_group_name",
            },
        ),
    ]
)


# _() permite extraer estos textos con Babel sin importar CKAN.
def _(text):
    return text


SHEET_LABELS = {
    "Start": _("Start here"),
    "Activities": _("Activities"),
    "Institutions": _("Institutions"),
    "Scope": _("Participation and scope"),
    "Indicators": _("Indicators"),
    "Contributions": _("Contributions and synergies"),
    "Supporters": _("Member State support"),
    "Partners": _("Partner organizations"),
    "Resources": _("Publications and resources"),
    "Reference": _("Reference lists"),
}
LABELS = {
    "yesno": _("Yes or no"),
    "resource_title": _("Resource title"),
    "resource_description": _("Resource description"),
    "row_ref": _("Activity reference"),
    "title": _("Activity title"),
    "start_date": _("Start date"),
    "end_date": _("Completion date"),
    "description": _("Brief description"),
    "outcomes": _("Key outputs and outcomes"),
    "priority_area": _("Priority Area"),
    "output": _("Output"),
    "key_activity_code": _("Key activity"),
    "key_activity": _("Contribution to the key activity"),
    "link": _("Link to the activity"),
    "focal_point_name": _("Focal point"),
    "contact_email": _("Email address of the focal point"),
    "institution": _("Institution name"),
    "institution_org_id": _("IHP-WINS organization"),
    "institution_type": _("Institution category"),
    "institution_type_other": _("Other institution category"),
    "country": _("Country"),
    "biennium": _("Biennium"),
    "partners": _("Other partners"),
    "unesco_secretariat_participation": _("UNESCO Secretariat participation"),
    "has_member_state_support": _("Was there Member State support?"),
    "supporting_member_state": _("Primary supporting Member State"),
    "has_flagship": _("Linked to a flagship initiative?"),
    "flagships": _("Flagship initiatives"),
    "cross_cutting_wg": _("Cross-cutting working groups"),
    "has_synergies": _("Were there synergies?"),
    "synergies": _("Describe the synergies"),
    "regions_benefit": _("Did countries or regions benefit?"),
    "regions": _("Beneficiary regions"),
    "member_states": _("Beneficiary Member States"),
    "additional_notes": _("Additional notes"),
    "image_url": _("Image URL"),
    "indicator": _("Indicator"),
    "answer": _("Yes or no"),
    "quantity": _("Total"),
    "youth": _("Of which youth (18–35 years old)"),
    "female": _("Of which female participants"),
    "types": _("Types (separate with ;)"),
    "other": _("Describe Other"),
    "group_names": _("Names of stakeholder groups"),
    "relation": _("Relationship"),
    "financial": _("Financial support"),
    "in_kind": _("In-kind support"),
    "hosting": _("Hosting support"),
    "organization_id": _("Partner organization"),
    "link_type": _("Resource type"),
    "url": _("Web address"),
    "event_date": _("Event date"),
    "target_kind": _("Existing resource source"),
    "target_id": _("Existing resource identifier"),
}
INDICATOR_LABELS = {
    "1a": _("Knowledge products"),
    "1b": _("Scientific products"),
    "2": _("Knowledge improvement"),
    "3": _("Training materials and courses"),
    "4": _("Curricula"),
    "5": _("Awareness raising"),
    "6": _("Transboundary Member States supported"),
    "8": _("Stakeholder groups supported"),
}
for key, fields in INDICATORS.items():
    for column, field in fields.items():
        LABELS[field] = INDICATOR_LABELS[key] + " — " + LABELS[column]
LABELS.update(
    {
        "contributions_json": SHEET_LABELS["Contributions"],
        "synergies_json": _("Synergies"),
        "supporters_json": SHEET_LABELS["Supporters"],
        "partner_org_ids": SHEET_LABELS["Partners"],
        "links_json": SHEET_LABELS["Resources"],
    }
)


def translator(locale="en"):
    locale = locale if locale in ("en", "es", "fr", "ar") else "en"
    return gettext.translation(
        "ckanext-theme_ejemplo",
        localedir=str(Path(__file__).parent / "i18n"),
        languages=[locale],
        fallback=True,
    ).gettext


def label(field, translate=lambda s: s):
    for key, fields in INDICATORS.items():
        for column, target in fields.items():
            if target == field:
                return (
                    translate(INDICATOR_LABELS[key]) + " — " + translate(LABELS[column])
                )
    return translate(LABELS.get(field, field))
