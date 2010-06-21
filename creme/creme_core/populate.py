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

from django.utils.translation import ugettext as _

from creme_core.models import *
from creme_core.models.relation import create_relation_type
from creme_core.utils import create_or_update_models_instance as create
from creme_core.constants import PROP_IS_MANAGED_BY_CREME, REL_SUB_RELATED_TO, REL_OBJ_RELATED_TO, REL_SUB_HAS, REL_OBJ_HAS
from creme_core.management.commands.creme_populate import BasePopulator
from creme_core.pop_data.populate_data import set_up as set_up_credentials #TODO: remove


class Populator(BasePopulator):
    def populate(self, *args, **kwargs):
        create(FilterType,  1, name=_(u'Est égal à'),                                       pattern_key='%s__exact',        pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType,  2, name=_(u'Est égal à (Ne respecte pas la casse)'),            pattern_key='%s__iexact',       pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType,  3, name=_(u"N'est pas égal à"),                                 pattern_key='%s__exact',        pattern_value='%s', is_exclude=True , type_champ="CharField", value_field_type='textfield')
        create(FilterType,  4, name=_(u"N'est pas égal à (Ne respecte pas la casse)"),      pattern_key='%s__iexact',       pattern_value='%s', is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType,  5, name=_(u"Contient"),                                         pattern_key='%s__contains',     pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType,  6, name=_(u"Contient (Ne respecte pas la casse)"),              pattern_key='%s__icontains',    pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType,  7, name=_(u"Ne contient pas"),                                  pattern_key='%s__contains',     pattern_value='%s', is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType,  8, name=_(u"Ne contient pas (Ne respecte pas la casse)"),       pattern_key='%s__icontains',    pattern_value='%s', is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType,  9, name=_(u">"),                                                pattern_key='%s__gt',           pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 10, name=_(u">="),                                               pattern_key='%s__gte',          pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 11, name=_(u"<"),                                                pattern_key='%s__lt',           pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 12, name=_(u"<="),                                               pattern_key='%s__lte',          pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 13, name=_(u"Commence par"),                                     pattern_key='%s__startswith',   pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 14, name=_(u"Commence par (Ne respecte pas la casse)"),          pattern_key='%s__istartswith',  pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 15, name=_(u"Ne commence pas par"),                              pattern_key='%s__startswith',   pattern_value='%s', is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType, 16, name=_(u"Ne commence pas par (Ne respecte pas la casse)"),   pattern_key='%s__istartswith',  pattern_value='%s', is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType, 17, name=_(u"Se termine par"),                                   pattern_key='%s__endswith',     pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 18, name=_(u"Se termine par (Ne respecte pas la casse)"),        pattern_key='%s__iendswith',    pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 19, name=_(u"Ne se termine pas par"),                            pattern_key='%s__endswith',     pattern_value='%s', is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType, 20, name=_(u"Ne se termine pas par (Ne respecte pas la casse)"), pattern_key='%s__iendswith',    pattern_value='%s', is_exclude=True,  type_champ="CharField", value_field_type='textfield')
        create(FilterType, 21, name=_(u"Est vide"),                                         pattern_key='%s__isnull',       pattern_value='%s', is_exclude=False, type_champ="CharField", value_field_type='textfield')
        create(FilterType, 22, name=_(u"N'est pas vide"),                                   pattern_key='%s__isnull',       pattern_value='%s', is_exclude=True,  type_champ="CharField", value_field_type='textfield')

        create(CremeTypeDroit, 1, name=_(u"Lire"))
        create(CremeTypeDroit, 2, name=_(u"Créer"))
        create(CremeTypeDroit, 3, name=_(u"Modifier"))
        create(CremeTypeDroit, 4, name=_(u"Supprimer"))
        create(CremeTypeDroit, 5, name=_(u"Mettre en relation avec"))

        create(CremeTypeEnsembleFiche,  1, name=_(u"Ses fiches"))
        create(CremeTypeEnsembleFiche,  2, name=_(u"Toutes les fiches"))
        create(CremeTypeEnsembleFiche,  3, name=_(u"Les fiches de l'équipe"))
        create(CremeTypeEnsembleFiche,  4, name=_(u"Les fiches de ses subordonnés"))
        create(CremeTypeEnsembleFiche,  5, name=_(u"Les fiches d'un rôle"))
        create(CremeTypeEnsembleFiche,  6, name=_(u"Les fiches d'un rôle et de ses subordonnés"))
        create(CremeTypeEnsembleFiche,  7, name=_(u"Sa fiche"))
        create(CremeTypeEnsembleFiche,  8, name=_(u"Les autres fiches"))
        create(CremeTypeEnsembleFiche,  9, name=_(u"Fiche unique"))
        create(CremeTypeEnsembleFiche, 10, name=_(u"Fiches en relation avec sa fiche"))

        create(CremeAppTypeDroit, 1, name=_(u"Est administrateur"))
        create(CremeAppTypeDroit, 2, name=_(u"A accès"))

        create(Language, 1, name=_(u'Français'), code='FRA')
        create(Language, 2, name=_(u'Anglais'),  code='EN')

        CremePropertyType.create(PROP_IS_MANAGED_BY_CREME, u'est géré par Creme')

        create_relation_type((REL_SUB_RELATED_TO, u'est en relation avec'),
                             (REL_OBJ_RELATED_TO, u'est en relation avec'))
        create_relation_type((REL_SUB_HAS, u'possède'),
                             (REL_OBJ_HAS, u'appartient à'))

        set_up_credentials()