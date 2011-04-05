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

import mimetypes
from StringIO import StringIO
from os.path import join, exists
from os import makedirs
import subprocess

from django.utils.encoding import smart_str
from django.utils.translation import ugettext
from django.shortcuts import get_object_or_404
from django.template import loader, Context
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings

from creme_core.models import CremeEntity
from creme_core.utils.exporter import Exporter

from billing.constants import CURRENCY
from billing.models import Invoice


#TODO: delete ??
def export_odt(request, base_id):
    c = get_object_or_404(CremeEntity, pk=base_id).get_real_entity()
    c.populate_with_organisation()
    c.currency = CURRENCY
    if c.source.image:
        c.logo = c.source.image.get_image_file()
    else:
        try:
            creme_logo = open('%s%s' % (settings.MEDIA_ROOT,'/images/creme_header_50.png'), 'rb')
            mimetype = mimetypes.guess_type(creme_logo.name)[0]
        except IOError:
            creme_logo = StringIO()
            mimetype = 'image/png'
        c.logo = (creme_logo, mimetype)
    return Exporter("%s%s" % (settings.MANDATORY_TEMPLATE, 'billing/templates/billing.odt'), c).generateODT(c.name)

#TODO: delete ??
#Draft
def export_pdf(request, base_id):
    c = get_object_or_404(CremeEntity, pk=base_id).get_real_entity()
    return Exporter("%s%s" % (settings.MANDATORY_TEMPLATE, 'billing/templates/report.odt'), c).generatePDF(c.name)

def export_pdf_by_latex(request, base_id):
    entity = get_object_or_404(CremeEntity, pk=base_id).get_real_entity()
    source = entity.get_source().get_real_entity()
    target = entity.get_target().get_real_entity()

    if isinstance(entity, Invoice):
        template_file = 'billing/templates/invoice.tex'
    else:
        template_file = 'billing/templates/billings.tex'

    document_name = ugettext(entity._meta.verbose_name)

    t = loader.get_template(template_file)
    context = Context({
            'plines':        entity.product_lines,
            'slines':        entity.service_lines,
            'source':        source,
            'target':        target,
            'object':        entity,
            'document_name': document_name
        })

    dir_path = join(settings.MEDIA_ROOT, 'upload', 'billing')
    if not exists(dir_path):
        makedirs(dir_path)

    basename = '%s_%i' % (document_name, entity.id)

    file_path = join(dir_path, '%s.tex' % basename)
    f = open(file_path, 'w') #TODO: use 'with' statement
    f.write(smart_str(t.render(context)))
    f.close()

    retcode = subprocess.call(['pdflatex', '-output-directory', dir_path, file_path]) #TODO: test retcode ??

    return HttpResponseRedirect('/download_file/upload/billing/%s.pdf' % basename)
