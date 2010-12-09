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

from creme_core.forms import CremeForm, CremeModelForm, CremeEntityForm, MultiCremeEntityField

from persons.models import Organisation

from commercial.models import Strategy, MarketSegment, CommercialAsset, MarketSegmentCharm


class StrategyForm(CremeEntityForm):
    class Meta:
        model = Strategy
        exclude = CremeEntityForm.Meta.exclude + ('evaluated_orgas', )


class _AuxForm(CremeModelForm):
    class Meta:
        exclude = ('strategy')

    def __init__(self, entity, *args, **kwargs):
        super(_AuxForm, self).__init__(*args, **kwargs)
        self._strategy = entity

    def save(self):
        self.instance.strategy = self._strategy
        return super(_AuxForm, self).save()


class SegmentForm(_AuxForm):
    class Meta(_AuxForm.Meta):
        model = MarketSegment


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
