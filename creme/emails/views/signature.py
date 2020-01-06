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

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from creme.creme_core.views import generic

from ..forms.signature import SignatureForm
from ..models import EmailSignature


class SignatureCreation(generic.CremeModelCreationPopup):
    model = EmailSignature
    form_class = SignatureForm
    permissions = 'emails'


class SignatureEdition(generic.CremeModelEditionPopup):
    model = EmailSignature
    form_class = SignatureForm
    pk_url_kwarg = 'signature_id'
    permissions = 'emails'

    def check_instance_permissions(self, instance, user):
        if not instance.can_change_or_delete(user):
            raise PermissionDenied(_('You can not edit this signature (not yours)'))


class SignatureDeletion(generic.CremeModelDeletion):
    model = EmailSignature
    permissions = 'emails'

    def check_instance_permissions(self, instance, user):
        if not instance.can_change_or_delete(user):
            raise PermissionDenied(_('You can not delete this signature (not yours)'))
