# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

# import warnings

from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

# from creme.creme_core.auth import build_creation_perm as cperm
# from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import RelationType
from creme.creme_core.views import generic

from .. import get_contact_model, get_organisation_model
from ..constants import DEFAULT_HFILTER_CONTACT
from ..forms import contact as c_forms

Contact = get_contact_model()


# def abstract_add_contact(request, form=c_forms.ContactForm,
#                          template='persons/add_contact_form.html',
#                          submit_label=Contact.save_label,
#                         ):
#     warnings.warn('persons.views.contact.abstract_add_contact() is deprecated ; '
#                   'use the class-based view ContactCreation instead.',
#                   DeprecationWarning
#                  )
#     return generic.add_entity(request, form, template=template,
#                               extra_template_dict={'submit_label': submit_label},
#                              )


# def abstract_add_related_contact(request, orga_id, rtype_id,
#                                  form=c_forms.RelatedContactForm,
#                                  template='persons/add_contact_form.html',
#                                  submit_label=Contact.save_label,
#                                 ):
#     warnings.warn('persons.views.contact.abstract_add_related_contact() is deprecated ; '
#                   'use the class-based view RelatedContactCreation instead.',
#                   DeprecationWarning
#                  )
#
#     from django.utils.http import is_safe_url
#
#     user = request.user
#     linked_orga = get_object_or_404(get_organisation_model(), pk=orga_id)
#     user.has_perm_to_view_or_die(linked_orga)  # Displayed in the form....
#     user.has_perm_to_link_or_die(linked_orga)
#
#     user.has_perm_to_link_or_die(Contact)
#
#     initial = {'linked_orga': linked_orga}
#
#     if rtype_id:
#         rtype = get_object_or_404(RelationType, id=rtype_id)
#
#         if rtype.is_internal:
#             raise ConflictError('This RelationType cannot be used because it is internal.')
#
#         if not rtype.is_compatible(linked_orga.entity_type_id):
#             raise ConflictError('This RelationType is not compatible with Organisation as subject')
#
#         # todo: improve API of is_compatible
#         if not rtype.symmetric_type.is_compatible(ContentType.objects.get_for_model(Contact).id):
#             raise ConflictError('This RelationType is not compatible with Contact as relationship-object')
#
#         initial['relation_type'] = rtype.symmetric_type
#
#     redirect_to = request.POST.get('callback_url') or request.GET.get('callback_url')
#     redirect_to_is_safe = is_safe_url(
#         url=redirect_to,
#         allowed_hosts={request.get_host()},
#         require_https=request.is_secure(),
#     )
#
#     return generic.add_entity(request, form,
#                               url_redirect=redirect_to if redirect_to_is_safe else '',
#                               template=template, extra_initial=initial,
#                               extra_template_dict={'submit_label': submit_label},
#                              )


# def abstract_edit_contact(request, contact_id, form=c_forms.ContactForm,
#                           template='persons/edit_contact_form.html',
#                          ):
#     warnings.warn('persons.views.contact.abstract_edit_contact() is deprecated ; '
#                   'use the class-based view ContactEdition instead.',
#                   DeprecationWarning
#                  )
#     return generic.edit_entity(request, contact_id, model=Contact, edit_form=form, template=template)


# def abstract_view_contact(request, contact_id,
#                           template='persons/view_contact.html',
#                          ):
#     warnings.warn('persons.views.contact.abstract_view_contact() is deprecated ; '
#                   'use the class-based view ContactDetail instead.',
#                   DeprecationWarning
#                  )
#     return generic.view_entity(request, contact_id, model=Contact, template=template)


# @login_required
# @permission_required(('persons', cperm(Contact)))
# def add(request):
#     warnings.warn('persons.views.contact.add() is deprecated.', DeprecationWarning)
#     return abstract_add_contact(request)


# @login_required
# @permission_required(('persons', cperm(Contact)))
# def add_related_contact(request, orga_id, rtype_id=None):
#     warnings.warn('persons.views.contact.add_related_contact() is deprecated.', DeprecationWarning)
#     return abstract_add_related_contact(request, orga_id, rtype_id)


# @login_required
# @permission_required('persons')
# def edit(request, contact_id):
#     warnings.warn('persons.views.contact.edit() is deprecated.', DeprecationWarning)
#     return abstract_edit_contact(request, contact_id)


# @login_required
# @permission_required('persons')
# def detailview(request, contact_id):
#     warnings.warn('persons.views.contact.detailview() is deprecated.', DeprecationWarning)
#     return abstract_view_contact(request, contact_id)


# @login_required
# @permission_required('persons')
# def listview(request):
#     return generic.list_view(request, Contact, hf_pk=DEFAULT_HFILTER_CONTACT)

class _ContactBaseCreation(generic.EntityCreation):
    model = Contact
    form_class = c_forms.ContactForm
    template_name = 'persons/add_contact_form.html'


class ContactCreation(_ContactBaseCreation):
    pass


class RelatedContactCreation(_ContactBaseCreation):
    form_class = c_forms.RelatedContactForm
    title = _('Create a contact related to «{organisation}»')
    orga_id_url_kwarg = 'orga_id'
    rtype_id_url_kwarg = 'rtype_id'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.linked_orga = None

    def get(self, *args, **kwargs):
        self.linked_orga = self.get_linked_orga()
        return super().get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.linked_orga = self.get_linked_orga()
        return super().post(*args, **kwargs)

    def check_view_permissions(self, user):
        super(RelatedContactCreation, self).check_view_permissions(user=user)
        self.request.user.has_perm_to_link_or_die(Contact)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['linked_orga'] = self.linked_orga
        kwargs['rtype'] = self.get_rtype()

        return kwargs

    def get_linked_orga(self):
        orga = get_object_or_404(get_organisation_model(),
                                 id=self.kwargs[self.orga_id_url_kwarg],
                                )

        user = self.request.user
        user.has_perm_to_view_or_die(orga)  # Displayed in the form....
        user.has_perm_to_link_or_die(orga)

        return orga

    def get_rtype(self):
        rtype_id = self.kwargs.get(self.rtype_id_url_kwarg)

        if rtype_id:
            rtype = get_object_or_404(RelationType, id=rtype_id)

            if rtype.is_internal:
                raise ConflictError('This RelationType cannot be used because it is internal.')

            if not rtype.is_compatible(self.linked_orga.entity_type_id):
                raise ConflictError('This RelationType is not compatible with Organisation as subject')

            # TODO: improve API of is_compatible()
            if not rtype.symmetric_type.is_compatible(ContentType.objects.get_for_model(Contact).id):
                raise ConflictError('This RelationType is not compatible with Contact as relationship-object')

            return rtype.symmetric_type

    def get_success_url(self):
        return self.linked_orga.get_absolute_url()

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['organisation'] = self.linked_orga

        return data


class ContactDetail(generic.EntityDetail):
    model = Contact
    template_name = 'persons/view_contact.html'
    pk_url_kwarg = 'contact_id'


class ContactEdition(generic.EntityEdition):
    model = Contact
    form_class = c_forms.ContactForm
    template_name = 'persons/edit_contact_form.html'
    pk_url_kwarg = 'contact_id'


class ContactsList(generic.EntitiesList):
    model = Contact
    default_headerfilter_id = DEFAULT_HFILTER_CONTACT
