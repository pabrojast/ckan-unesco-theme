"""El actor de las acciones IHP-IX: un anónimo recibe 403, no un error 500."""
import pytest

# ihpix_collaboration importa ckan.model y toolkit: sin CKAN (suite pura de
# Theme checks) el módulo se salta en vez de romper la recolección.
pytest.importorskip('ckan')

import ckan.plugins.toolkit as tk
from ckanext.theme_ejemplo import ihpix_collaboration as C


class Anonymous(object):
    """Como el AnonymousUser de Flask-Login: verdadero y sin `state`."""


def test_anonymous_user_is_not_authorized_instead_of_crashing():
    with pytest.raises(tk.NotAuthorized):
        C.user({'auth_user_obj': Anonymous(), 'user': ''})
