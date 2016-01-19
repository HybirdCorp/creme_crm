# -*- coding: utf-8 -*-

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import view_entity, list_view

from ..tests import fake_models


@login_required
@permission_required('reports')
def folder_detailview(request, folder_id):
    return view_entity(request, folder_id, fake_models.FakeReportsFolder)


@login_required
@permission_required('reports')
def document_listview(request):
    return list_view(request, fake_models.FakeReportsDocument)
