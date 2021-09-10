# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from typing import List, Type, Union

from django.forms.forms import BaseForm
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template import Context, Template
from django.utils.decorators import method_decorator
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views.decorators.clickjacking import xframe_options_sameorigin

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.custom_form import CustomFormDescriptor
from creme.creme_core.models import RelationType
from creme.creme_core.shortcuts import get_bulk_or_404
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.utils.html import sanitize_html
from creme.creme_core.views import generic
from creme.creme_core.views.generic.base import EntityRelatedMixin
from creme.creme_core.views.relation import RelationsAdding

from .. import bricks, constants, get_entityemail_model
from ..forms import mail as mail_forms
from ..models import LightWeightEmail
from ..models.template import body_validator

EntityEmail = get_entityemail_model()


class EntityEmailCreation(generic.AddingInstanceToEntityPopup):
    model = EntityEmail
    form_class = mail_forms.EntityEmailForm
    template_name = 'creme_core/generics/blockform/link-popup.html'
    permissions = ['emails', cperm(EntityEmail)]
    title = _('Sending an email to «{entity}»')
    submit_label = EntityEmail.sending_label

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)


class EntityEmailWizard(EntityRelatedMixin, generic.EntityCreationWizardPopup):
    model = EntityEmail
    form_list: List[Union[Type[BaseForm], CustomFormDescriptor]] = [
        mail_forms.TemplateSelectionFormStep,
        mail_forms.EntityEmailForm,
    ]
    title = _('Sending an email to «{entity}»')
    submit_label = _('Send the email')

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)
        user.has_perm_to_link_or_die(entity)

    def done_save(self, form_list):
        for form in form_list:
            form.save()

    def get_form_initial(self, step):
        initial = super().get_form_initial(step=step)

        if step == '1':
            email_template = self.get_cleaned_data_for_step('0')['template']
            ctx = {
                var_name: getattr(self.get_related_entity(), var_name, '')
                # for var_name in TEMPLATES_VARS
                for var_name in body_validator.allowed_variables
            }
            initial['subject'] = email_template.subject
            initial['body'] = Template(email_template.body).render(Context(ctx))
            initial['body_html'] = Template(email_template.body_html).render(Context(ctx))
            initial['signature'] = email_template.signature_id
            initial['attachments'] = [
                *email_template.attachments.values_list('id', flat=True)
            ]  # TODO: test

        return initial

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        entity = self.get_related_entity()

        if step == '1':
            kwargs['entity'] = entity

        return kwargs

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['entity'] = self.get_related_entity()

        return data


class EntityEmailDetail(generic.EntityDetail):
    model = EntityEmail
    template_name = 'emails/view_entity_mail.html'
    pk_url_kwarg = 'mail_id'


class EntityEmailPopup(generic.EntityDetailPopup):
    model = EntityEmail
    pk_url_kwarg = 'mail_id'
    title = _('Details of the email')

    def get_brick_ids(self):
        return (
            bricks.MailPopupBrick.id_,
        )


class EntityEmailsList(generic.EntitiesList):
    model = EntityEmail
    default_headerfilter_id = constants.DEFAULT_HFILTER_EMAIL


class EntityEmailLinking(RelationsAdding):
    title = _('Link «{entity}» to emails')

    def get_relation_types(self):
        subject = self.get_related_entity()
        subject_ctype = subject.entity_type
        rtypes = []
        subjects_prop_ids = None  # TODO: lazy object

        for rtype in RelationType.objects.filter(id__in=bricks.MailsHistoryBrick
                                                              .relation_type_deps):
            if not rtype.is_compatible(subject_ctype):
                continue

            # TODO: unit test
            # TODO: factorise with RelationsAdding
            needed_property_types = [*rtype.subject_properties.all()]
            if needed_property_types:
                if subjects_prop_ids is None:
                    subjects_prop_ids = {*subject.properties.values_list('type', flat=True)}

                if any(
                    needed_ptype.id not in subjects_prop_ids
                    for needed_ptype in needed_property_types
                ):
                    continue

            rtypes.append(rtype.id)

        # TODO: unit test
        if not rtypes:
            raise ConflictError(gettext('No type of relationship is compatible.'))

        return rtypes


class EntityEmailsResending(generic.CheckedView):
    permissions = 'emails'
    model = EntityEmail
    email_ids_arg = 'ids'

    def get_email_ids(self, request):
        try:
            return [
                int(s)
                for s in get_from_POST_or_404(request.POST, self.email_ids_arg).split(',')
                if s.strip()
            ]
        except ValueError as e:
            raise ConflictError(str(e)) from e

    def post(self, request, *args, **kwargs):
        ids = self.get_email_ids(request)

        if ids:
            for email in get_bulk_or_404(self.model, ids).values():
                email.send()

        return HttpResponse()


# TODO: disable the link in the template if view is not allowed
class LightWeightEmailPopup(generic.RelatedToEntityDetailPopup):
    model = LightWeightEmail
    pk_url_kwarg = 'mail_id'
    permissions = 'emails'
    title = _('Details of the email')

    def get_brick_ids(self):
        return (
            bricks.LwMailPopupBrick.id_,
        )


@method_decorator(xframe_options_sameorigin, name='dispatch')
class LightWeightEmailBody(generic.CheckedView):
    """Used to show an HTML document in an <iframe>."""
    permissions = 'emails'
    model = LightWeightEmail
    mail_id_url_kwarg = 'mail_id'

    def check_email_permissions(self, email, user):
        user.has_perm_to_view_or_die(email.sending.campaign)

    def get_email(self):
        email = get_object_or_404(self.model, pk=self.kwargs['mail_id'])
        self.check_email_permissions(email, self.request.user)

        return email

    def get(self, *args, **kwargs):
        email = self.get_email()

        return HttpResponse(sanitize_html(
            email.rendered_body_html,
            # TODO: ? allow_external_img=request.GET.get('external_img', False),
            allow_external_img=True,
        ))
