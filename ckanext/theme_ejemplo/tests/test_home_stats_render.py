"""La primera respuesta ya contiene los valores; no depende de JavaScript."""
from pathlib import Path
from types import SimpleNamespace
import re

from jinja2 import Environment


def test_home_counters_are_readable_without_javascript():
    template = Path(__file__).parents[1] / 'templates/home/snippets/site_stats_hero.html'
    env = Environment(extensions=['jinja2.ext.i18n'])
    env.install_null_translations()
    helpers = SimpleNamespace(
        theme_ejemplo_site_statistics=lambda: dict(organization_count=248, initiative_count=51,
            member_state_count=210, dataset_count=446, dataset_only_count=446, document_count=12),
        get_tracking_totals=lambda: dict(page_views=245001, downloads=0),
        localised_number=lambda n: format(n, ','), url_for=lambda *args, **kwargs: '/',
    )
    html = env.from_string(template.read_text()).render(h=helpers, _=lambda text: text)
    counters = re.findall(r'data-count-to="(\d+)">([^<]+)</span>', html)
    assert len(counters) == 6
    assert all(int(visible.replace(',', '')) == int(value) for value, visible in counters)
