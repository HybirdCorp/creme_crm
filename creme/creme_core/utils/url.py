# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2017-2021 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
################################################################################

import re
from urllib.parse import urlparse

from django.urls import reverse


class TemplateURLBuilderError(Exception):
    """Cannot generate an URL template because of collision."""
    pass


class TemplateURLBuilder:
    r""" Resolve URLs by their name, but some parts of the URL can be replaced by
    template-like arguments ; it can be useful to build template-URL for JavaScript.

    Example:
        You have a URL which is like: '/my_app/list_elements/65/9'
        You want something like '/my_app/list_elements/65/$count'.

        In your file my_app.urls.py your URL is declared as:
            re_path(
                r'^list_elements/(?P<ctype_id>\d+)/(?P<count>\d+)$',
                my_views.list_elements,
                name='list_my_app_elements',
            ),

        So you want to create a template-like URL for the parameter 'count' of
        the view (the 'ctype_id' is fixed):
            builder = TemplateURLBuilder(count=(TemplateURLBuilder.Int, '$count'))
            url = builder.resolve('list_my_app_elements', kwargs={'ctype_id': 65})

    BEWARE:
        The way the template is built uses string replacement with place holders.
        In order to avoid ambiguous replacement, these place holders must be unique
        and should not appear several times in the URL.
        The resolve() method tries several place-holder to avoids unlucky
        collision before failing.
        So, the regex groups name should accept long & various string,
        like long integer or words, & it would regularly fail if the group name
         is a simple letter/numeric for example.
        It's why no PlaceHolder class for simple alphanumeric is provided,
        because it would be a bad idea.
    """

    class PlaceHolder:
        def __init__(self, final_name, regex_key):
            self.final_name = final_name
            self.regex_key = regex_key

        def tmp_name(self, index, trial):
            raise NotImplementedError

    class Word(PlaceHolder):
        _patterns = [
            '__placeholder{}__', '__PLACEHOLDER{}__',
            '__place_holder{}__', '__PLACE_HOLDER{}__',
            '__XXXXXX{}__',
        ]

        def tmp_name(self, index, trial):
            patterns = self._patterns
            return patterns[trial % len(patterns)].format(index)

    class Int(PlaceHolder):
        _patterns = [
            '123456789{}', '987654321{}', '88888888888888{}', '112233445566{}',
        ]

        def tmp_name(self, index, trial):
            patterns = self._patterns
            return patterns[trial % len(patterns)].format(index)

    def __init__(self, **place_holders):
        """Constructor.

        @param place_holders: For each kwarg:
               - The key is the name of the URL part in the URL regex.
               - The value is a tuple (PlaceHolderClass, final_name).
        """
        self._place_holders = [
            ph_value[0](final_name=ph_value[1], regex_key=ph_key)
            for ph_key, ph_value in place_holders.items()
        ]

    def resolve(self, viewname, urlconf=None, kwargs=None, current_app=None):
        """This method works like django.urls.reverse(), excepted that:
        - It has no 'args' parameter ; you have to use the 'kwargs' one.
        - The returned URL is not a valid URL
          (if you have passed some place_holders to the constructor, of course).
        """
        kwargs = kwargs or {}
        reverse_kwargs = {}
        tried_urls = []

        for trial in range(10):
            try:
                tmp_names = []

                for index, place_holder in enumerate(self._place_holders):
                    tmp_name = place_holder.tmp_name(index, trial)
                    reverse_kwargs[place_holder.regex_key] = tmp_name
                    tmp_names.append(tmp_name)

                reverse_kwargs.update(kwargs)

                url = reverse(
                    viewname,
                    kwargs=reverse_kwargs, urlconf=urlconf, current_app=current_app,
                )
                tried_urls.append(url)

                for tmp_name, place_holder in zip(tmp_names, self._place_holders):
                    url = url.replace(tmp_name, place_holder.final_name, 1)

                    if tmp_name in url:
                        raise TemplateURLBuilderError

            except TemplateURLBuilderError:
                pass
            else:
                return url

        raise TemplateURLBuilderError(
            'Cannot generate a URL because of a collision '
            '(we tried these URLs -- with place holders --: {})'.format(
                ' '.join(tried_urls),
            )
        )


def parse_path(path):
    # handles C:/ use case for windows
    path = re.sub(r'^(?:file://)?[/]*([A-Za-z]):[\\/]', r'file://\1/', path)
    return urlparse(path)
