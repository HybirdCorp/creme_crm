# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2021  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse

from creme.creme_core.http import is_ajax
from creme.creme_core.models import CremeModel
from creme.creme_core.utils import get_from_POST_or_404

from .base import CheckedView


class CremeDeletion(CheckedView):
    def get_ajax_success_url(self):
        return ''

    def get_success_url(self):
        return reverse('creme_core__home')

    def post(self, request, *args, **kwargs):
        # TODO: <return self.delete(request, *args, **kwargs)> ?
        self.perform_deletion(self.request)

        return (
            HttpResponse(self.get_ajax_success_url(), content_type='text/plain')
            # if request.is_ajax() else
            if is_ajax(request) else
            HttpResponseRedirect(self.get_success_url())
        )

    def perform_deletion(self, request):
        raise NotImplementedError


class CremeModelDeletion(CremeDeletion):
    model = CremeModel
    pk_arg = 'id'

    def check_instance_permissions(self, instance, user):
        pass

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        instance = get_object_or_404(queryset, **self.get_query_kwargs())

        self.check_instance_permissions(instance=instance, user=self.request.user)

        return instance

    def get_query_kwargs(self):
        return {'pk': get_from_POST_or_404(self.request.POST, self.pk_arg)}

    def get_queryset(self):
        return self.model._default_manager.all()

    def perform_deletion(self, request):
        self.object = self.get_object()
        self.object.delete()
