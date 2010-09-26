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

from django.http import HttpResponse

#from relatorio.templates.opendocument import Template
#from relatorio.templates.pdf import Template as PdfTemplate


class Exporter(object):
    pass
#    def __init__(self, filepath, context=None):
#        self.filepath = filepath
#        self.context = context
#
#    def generateODT(self, output_name=None):
#        #http://framework.openoffice.org/documentation/mimetypes/mimetypes.html
#        basic = Template(source=None, filepath=self.filepath)
#        basic_generated = basic.generate(o=self.context).render()
#
#        response = HttpResponse(basic_generated.getvalue(), mimetype='application/vnd.oasis.opendocument.text')
#
#        response['Content-Disposition'] = 'attachment; filename="%s.odt"' % ((output_name or "file").replace(' ',''))
#        return response
#
#    def generatePDF(self, output_name=None):
#        raise NotImplementedError
