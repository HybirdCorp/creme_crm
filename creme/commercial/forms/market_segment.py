# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from creme_core.models import CremePropertyType
from creme_core.forms import CremeModelForm

from commercial.models import MarketSegment


class MarketSegmentForm(CremeModelForm):
    class Meta:
        model = MarketSegment
        exclude = ('property_type',)

    def save(self, *args, **kwargs):
        instance = self.instance

        # is_custom=False ==> CremePropertyType won't be deletable
        instance.property_type = CremePropertyType.create('commercial-segment',
                                                           MarketSegment.generate_property_text(instance.name),
                                                           generate_pk=True,
                                                           is_custom=False
                                                          )
        super(MarketSegmentForm, self).save(*args, **kwargs)
