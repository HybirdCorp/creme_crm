# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

import os
from os.path import basename, join
from random import randint

from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils.translation import ugettext as _

from ..auth.decorators import login_required
# from ..utils.secure_filename import secure_filename
from ..utils.file_handling import FileCreator


MAXINT = 100000


def handle_uploaded_file(f, path=None, name=None):
    """Handle an uploaded file by a form and return the complete file's path
    path has to be iterable
    """
    # def get_name(file, exists=False):
    def get_name(file):
        if hasattr(file, 'name'):
            name = file.name
        elif hasattr(file, '_name'):
            name = file._name
        else:
            name = 'file_%08x' % randint(0, MAXINT)

        # if exists or not name:
        #     name = "%08x%s" % (randint(0, MAXINT), name)

        if name.rpartition('.')[2] not in settings.ALLOWED_EXTENSIONS:
            name = '%s.txt' % name

        return name

    if not hasattr(path, '__iter__'):  # TODO: path is None  (or add support for only one string)
        relative_dir_path = 'upload'
        dir_path = join(settings.MEDIA_ROOT, 'upload')
    else:
        relative_dir_path = join(*path)
        dir_path = join(settings.MEDIA_ROOT, *path)

    # if not os.path.exists(dir_path):
    #     os.makedirs(dir_path, 0755)

    if not name:
        name = get_name(f)

    # name = secure_filename(name)
    # final_path = join(path, name)
    #
    # while os.path.exists(final_path):
    #     name = secure_filename(get_name(f, True))
    #     final_path = join(path, name)
    final_path = FileCreator(dir_path=dir_path, name=name).create()

    with open(final_path, 'wb+', 0755) as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    # return join(relative_dir_path, name)
    return join(relative_dir_path, basename(final_path))


@login_required
def download_file(request, location, mimetype=None):
    if mimetype is not None:
        ftype = mimetype
    else:
        name_parts = location.replace('\\','/').rpartition('/')[2].split('.')

        if len(name_parts) == 1:  # Should not happen
            ftype = 'text/plain'
            name = name_parts[0]
        else:
            if len(name_parts) > 2 and name_parts[-1] == 'txt' and \
               name_parts[-2] not in settings.ALLOWED_EXTENSIONS:
                name_parts.pop()  # Drop the added '.txt'

            name = '.'.join(name_parts)
            ftype = name_parts[-1]

    path = settings.MEDIA_ROOT + os.sep + location.replace('../','').replace('..\\','')

    try:
        with open(path, 'rb') as f:
            data = f.read()
    except IOError:
        raise Http404(_('Invalid file'))

    response = HttpResponse(data, content_type=ftype)
    response['Content-Disposition'] = "attachment; filename=%s" % (name.replace(' ','_'))

    return response


def fetch_resources(uri, rel):
    """Callback to allow pisa/reportlab to retrieve Images,Stylesheets, etc.
    `uri` is the href attribute from the html link element.
    `rel` gives a relative path, but it's not used here.
    """
    return join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ''))
