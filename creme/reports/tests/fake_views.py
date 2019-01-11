# -*- coding: utf-8 -*-

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views import generic

from ..tests import fake_models


class FakeReportsFolderDetail(generic.EntityDetail):
    model = fake_models.FakeReportsFolder
    pk_url_kwarg = 'folder_id'


@login_required
@permission_required('reports')
def document_listview(request):
    return generic.list_view(request, fake_models.FakeReportsDocument)
