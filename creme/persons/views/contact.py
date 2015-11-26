# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.contrib.contenttypes.models import ContentType
# from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import RelationType
from creme.creme_core.views.generic import add_entity, edit_entity, view_entity, list_view

from .. import get_contact_model, get_organisation_model
from ..constants import DEFAULT_HFILTER_CONTACT
#from ..models import Contact, Organisation
from ..forms.contact import RelatedContactForm, ContactForm


Contact = get_contact_model()


def abstract_add_contact(request, form=ContactForm,
                         template='persons/add_contact_form.html',
                         submit_label=_('Save the contact'),
                        ):
    return add_entity(request, form, template=template,
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_add_related_contact(request, orga_id, rtype_id,
                                 form=RelatedContactForm,
                                 template='persons/add_contact_form.html',
                                 submit_label=_('Save the contact'),
                                ):
    user = request.user
#    linked_orga = get_object_or_404(Organisation, pk=orga_id)
    linked_orga = get_object_or_404(get_organisation_model(), pk=orga_id)
    user.has_perm_to_link_or_die(linked_orga)
    user.has_perm_to_view_or_die(linked_orga)  # Displayed in the form....

    user.has_perm_to_link_or_die(Contact)

    initial = {'linked_orga': linked_orga}

#    if predicate_id:
#        initial['relation_type'] = get_object_or_404(RelationType, symmetric_type=predicate_id)
    if rtype_id:
        rtype = get_object_or_404(RelationType, id=rtype_id)

        if rtype.is_internal:
            raise ConflictError('This RelationType cannot be used because it is internal.')

        if not rtype.is_compatible(linked_orga.entity_type_id):
            raise ConflictError('This RelationType is not compatible with Organisation as subject')

        if not rtype.symmetric_type.is_compatible(ContentType.objects.get_for_model(Contact).id): #TODO: improve API of is_compatible
            raise ConflictError('This RelationType is not compatible with Contact as relationship-object')

        initial['relation_type'] = rtype.symmetric_type

#    return add_entity(request, RelatedContactForm,
    return add_entity(request, form,
#                      request.REQUEST.get('callback_url'),
                      url_redirect=request.POST.get('callback_url') or
                                   request.GET.get('callback_url'),
                      template=template, extra_initial=initial,
                      extra_template_dict={'submit_label': submit_label},
                     )


def abstract_edit_contact(request, contact_id, form=ContactForm,
                          template='persons/edit_contact_form.html',
                         ):
    return edit_entity(request, contact_id, model=Contact, edit_form=form, template=template)


def abstract_view_contact(request, contact_id,
                          template='persons/view_contact.html',
                         ):
    return view_entity(request, contact_id, model=Contact, template=template,
                       # path='/persons/contact',
                      )


@login_required
# @permission_required(('persons', 'persons.add_contact'))
@permission_required(('persons', cperm(Contact)))
def add(request):
    return abstract_add_contact(request)


@login_required
# @permission_required(('persons', 'persons.add_contact'))
@permission_required(('persons', cperm(Contact)))
#def add_with_relation(request, orga_id, predicate_id=None):
def add_related_contact(request, orga_id, rtype_id=None):
    return abstract_add_related_contact(request, orga_id, rtype_id)


@login_required
@permission_required('persons')
def edit(request, contact_id):
    return abstract_edit_contact(request, contact_id)


@login_required
@permission_required('persons')
def detailview(request, contact_id):
    return abstract_view_contact(request, contact_id)


@login_required
@permission_required('persons')
def listview(request):
#    return list_view(request, Contact, extra_dict={'add_url': '/persons/contact/add'})
    return list_view(request, Contact,
                     hf_pk=DEFAULT_HFILTER_CONTACT,
                     # extra_dict={'add_url': reverse('persons__create_contact')},
                    )
