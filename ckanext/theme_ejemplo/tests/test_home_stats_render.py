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
            member_state_count=210, dataset_count=446, dataset_only_count=446, document_count=12,
            user_count=1310, news_count=37),
        get_tracking_totals=lambda: dict(page_views=245001, downloads=0),
        localised_number=lambda n: format(n, ','), url_for=lambda *args, **kwargs: '/',
    )
    html = env.from_string(template.read_text()).render(h=helpers, _=lambda text: text)
    counters = re.findall(r'data-count-to="(\d+)">([^<]+)</span>', html)
    assert len(counters) == 8
    assert ('1310', '1,310') in counters and ('37', '37') in counters
    assert all(int(visible.replace(',', '')) == int(value) for value, visible in counters)


def test_users_and_news_cards_are_left_out_when_their_count_is_unknown():
    template = Path(__file__).parents[1] / 'templates/home/snippets/site_stats_hero.html'
    env = Environment(extensions=['jinja2.ext.i18n'])
    env.install_null_translations()
    helpers = SimpleNamespace(
        theme_ejemplo_site_statistics=lambda: dict(organization_count=248, initiative_count=51,
            member_state_count=210, dataset_count=446, dataset_only_count=446, document_count=12,
            news_count=0),
        get_tracking_totals=lambda: dict(page_views=245001, downloads=0),
        localised_number=lambda n: format(n, ','), url_for=lambda *args, **kwargs: '/',
    )
    html = env.from_string(template.read_text()).render(h=helpers, _=lambda text: text)
    assert len(re.findall(r'data-count-to="(\d+)"', html)) == 6
    assert 'fa-newspaper' not in html and 'fa-user"' not in html
