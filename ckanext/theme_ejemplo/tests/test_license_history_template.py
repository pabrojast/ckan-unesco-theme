from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup


@pytest.fixture
def render():
    env = Environment(loader=FileSystemLoader(
        Path(__file__).resolve().parents[1] / 'templates' / 'overrides'), autoescape=True)
    template = env.get_template('snippets/changes/license.html')

    def render_change(**values):
        change = dict(pkg_id='example', title='Dataset', old_title='Old',
                      new_title='New', old_url='', new_url='')
        change.update(values)
        return template.render(change=change, _=lambda text: Markup(text),
                               h=SimpleNamespace(url_for=lambda *a, **k: '/dataset/example'))
    return render_change


@pytest.mark.parametrize('old_title,new_title', [
    ('Other (Open)', None), (None, 'New'), (None, None), ('', ''), ('Old', 'New')])
@pytest.mark.parametrize('old_url,new_url', [
    ('', ''), (None, None), ('https://old.example', ''),
    ('', 'https://new.example'), ('https://old.example', 'https://new.example')])
def test_license_history_handles_missing_values(render, old_title, new_title, old_url, new_url):
    html = render(old_title=old_title, new_title=new_title, old_url=old_url, new_url=new_url)
    assert (old_title or 'Unknown license') in html
    assert (new_title or 'Unknown license') in html
    assert 'None' not in html
    assert html.count('<a ') == 1 + bool(old_url) + bool(new_url)
    assert html.count('</a>') == html.count('<a ')


def test_license_history_escapes_titles_and_url_attributes(render):
    html = render(title='<script>bad()</script>', new_title='<b>unsafe</b>',
                  old_title='<img src=x>', new_url='https://license.example/" onclick="bad()')
    assert '<script>' not in html and '<b>' not in html and '<img ' not in html
    assert '&lt;b&gt;unsafe&lt;/b&gt;' in html
    assert '" onclick="' not in html
