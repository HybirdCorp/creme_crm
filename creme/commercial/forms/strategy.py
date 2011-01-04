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

from django.utils.translation import ugettext_lazy as _
from django.forms import ModelMultipleChoiceField

from creme_core.models import CremePropertyType
from creme_core.forms import CremeForm, CremeModelForm, CremeEntityForm, MultiCremeEntityField
from creme_core.forms.widgets import UnorderedMultipleChoiceWidget

from persons.models import Organisation

from commercial.models import Strategy, MarketSegment, CommercialAsset, MarketSegmentCharm


class StrategyForm(CremeEntityForm):
    class Meta:
        model = Strategy
        exclude = CremeEntityForm.Meta.exclude + ('evaluated_orgas', 'segments')


class _SegmentForm(CremeModelForm):
    class Meta:
        model = MarketSegment
        fields = ('name',)


class SegmentEditForm(_SegmentForm):
    def save(self):
        segment = super(SegmentEditForm, self).save()

        ptype = segment.property_type
        ptype.text = MarketSegment.generate_property_text(segment.name)
        ptype.save()

        return segment


class SegmentCreateForm(_SegmentForm):
    def __init__(self, entity, *args, **kwargs):
        super(SegmentCreateForm, self).__init__(*args, **kwargs)
        self._strategy = entity

    def save(self):
        segment = self.instance

        # is_custom=False ==> CremePropertyType won't be deletable
        segment.property_type = CremePropertyType.create('commercial-segment',
                                                         MarketSegment.generate_property_text(self.cleaned_data['name']),
                                                         generate_pk=True,
                                                         is_custom=False
                                                        )
        super(SegmentCreateForm, self).save()

        self._strategy.segments.add(segment)

        return segment


class SegmentLinkForm(CremeForm):
    segments = ModelMultipleChoiceField(queryset=MarketSegment.objects.all(),
                                        label=_(u'Available segments'),
                                        widget=UnorderedMultipleChoiceWidget
                                       )

    def __init__(self, entity, *args, **kwargs):
        super(SegmentLinkForm, self).__init__(*args, **kwargs)
        self._strategy = entity

        self.fields['segments'].queryset = MarketSegment.objects.exclude(strategy=entity)

    def save(self):
        segments = self._strategy.segments

        for segment in self.cleaned_data['segments']:
            segments.add(segment)


class _AuxForm(CremeModelForm):
    class Meta:
        exclude = ('strategy',)

    def __init__(self, entity, *args, **kwargs):
        super(_AuxForm, self).__init__(*args, **kwargs)
        self._strategy = entity

    def save(self):
        self.instance.strategy = self._strategy
        return super(_AuxForm, self).save()


class AssetForm(_AuxForm):
    class Meta(_AuxForm.Meta):
        model = CommercialAsset


class CharmForm(_AuxForm):
    class Meta(_AuxForm.Meta):
        model = MarketSegmentCharm


class AddOrganisationForm(CremeForm):
    organisations = MultiCremeEntityField(label=_(u"Organisations"), model=Organisation)

    def __init__(self, entity, *args, **kwargs):
        super(AddOrganisationForm, self).__init__(*args, **kwargs)
        self._strategy = entity

    def save(self):
        eval_orgas = self._strategy.evaluated_orgas

        for orga in self.cleaned_data['organisations']:
            eval_orgas.add(orga)
