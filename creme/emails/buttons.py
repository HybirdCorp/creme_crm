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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_link_perm
from creme.creme_core.gui.button_menu import Button

from . import constants, get_entityemail_model

EntityEmail = get_entityemail_model()


class EntityEmailLinkButton(Button):
    id_ = Button.generate_id('emails', 'entity_email_link')
    verbose_name = _('Link this email to')
    description = _(
        'This button links the current entity with a selected email, '
        'using a relationship type in:\n'
        ' - «sent the email».\n'
        ' - «received the email».\n'
        ' - «related to the email».\n'
        'App: Emails'
    )
    template_name = 'emails/buttons/entityemail-link.html'
    # permission = build_link_perm(EntityEmail)
    permissions = build_link_perm(EntityEmail)

    rtype_ids = [
        constants.REL_SUB_MAIL_SENDED,
        constants.REL_SUB_MAIL_RECEIVED,
        constants.REL_SUB_RELATED_TO,
    ]

    def get_ctypes(self):
        return (EntityEmail,)

    def render(self, context):
        context['rtypes'] = self.rtype_ids

        return super().render(context)
