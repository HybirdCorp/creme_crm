# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from __future__ import with_statement

import os
from random import randint

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings

from creme_core.utils.secure_filename import secure_filename

MAXINT = 100000

def handle_uploaded_file(f, path=None, name=None):
    """
        Handle an uploaded file by a form and return the complete file's path
        path has to be iterable
    """
    def get_name(file, exists=False):
        if hasattr(file, 'name'):
            name = file.name
        elif hasattr(file, '_name'):
            name = file._name
        else :
            name = 'file_%08x' % randint(0, MAXINT)

        if exists or not name:
            name = "%08x%s" % (randint(0, MAXINT), name)

        if name.rpartition('.')[2] not in settings.ALLOWED_EXTENSIONS:
            name = "%s.txt" % name
        return name


    if not hasattr(path, "__iter__"):
        return_path = 'upload'
        path = os.path.join(settings.MEDIA_ROOT, 'upload')
    else:
        return_path = os.path.join(*path)
        path = os.path.join(settings.MEDIA_ROOT, *path)

    if not os.path.exists(path):
        os.makedirs(path, 0755)

    if not name:
        name = get_name(f)

    name = secure_filename(name)

    final_path = os.path.join(path, name)

    while os.path.exists(final_path):
        name = secure_filename(get_name(f, True))
        final_path = os.path.join(path, name)

    destination = open(final_path, 'wb+', 0755)
    for chunk in f.chunks():
        destination.write(chunk)
    destination.close()

    return os.path.join(return_path, name)

@login_required
def download_file(request, location, mimetype=None):
    #TODO : To be replaced
    if mimetype is not None :
        type = mimetype
    else :
        type = location.replace('\\','/').rpartition('/')[2].split('.')
        if len(type) <= 1 :
            type = "text/plain"
            name = type[0]
        else :
            if len(type) >=3 and type[1]!=type[2]:
                name = type[0]+'.'+type[1]
            else:
                name = '.'.join(type)
            type = type[len(type)-1]

    image_url = settings.MEDIA_ROOT + os.sep + location.replace('../','').replace('..\\','')
    with open(image_url, 'rb+') as f:
        data = f.read()

    response = HttpResponse(data, mimetype=type)
    response['Content-Disposition'] = "attachment; filename=%s" % (name.replace(' ','_'))
    return response

def fetch_resources(uri, rel):
    """
    Callback to allow pisa/reportlab to retrieve Images,Stylesheets, etc.
    `uri` is the href attribute from the html link element.
    `rel` gives a relative path, but it's not used here.

    """
    path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    return path
