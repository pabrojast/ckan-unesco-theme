"""Regresiones de autoría y editorial en la plantilla de citación del tema."""

import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader

from ckanext.doi.lib.helpers import (
    get_citation_publisher,
    package_get_year,
    parse_json_authors,
)


@pytest.fixture
def render():
    env = Environment(loader=FileSystemLoader(
        Path(__file__).resolve().parents[1] / 'templates'), autoescape=True)
    template = env.get_template('doi/snippets/package_citation.html')
    helpers = SimpleNamespace(
        doi_get_citation_publisher=get_citation_publisher,
        package_get_year=package_get_year,
        parse_json_authors=parse_json_authors,
    )

    def render_citation(**values):
        record = dict(id='citation-test', name='citation-test', type='documents',
                      title='Water study', metadata_created='2026-09-10T00:00:00',
                      publication_year='2020', doi_publisher='IHP-WINS',
                      doi_date_published='2026-09-10', doi_status=True,
                      custom_doi='https://doi.org/10.1234/external',
                      authors_json=[{'name': 'Author supplied'}])
        record.update(values)
        return template.render(pkg_dict=record, h=helpers, _=lambda text: text)

    return render_citation


@pytest.mark.parametrize('kind', ['dataset', 'documents'])
@pytest.mark.parametrize('author_field', ['authors', 'authors_json', 'author'])
@pytest.mark.parametrize('publisher', ['Publisher supplied', ''])
def test_preserves_authors_year_and_publisher(render, kind, author_field, publisher):
    values = dict(type=kind, authors_json=None, publisher_name=publisher)
    values[author_field] = 'Author supplied' if author_field == 'author' else [{'name': 'Author supplied'}]
    rendered = render(**values)
    assert 'Author supplied' in rendered
    assert '(2020)' in rendered
    assert 'IHP-WINS' not in rendered
    assert ('Publisher supplied' in rendered) == bool(publisher)
    assert ('[Document]' if kind == 'documents' else '[Data set]') in rendered


@pytest.mark.parametrize('field', ['custom_citation', 'citation'])
def test_respects_existing_citation(render, field):
    text = 'Author supplied. Intentionally credited IHP-WINS.'
    rendered = render(**{field: text})
    citation = re.search(r'id="citation-string"[^>]*>(.*?)</div>', rendered, re.S)[1]
    assert citation.strip() == text


def test_manual_citation_takes_precedence(render):
    rendered = render(custom_citation='Manual citation', citation='Automatic citation')
    assert 'Manual citation' in rendered
    assert 'Automatic citation' not in rendered


def test_native_doi_keeps_publisher(render):
    rendered = render(custom_doi='', doi='10.1234/internal', publisher_name='Publisher supplied')
    assert 'IHP-WINS' in rendered
    assert 'Publisher supplied' not in rendered
