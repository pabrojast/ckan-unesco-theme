# -*- coding: utf-8 -*-
"""Presentación localizada de lotes, sin exponer JSON ni nombres internos."""
import re
from ckanext.theme_ejemplo import (
    ihpix_bulk_schema as S,
    ihpix_forms as F,
    ihpix_relations as R,
)
from ckanext.theme_ejemplo.ihpix_bulk_workbook import choices, choice_field


def present(batch, locale="en", organizations=(), page=1):
    tr = S.translator(locale)
    preview = batch["preview"]
    vocabulary = {
        field: dict(items)
        for field, items in choices(organizations, locale, tr).items()
    }

    def value_text(field, value):
        if isinstance(value, list):
            return "; ".join(value_text(field, v) for v in value)
        if isinstance(value, dict):
            return " · ".join(
                S.label(
                    (
                        "resource_" + k
                        if field == "links_json" and k in ("title", "description")
                        else k
                    ),
                    tr,
                )
                + ": "
                + value_text(k, v)
                for k, v in value.items()
                if v not in (None, "", [])
            )
        if field in F.BOOL_FIELDS and F._gate_answered(value):
            return (
                tr("Yes")
                if str(value).lower() in ("yes", "true", "1", "y", "on")
                else tr("No")
            )
        if field in ("country", "member_states", "supporting_member_state"):
            country = R.country_metadata(value)
            if country:
                return (
                    country.get("country_title_" + locale)
                    or country["country_title_en"]
                )
        if field in ("institution_org_id", "organization_id", "partner_org_ids"):
            return vocabulary.get("organization_id", {}).get(
                str(value), tr("IHP-WINS organization")
            )
        if field == "types":
            return tr(
                {
                    "financial": "Financial support",
                    "in_kind": "In-kind support",
                    "hosting": "Hosting support",
                }.get(str(value), str(value))
            )
        return vocabulary.get(choice_field(field), {}).get(str(value), tr(str(value)))

    def issue_text(issue):
        message = issue["message"]
        if message.startswith("Must be one of:"):
            return tr("Choose a value from Reference lists.")
        for pattern in F.MESSAGES.values():
            fields = re.findall(r"\{(\w+)\}", pattern)
            if not fields:
                continue
            regex = re.escape(pattern)
            for name in fields:
                regex = regex.replace(
                    re.escape("{" + name + "}"), "(?P<" + name + ">.*?)"
                )
            match = re.fullmatch(regex, message)
            if match:
                params = match.groupdict()
                if "field" in params:
                    params["field"] = S.label(params["field"], tr)
                return tr(pattern).format(**params)
        return tr(message)

    def issue_view(issue):
        issue = dict(issue)
        if not issue.get("ref"):
            for item in preview["rows"]:
                if issue["sheet"] == "Activities" and issue["row"] == item["row"]:
                    issue["ref"] = item["ref"]
                    break
                rows_key = {
                    "Resources": "resource_rows",
                    "Partners": "partner_rows",
                }.get(issue["sheet"])
                if rows_key and issue["row"] in item.get(rows_key, []):
                    issue["ref"] = item["ref"]
                    break
        return dict(
            issue,
            label=S.label(issue["field"].split(".")[0], tr),
            text=issue_text(issue),
        )

    errors = [issue_view(x) for x in preview.get("errors", [])]
    warnings = [issue_view(x) for x in preview.get("warnings", [])]
    total = len(preview["rows"])
    pages = max(1, (total + 19) // 20)
    try:
        page = max(1, min(pages, int(page)))
    except (ValueError, TypeError):
        page = 1
    rows = []
    for item in preview["rows"][(page - 1) * 20 : page * 20]:
        data = item["data"]
        sections = []

        def add_section(title, fields):
            values = []
            for field in fields:
                value = data.get(field)
                if value not in (None, "", []):
                    values.append(
                        {
                            "label": S.label(field, tr),
                            "value": value_text(field, value),
                            "source": item.get("sources", {}).get(field),
                        }
                    )
            if values:
                sections.append({"title": title, "fields": values})

        for key in ("Activities", "Institutions", "Scope"):
            add_section(
                tr(S.SHEET_LABELS[key]), [f for f in S.SHEETS[key] if f != "row_ref"]
            )
        for key, fields in S.INDICATORS.items():
            add_section(key + " · " + tr(S.INDICATOR_LABELS[key]), fields.values())
        add_section(tr("Additional details"), R.JSON_FIELDS + ("links_json",))
        rows.append(
            dict(
                item,
                sections=sections,
                errors=[e for e in errors if e.get("ref") == item["ref"]],
                warnings=[e for e in warnings if e.get("ref") == item["ref"]],
            )
        )
    known = {r["ref"] for r in preview["rows"]}
    return {
        "rows": rows,
        "errors": errors,
        "warnings": warnings,
        "general_errors": [e for e in errors if e.get("ref") not in known],
        "general_warnings": [e for e in warnings if e.get("ref") not in known],
        "incomplete": len({w.get("ref") for w in warnings if w.get("ref")}),
        "page": page,
        "pages": pages,
        "common": [
            {"label": S.label(field, tr), "value": value_text(field, val)}
            for field, val in preview.get("common", {}).items()
            if val not in (None, "", [])
        ],
        "example": preview.get("example", False),
    }
