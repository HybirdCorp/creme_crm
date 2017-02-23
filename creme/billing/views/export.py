# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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
from os import path
from shutil import copy, rmtree
import subprocess
from tempfile import mkdtemp

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import loader
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils.file_handling import FileCreator
from creme.creme_core.utils.secure_filename import secure_filename

from creme import billing


logger = logging.getLogger(__name__)
TEMPLATE_PATHS = {
    billing.get_invoice_model():       'billing/templates/invoice.tex',
    billing.get_credit_note_model():   'billing/templates/billings.tex',
    billing.get_quote_model():         'billing/templates/billings.tex',
    billing.get_sales_order_model():   'billing/templates/billings.tex',
    billing.get_template_base_model(): 'billing/templates/billings.tex',
}


@login_required
@permission_required('billing')
def export_as_pdf(request, base_id):
    entity = get_object_or_404(CremeEntity, pk=base_id).get_real_entity()

    has_perm = request.user.has_perm_to_view_or_die
    has_perm(entity)

    template_path = TEMPLATE_PATHS.get(entity.__class__)
    if template_path is None:
        raise ConflictError('This type of entity cannot be exported as pdf')

    source = entity.get_source().get_real_entity()
    has_perm(source)

    target = entity.get_target().get_real_entity()
    has_perm(target)

    document_name = unicode(entity._meta.verbose_name)

    template = loader.get_template(template_path)
    context = {
            # 'plines':        entity.product_lines,
            # 'slines':        entity.service_lines,
            'plines':        entity.get_lines(billing.get_product_line_model()),
            'slines':        entity.get_lines(billing.get_service_line_model()),
            'source':        source,
            'target':        target,
            'object':        entity,
            'document_name': document_name,
        }

    basename = secure_filename(u'%s_%i' % (document_name, entity.id))
    tmp_dir_path = mkdtemp(prefix='creme_billing_latex')
    latex_file_path = path.join(tmp_dir_path, '%s.tex' % basename)

    with open(latex_file_path, 'w') as f:
        f.write(smart_str(template.render(context)))

    # NB: return code seems always 1 even when there is no error...
    subprocess.call(['pdflatex',
                     '-interaction=batchmode',
                     '-output-directory', tmp_dir_path,
                     latex_file_path,
                    ]
                   )

    pdf_basename = '%s.pdf' % basename
    temp_pdf_file_path = path.join(tmp_dir_path, pdf_basename)

    if not path.exists(temp_pdf_file_path):
        logger.critical('It seems the PDF generation has failed. '
                        'The temporary directory has not been removed, '
                        'so you can inspect the *.log file in %s' % tmp_dir_path
                       )
        # TODO: use a better exception class ?
        raise ConflictError(_(u'The generation of the PDF file has failed ; please contact your administrator.'))

    final_path = FileCreator(dir_path=path.join(settings.MEDIA_ROOT, 'upload', 'billing'),
                             name=pdf_basename,
                            ).create()
    copy(temp_pdf_file_path, final_path)

    rmtree(tmp_dir_path)

    # return HttpResponseRedirect('/download_file/upload/billing/' + path.basename(final_path))
    return HttpResponseRedirect(reverse('creme_core__dl_file',
                                        args=('upload/billing/' + path.basename(final_path),),
                                       )
                               )
