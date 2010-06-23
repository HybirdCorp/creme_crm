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

from logging import debug

from django.db.models import Model, CharField, BooleanField, DateTimeField, PositiveIntegerField
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from creme_core.models import RelationType, Relation

from commercial.constants import REL_SUB_SOLD_BY


#TODO: to be tested (genglert: not used any more for now ; maybe broken after Relation refactoring....)

class SellByRelation(Relation):
    """Relation 'has sold / has been sold' between a salesman and an entity."""
    commission_paye = BooleanField (blank=True, default=False)
    int_value =       PositiveIntegerField( default=0)
    char_value =      CharField(max_length=100, blank=True)
    date_paiement =   DateTimeField(_(u'Date de paiement'), blank=True, null=True,)

    class Meta:
        app_label = "commercial"

    def __unicode__(self):
        commission_is_paid = 'Oui' if self.commission_paye else 'Non'

        subject = self.subject_entity
        object_ = self.object_entity

        str_ = '<a href="%s">%s</a> -- %s  --> <a href="%s">%s</a> commission payée: %s' % (
                        subject.get_absolute_url(), subject,
                        self.type,
                        object_.get_absolute_url(), object_,
                        commission_is_paid
                    )
        return force_unicode(str_)

    #def delete(self):
        #debug(' SellByRelation: delete_relation %s ', self.id)

        #sym_relation = self.symmetric_relation
        #sym_sellbyrelation = sym_relation.sellbyrelation if sym_relation is not None else None

        #try:
            #self.subject_creme_entity.new_relations.remove(self)
        #except:
            #pass
        #Model.delete(self) ##WTF ??!!!!!!

        #debug(' SellByRelation , aprés model.delete %s ', sym_sellbyrelation)

        #if sym_sellbyrelation is not None:
            #sym_sellbyrelation.symmetric_relation = None
            #super(SellByRelation, sym_sellbyrelation).save()
            #try:
                #sym_sellbyrelation.subject_creme_entity.new_relations.remove(sym_relation)
            #except Exception, e:
                #debug('Exception in SellByRelation.delete_relation(): %s', e)

            #sym_sellbyrelation.delete()

    def _build_symmetric_relation(self, update):
        if update:
            sym_relation = self.symmetric_relation
            assert sym_relation

            sym_relation.commission_paye = self.commission_paye
            sym_relation.int_value       = self.int_value
            sym_relation.char_value      = self.char_value
            sym_relation.date_paiement   = self.date_paiement
        else:
            sym_relation = SellByRelation(user=self.user,
                                          type=self.type.symmetric_type,
                                          symmetric_relation= self,
                                          subject_entity=self.object_entity,
                                          object_entity=self.subject_entity,
                                          commission_paye=self.commission_paye,
                                          int_value=self.int_value,
                                          char_value=self.char_value,
                                          date_paiement=self.date_paiement,
                                         )
        return sym_relation

    @staticmethod
    def create(subject, object_, commission_paye, int_value=0, char_value=""):
        relation = SellByRelation()
        relation.user = User.objects.get(pk=1) #hum....
        relation.type_id = REL_SUB_SOLD_BY
        relation.subject_entity = subject
        relation.object_entity = object_
        relation.commission_paye = commission_paye 
        relation.int_value = int_value
        relation.char_value = char_value

        relation.save()
