# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from os import makedirs
from os.path import join, exists
import subprocess

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import loader, Context
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity

from creme.billing import get_invoice_model


@login_required
@permission_required('billing')
def export_as_pdf(request, base_id):
    entity = get_object_or_404(CremeEntity, pk=base_id).get_real_entity()
    source = entity.get_source().get_real_entity()
    target = entity.get_target().get_real_entity()

    template_name = 'invoice' if isinstance(entity, get_invoice_model()) else 'billings'
    document_name = _(entity._meta.verbose_name)

    t = loader.get_template('billing/templates/%s.tex' % template_name)
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
    f = open(file_path, 'w')  # TODO: use 'with' statement
    f.write(smart_str(t.render(context)))
    f.close()

    retcode = subprocess.call(['pdflatex', '-output-directory', dir_path, file_path])  # TODO: test retcode ??

    return HttpResponseRedirect('/download_file/upload/billing/%s.pdf' % basename)
