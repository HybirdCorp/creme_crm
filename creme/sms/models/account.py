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

from django.db.models import CharField, IntegerField
from django.utils.translation import ugettext as _

from creme_core.models import CremeModel

from sms.webservice.samoussa import SamoussaBackEnd
from sms.webservice.backend import WSException


class SMSAccount(CremeModel):
    class Meta:
        app_label = "sms"
        verbose_name = _(u'Compte plateforme SMS')
        verbose_name_plural = _(u'Compte plateforme SMS')

    excluded_fields_in_html_output = ['id']

    name        = CharField(_(u'Nom'), max_length=200, null=True)
    credit      = IntegerField(_(u'Crédit'), null=True)
    groupname   = CharField(_(u'Groupe'), max_length=200, null=True)
    
    
    def __unicode__(self):
        return self.name
    
    def sync(self):
        ws = SamoussaBackEnd()
        
        try:
            ws.connect()
            res = ws.get_account()
            
            parent = res.get('parent', {})
            
            self.name = res.get('name', self.name)
            self.credit = int(res.get('credit', '0')) + int(parent.get('credit', '0'))
            self.groupname = parent.get('name', '')
            self.save()
            
            ws.close()
        except WSException:
            pass

        return self