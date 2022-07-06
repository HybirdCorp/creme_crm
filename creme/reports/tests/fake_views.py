from creme.creme_core.views import generic

from ..tests import fake_models


class FakeReportsFolderDetail(generic.EntityDetail):
    model = fake_models.FakeReportsFolder
    pk_url_kwarg = 'folder_id'


class FakeReportsDocumentsList(generic.EntitiesList):
    model = fake_models.FakeReportsDocument
