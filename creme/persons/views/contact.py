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

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from creme_core.views.generic import add_entity, edit_entity, view_entity_with_template, list_view
from creme_core.gui.last_viewed import change_page_for_last_item_viewed
from creme_core.entities_access.functions_for_permissions import add_view_or_die, get_view_or_die, read_object_or_die

from persons.models import Contact
from persons.forms.contact import ContactWithRelationForm, ContactCreateForm


@login_required
@get_view_or_die('persons')
@add_view_or_die(ContentType.objects.get_for_model(Contact), None, 'persons')
def add(request):
    return add_entity(request, ContactCreateForm, template="persons/add_contact_form.html")

@login_required
@get_view_or_die('persons')
@add_view_or_die(ContentType.objects.get_for_model(Contact), None, 'persons')
def add_with_relation(request, organisation_id):
    return add_entity(request,
                      ContactWithRelationForm,
                      request.REQUEST.get('callback_url'),
                      'persons/add_contact_form.html',
                      extra_initial={'organisation_id': organisation_id})

def edit(request, contact_id):
    return edit_entity(request, contact_id, Contact, ContactCreateForm, 'persons', template='persons/edit_contact_form.html')

@login_required
@get_view_or_die('persons')
def detailview(request, contact_id):
    return view_entity_with_template(request, contact_id, Contact, '/persons/contact', 'persons/view_contact.html')

@login_required
@get_view_or_die('persons')
@change_page_for_last_item_viewed #useful ????
def listview(request):
    return list_view(request, Contact, extra_dict={'add_url':'/persons/contact/add'})

#TODO: set the HF in the url ????
@login_required
@get_view_or_die('persons')
@change_page_for_last_item_viewed #useful ????
def list_my_leads_my_customers(request):
    #use a constant for 'persons-hf_leadcustomer' ??
    return list_view(request, Contact, hf_pk='persons-hf_leadcustomer', extra_dict={'list_title': 'Liste de mes suspects / prospects / clients'})
