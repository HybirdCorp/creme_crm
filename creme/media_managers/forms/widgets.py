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
from django.utils.safestring import mark_safe
from django.conf import settings

from creme_core.forms.widgets import ListViewWidget


class ImageM2MWidget(ListViewWidget):
    include_js =  settings.MEDIA_URL + '/js/models/image_m2m_widget.js'

    def render(self, name, value, attrs=None):
        html_output = u"""
                %(input)s
                <script type="text/javascript">
                    include('%(include)s', 'js');
                </script>
                <a href="javascript:image_m2m_widget.handleCreate('/media_managers/image/add?popup=true&from_id=%(id)s', 'm2m_%(id)s_popup');">
                    %(label)s
                </a>
            """ % {
                    'input':   super(ImageM2MWidget, self).render(name, value, attrs),
                    'include': self.include_js,
                    'id':      self.attrs['id'],
                    'label':   _(u'Add image'),
                  }

        return mark_safe(html_output)
