from unittest import skipIf

from creme.creme_core.models import Job
from creme.creme_core.tests.base import CremeTestCase

from .. import get_rgenerator_model, rgenerator_model_is_custom
from ..creme_jobs import recurrents_gendocs_type

skip_generator_tests = rgenerator_model_is_custom()

RecurrentGenerator = get_rgenerator_model()
# CTYPE_KEY = '0-cform_extra-recurrents_ctype'


def skipIfCustomGenerator(test_func):
    return skipIf(skip_generator_tests, 'Custom generator model in use')(test_func)


class RecurrentsTestCase(CremeTestCase):
    CTYPE_KEY = '0-cform_extra-recurrents_ctype'

    def _get_job(self):
        return self.get_object_or_fail(Job, type_id=recurrents_gendocs_type.id)

    def _generate_docs(self, job=None):
        recurrents_gendocs_type.execute(job or self._get_job())
