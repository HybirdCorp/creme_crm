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

from django.forms.utils import ValidationError
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.models import CremePropertyType

from ..models import MarketSegment


#TODO: save/check unicity only if name has changed
class MarketSegmentForm(CremeModelForm):
    error_messages = {
        'duplicated_name':     _(u'A segment with this name already exists'),
        'duplicated_property': _(u'A property with the name «%(name)s» already exists'),
    }

    class Meta:
        model = MarketSegment
        fields = '__all__'

    # TODO: move to MarketSegment.clean() [but the error would be global, & not for 'name' field]
    def clean_name(self):
        name = self.cleaned_data['name']
        ptype_text = MarketSegment.generate_property_text(name)

        instance = self.instance
        segments = MarketSegment.objects.filter(name=name)
        ptypes   = CremePropertyType.objects.filter(text=ptype_text)

        if instance.pk:
            segments = segments.exclude(pk=instance.pk)
            ptypes   = ptypes.exclude(pk=instance.property_type_id)

        if segments.exists():
            raise ValidationError(self.error_messages['duplicated_name'],
                                  code='duplicated_name',
                                 )


        if ptypes.exists():
            raise ValidationError(self.error_messages['duplicated_property'],
                                  params={'name': ptype_text},
                                  code='duplicated_property',
                                 )

        self.ptype_text = ptype_text

        return name

    def save(self, *args, **kwargs):
        instance = self.instance

        # TODO: move to MarketSegment.save() ?
        if instance.pk: #edition
            ptype = instance.property_type
            ptype.text = self.ptype_text
            ptype.save()
        else:
            # is_custom=False ==> CremePropertyType won't be deletable
            instance.property_type = CremePropertyType.create('commercial-segment',
                                                              self.ptype_text,
                                                              generate_pk=True,
                                                              is_custom=False,
                                                             )

        return super(MarketSegmentForm, self).save(*args, **kwargs)
