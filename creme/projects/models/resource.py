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

from django.db.models import ForeignKey, PositiveIntegerField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity

from persons.models import Contact

from task import ProjectTask


class Resource(CremeEntity): #CremeModel instead ??
    linked_contact  = ForeignKey(Contact, verbose_name=_(u'Contact'))
    hourly_cost     = PositiveIntegerField(_(u'Hourly cost (in €)'), blank=True, null=True)
    task            = ForeignKey(ProjectTask, verbose_name=_(u'Task'), related_name='resources_set')

    class Meta:
        app_label = 'projects'
        verbose_name = _(u'Resource of project')
        verbose_name_plural = _(u'Resources of project')

    def __unicode__(self):
        return unicode(self.linked_contact)

    def get_absolute_url(self):
        return self.linked_contact.get_absolute_url()

    def get_edit_absolute_url(self):
        return "/projects/resource/edit/%s" % self.id

#Commented on 15 june 2010
#    def get_delete_absolute_url(self):
#        return "/projects/resource/delete/%s" % self.id

    def delete(self):
        # delete first all working period related to this resource (functionnal constraint)
        WorkingPeriod.objects.filter(task=self.task, resource=self).delete()
        super(Resource, self).delete()


from workingperiod import WorkingPeriod
