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

from django.db.models import CharField, ManyToManyField
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from creme_core.models import CremeEntity, RelationType, Relation


class Graph(CremeEntity):
    name           = CharField(_(u'Name of the graph'), max_length=100)
    subjects       = ManyToManyField(CremeEntity, verbose_name=_(u'Subjects'), related_name='graphs_set')
    relation_types = ManyToManyField(RelationType, verbose_name=_(u'Types of relation'))

    class Meta:
        app_label = 'graphs'
        verbose_name = _(u'Graph')
        verbose_name_plural = _(u'Graphs')

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/graphs/graph/%s" % self.id

    def get_edit_absolute_url(self):
        return "/graphs/graph/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        return "/graphs/graphs"

    def get_delete_absolute_url(self):
        return "/graphs/graph/delete/%s" % self.id

    def generate_png(self):
        from os.path import join, exists
        from os import makedirs

        import pygraphviz as pgv

        graph = pgv.AGraph(directed=True)

        #subjects_id = []
        subjects = self.subjects.all()
        add_node = graph.add_node
        add_edge = graph.add_edge

        #todo: entity cache ?? ....

        #for subject in self.subjects.all():
        for subject in subjects:
            #subjects_id.append(subject.id)
            add_node(unicode(subject.get_real_entity()), shape='box')
            #add_node('filled box',     shape='box',     style='filled',  color='#FF00FF')
            #add_node('filled box v2',  shape='box',     style='filled',  fillcolor='#FF0000', color='#0000FF', penwidth='2.0') #default pensize="1.0"

        #for relation in Relation.objects.filter(type__in=self.relation_types.all(), subject_id__in=subjects_id):
        for relation in Relation.objects.filter(type__in=self.relation_types.all(), subject_entity__in=subjects):
            add_edge(unicode(relation.subject_entity),
                     unicode(relation.object_entity),
                     label=unicode(relation.type.predicate).encode('utf-8')) # beware: not unicode for label (pygraphviz use label as dict key)
            #add_edge('b', 'd', color='#FF0000', fontcolor='#00FF00', label='foobar', style='dashed')

        #print graph.string()

        graph.layout(prog='dot') #algo: neato dot twopi circo fdp nop

        #TODO: use a true tmp file ???? or in populate ???
        dir_path = join(settings.MEDIA_ROOT, 'upload', 'graphs')
        if not exists(dir_path):
            makedirs(dir_path)

        filename = 'graph_%i.png' % self.id

        #TODO: delete old files ???
        graph.draw(join(dir_path, filename), format='png') #format: pdf svg

        return HttpResponseRedirect('/download_file/upload/graphs/' + filename)
