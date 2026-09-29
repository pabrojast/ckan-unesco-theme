"""Contrato del header efectivo: retorno CS opcional, sin alterar otros hubs."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode
from jinja2 import Environment


class CitizenScienceLoginHeaderTest(unittest.TestCase):
    def render_header(self, destination=None, plugin=True, user=None):
        source = (Path(__file__).parents[1] / 'templates/header.html').read_text()
        source = source.split('{% block header_account_notlogged %}', 1)[1].split('{% endblock %}', 1)[0]
        def url_for(endpoint, **kwargs):
            return '/user/' + endpoint.split('.')[-1] + ('?' + urlencode(kwargs) if kwargs else '')
        helpers = {'url_for': url_for}
        if plugin:
            helpers['csunesco_login_return_url'] = lambda: destination
        return Environment(autoescape=True).from_string(source).render(h=SimpleNamespace(**helpers), c=SimpleNamespace(userobj=user), _=lambda s: s)

    def test_cs_return_includes_page_and_query(self):
        html = self.render_header('/es/citizen-science/projects?q=river')
        self.assertIn('href="/user/login?came_from=%2Fes%2Fcitizen-science%2Fprojects%3Fq%3Driver"', html)

    def test_other_pages_keep_original_login(self):
        self.assertIn('href="/user/login"', self.render_header())

    def test_missing_cs_plugin_keeps_original_login(self):
        self.assertIn('href="/user/login"', self.render_header(plugin=False))

    def test_logged_in_users_keep_logout(self):
        self.assertIn('href="/user/logout"', self.render_header('/citizen-science/', user=object()))


if __name__ == '__main__':
    unittest.main()
