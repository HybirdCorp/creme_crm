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

import logging

from django.db.models import Model, CharField, ForeignKey, PositiveIntegerField
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType


#TODO : Fonctions unicode a lever / modifier

from creme_core.models import CremeModel

#todo comment trouver les models defini dans une app : 
#from django.db.models.loading import get_models
#from django.db.models.loading import get_app
#get_models (get_app ( "creme_core") )

class CremeTypeDroit(CremeModel):
    """ pour modeliser les type de droits ( dont le CRUD) sur les CremeEntity """
    name = CharField(_(u'Name'), max_length=100)

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return self.name


class CremeTypeEnsembleFiche(CremeModel):
    """
    de base :
    Ses Fiches ses_fiches
    Toutes les Fiches toutes_les_fiches
    Les Fiches d'une de ses equipes les_fiches_de_l_equipe
    Les Fiches de ses Subordonnées les_fiches_de_ses_subordonnees
    Les Fiches d'un role precis fiche_d_un_role
    Les Fiches d'un role precis ainsi que de ses subordonnées fiche_d_un_role_et_subordonnees
    Sa Fiche personne sa_fiche
    Les Autres Fiches les_autres_fiches
    Fiche Unique fiche_unique
    fiche en relation avec sa fiche fiche_en_rel_avec_sa_fiche
    """
    name = CharField(_(u'Name'), max_length=100)

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return self.name


class CremeDroitEntityType(CremeModel):
    """ la modélisation d'un droit . Cela contient le content type sur lequel le droit porte,
        le type de droit, l'ensemble de fiche ainsi que si necessaire l'id de la fiche, du role
        ou de l'equipe dont il est question.
    """
    content_type        = ForeignKey(ContentType, editable=False)
    type_droit          = ForeignKey(CremeTypeDroit, editable=False)
    type_ensemble_fiche = ForeignKey(CremeTypeEnsembleFiche, editable=False)

    id_fiche_role_ou_equipe = PositiveIntegerField( blank=True, null=True)

    research_fields = ['content_type__name', 'type_droit__name', 'type_ensemble_fiche__name', 'id_fiche_role_ou_equipe']

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return force_unicode('%s -> Droit de: %s, pour les fiches:%s, idFicheRole/Equipe:%s' % \
                                (self.content_type, self.type_droit, self.type_ensemble_fiche, self.id_fiche_role_ou_equipe))

    def get_entity_summary(self):
        return self.__unicode__()


class CremeAppTypeDroit(CremeModel):
    """ pour modeliser les type de droits (Est Admin et A Acces) sur les App """
    name = CharField(_(u'Name'), max_length=100)

    research_fields = ['name']

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return self.name

    def get_entity_summary(self):
        return self.__unicode__()


class CremeAppDroit(CremeModel):
    """ pour modeliser les droits  sur les App """
    type_droit = ForeignKey(CremeAppTypeDroit, editable=False)
    name_app   = CharField(max_length=100)

    research_fields = ['type_droit__name', 'name_app']

    class Meta:
        app_label = 'creme_core'

    def __unicode__(self):
        return u'Application: %s -> %s' % (unicode(self.name_app), unicode(self.type_droit))

    def get_entity_summary(self):
        return self.__unicode__()
