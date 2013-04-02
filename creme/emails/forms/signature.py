# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

#from django.forms import CharField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.fields import MultiCremeEntityField

from creme.media_managers.models.image import Image
from creme.media_managers.forms.widgets import ImageM2MWidget

from ..models import EmailSignature


class SignatureForm(CremeModelForm):
    #body   = CharField(label=_(u'Body')) #TODO: Use a rich text editor which works with innerpopup
    images = MultiCremeEntityField(label=_(u'Images'), model=Image, required=False, widget=ImageM2MWidget,
                                   help_text=_(u'Images embedded in emails (but not as attached).'))

    class Meta:
        model = EmailSignature
        exclude = ('user',)

    def save(self, *args, **kwargs):
        self.instance.user = self.user
        return super(SignatureForm, self).save(*args, **kwargs)
