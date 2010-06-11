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

from django.forms import ModelForm, CharField

from creme_core.forms.fields import MultiCremeEntityField
from creme_core.forms.widgets import RTEWidget

from persons.models.other_models import MailSignature

from media_managers.models.image import Image
from media_managers.forms.widgets import ImageM2MWidget


class MailSignatureForm(ModelForm):
    corpse = CharField(widget=RTEWidget())
    images = MultiCremeEntityField(required=False, model=Image,
                                   widget=ImageM2MWidget())

    #def __init__(self, *args, **kwargs):
        #super(MailSignatureForm, self).__init__(*args, **kwargs)

    class Meta:
        model = MailSignature