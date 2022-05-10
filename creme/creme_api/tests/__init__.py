from django.test import TestCase

from .test_addresses import *  # noqa
from .test_authentication import *  # noqa
from .test_civilities import *  # noqa
from .test_contacts import *  # noqa
from .test_contenttypes import *  # noqa
from .test_credentials import *  # noqa
from .test_documentation import *  # noqa
from .test_legal_forms import *  # noqa
from .test_models import *  # noqa
from .test_positions import *  # noqa
from .test_roles import *  # noqa
from .test_sectors import *  # noqa
from .test_staff_sizes import *  # noqa
from .test_teams import *  # noqa
from .test_tokens import *  # noqa
from .test_users import *  # noqa
from .utils import *  # noqa

from creme.creme_api.api.routes import router


class CollectionTestCase(TestCase):
    def test_all_routes_covered(self):
        expected_tests = {
            (pattern.name, action)
            for pattern in router.get_urls()
            for action in pattern.callback.actions
        }
        found_tests = {
            (obj.url_name, obj.method)
            for obj in globals().values()
            if isinstance(obj, type) and issubclass(obj, CremeAPITestCase)
        }
        missing = expected_tests - found_tests
        if missing:
            msg = (
                f"Missing tests for routes:\n"
                + "\n".join(f"{action.upper()}\t{url}" for url, action in sorted(missing)))
            self.fail(msg)
