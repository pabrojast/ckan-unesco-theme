"""Contrato entre el formulario de revision y su controlador Flask."""
import ast
from pathlib import Path
import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('operation', ['approve', 'reject'])
def test_review_screen_passes_report_identity_to_action(operation):
    template = (ROOT / 'templates/admin/ihpix_reports.html').read_text()
    field = re.search(r"formData\.append\('([^']+)', reportId\)", template).group(1)
    controller = ast.parse((ROOT / 'controller.py').read_text())
    handler = next(node for node in ast.walk(controller)
                   if isinstance(node, ast.FunctionDef)
                   and node.name == 'ihpix_report_review_admin')
    handler.decorator_list = []
    review = Mock(return_value={'id': 'qa-report'})
    toolkit = SimpleNamespace(check_access=Mock(), get_action=Mock(return_value=review))
    namespace = dict(toolkit=toolkit, c=SimpleNamespace(user='ckan_admin'), model=object(),
                     request=SimpleNamespace(form={field: 'qa-report', 'action': operation,
                                                   'review_notes': 'QA review'}),
                     jsonify=lambda value: value)
    exec(compile(ast.Module(body=[handler], type_ignores=[]), 'review-controller', 'exec'), namespace)
    result = namespace['ihpix_report_review_admin']()
    assert result['success'] is True
    assert review.call_args.args[1] == {
        'id': 'qa-report', 'action': operation, 'review_notes': 'QA review',
    }
