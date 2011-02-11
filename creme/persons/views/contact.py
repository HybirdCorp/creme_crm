# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from logging import debug

from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.models import RelationType
from creme_core.views.generic import add_entity, edit_entity, view_entity, list_view

from persons.models import Contact, Organisation
from persons.forms.contact import ContactWithRelationForm, ContactForm


@login_required
@permission_required('persons')
@permission_required('persons.add_contact')
def add(request):
    return add_entity(request, ContactForm, template="persons/add_contact_form.html")

@login_required
@permission_required('persons')
@permission_required('persons.add_contact')
def add_with_relation(request, orga_id, predicate_id=None):
    user = request.user
    linked_orga = get_object_or_404(Organisation, pk=orga_id)
    linked_orga.can_link_or_die(user)
    linked_orga.can_view_or_die(user) #displayed in the form....

    initial = {'linked_orga': linked_orga}

    if predicate_id:
        rtype = get_object_or_404(RelationType, symmetric_type=predicate_id)
        initial.update(relation_type=rtype) #TODO: inline ,??

    return add_entity(request, ContactWithRelationForm,
                      request.REQUEST.get('callback_url'), #TODO: request.GET ??
                      'persons/add_contact_form.html', extra_initial=initial
                     )

@login_required
@permission_required('persons')
def edit(request, contact_id):
    return edit_entity(request, contact_id, Contact, ContactForm, template='persons/edit_contact_form.html')

@login_required
@permission_required('persons')
def detailview(request, contact_id):
    return view_entity(request, contact_id, Contact, '/persons/contact', 'persons/view_contact.html')

@login_required
@permission_required('persons')
def listview(request):
    return list_view(request, Contact, extra_dict={'add_url': '/persons/contact/add'})
