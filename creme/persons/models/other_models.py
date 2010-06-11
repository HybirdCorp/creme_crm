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

from django.db.models import Model, CharField, TextField, ManyToManyField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeModel

from media_managers.models import Image


class Civility(CremeModel):
    civility_name = CharField(_(u'Intitulé'), max_length=100)

    def __unicode__(self):
        return self.civility_name

    class Meta:
        app_label = "persons"
        verbose_name = _(u'Civilité')
        verbose_name_plural = _(u'Civilités')


class PeopleFunction(CremeModel):
    function_name = CharField(_(u'Intitulé'), max_length=100)

    def __unicode__(self):
        return self.function_name

    class Meta:
        app_label = "persons"
        verbose_name = _(u'Fonction de personne')
        verbose_name_plural = _(u'Fonctions des personnes')


class Sector(CremeModel):
    sector_name = CharField(_(u'Intitulé'), max_length=100)

    def __unicode__(self):
        return self.sector_name

    class Meta:
        app_label = "persons"
        verbose_name = _(u"Secteur d'activités")
        verbose_name_plural = _(u"Secteurs d'activités")


class LegalForm(CremeModel):
    legal_form_name = CharField(_(u'Intitulé'), max_length=100)

    def __unicode__(self):
        return self.legal_form_name

    class Meta:
        app_label = "persons"
        verbose_name = _(u'Forme juridique')
        verbose_name_plural = _(u'Formes juridiques')


class StaffSize(CremeModel):
    employees = CharField(_(u'Intitulé'), max_length=100)

    def __unicode__(self):
        return self.employees

    class Meta:
        app_label = "persons"
        verbose_name = _(u"Effectif d'organisation")
        verbose_name_plural = _(u"Effectifs d'organisations")


class MailSignature(CremeModel):
    sign_name = CharField(_(u'Nom de la signature'), max_length=100)
    corpse    = TextField(_(u'Corps'))
    images    = ManyToManyField(Image, verbose_name=_(u'Images de la signature'),
                           help_text=_(u'Les images incorporées aux mails et non pas en pièce jointe.'),
                           blank=True, null=True, related_name='MailSignatureImages_set')

    def __unicode__(self):
        return self.sign_name

    class Meta:
        app_label = "persons"
        verbose_name = _(u"Signature de mail")
        verbose_name_plural = _(u"Signatures de mail")
        ordering = ('sign_name',)
