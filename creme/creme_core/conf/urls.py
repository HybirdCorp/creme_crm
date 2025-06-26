################################################################################
#
# Copyright (c) 2018-2025 Hybird
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
################################################################################

from collections.abc import Callable, Iterator


class Swappable:
    r"""Wrapper for django.conf.urls.url(...) which indicates this path can be
     swapped on some reason (see _PatternSwapManager).

     A swapped URL is a URL which is not given to the Django's resolver & must
     be defined in another place. It's useful when you define a view related to
     a swappable model, & you want your vanilla view to be defined only if the
     model is the vanilla one.

     E.g. we want to wrap
        re_path(
            r'^my_stuff/(?P<id>\d+)/edit[/]?$',
            my_app.views.my_stuff.StuffEdition.as_view(),
            name='my_app__create_my_stuff',
        )

     It could give (notice the integer argument which corresponds to our URL):
        Swappable(url(...), check_args=(1,)

     Notice: we can use <check_args=Swappable.INT_ID> here.
    """
    __slots__ = ('pattern', 'check_args')

    INT_ID = (1,)

    def __init__(self, pattern, check_args=()):
        """Constructor.

        @param pattern: Should be an object returned by url().
        @param check_args: Tuple used as arguments to reverse() the <pattern>.
               Empty tuple by default (i.e. OK for URL without argument).
        """
        self.pattern = pattern
        self.check_args = check_args

    @property
    def verbose_args(self) -> str:
        """Returns a string describing the types of the arguments."""
        return '[{}]'.format(', '.join(type(arg).__name__ for arg in self.check_args))


class _PatternSwapManager:
    r"""Manager for Swappable URLs in a project.

    You can register some Swappable URLs into it, then iterate on the URLs,
    or only the swapped one.

    See to:
     - creme_core.checks.check_swapped_urls: check that all swapped URLs have been
       defined in another place.

    In a <urls.py> :

    urlpatterns += swap_manager.add_group(
        my_app.my_stuff_model_is_custom,
        Swappable(
            re_path(
                r'^my_stuff/add[/]?$',
               views.my_stuff.StuffCreation.as_view(),
               name='my_app__create_stuff'
            ),
        ),
        Swappable(
            re_path(
                r'^my_stuff/(?P<stuff_id>\d+)[/]?$',
                views.my_stuff.StuffDetail.as_view(),
                name='my_app__view_stuff',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='my_app',
    ).kept_patterns()
    """

    class _SwappableGroup:
        """Collection of Swappable instances, with the condition to swap them."""
        def __init__(self, swapping_func, *patterns, app_name):
            """See _PatternSwapManager.add_group()"""
            for pattern in patterns:
                if not isinstance(pattern, Swappable):
                    raise ValueError(f'<patterns> must be Swappable instances: {pattern}.')

            self.func = swapping_func
            self.swappables = patterns
            self.app_name = app_name

        def __iter__(self):
            """Iterate on all Swappable instances."""
            return iter(self.swappables)

        def kept_patterns(self):
            """Iterate on kept (ie not swapped, the condition is False) pattern instances
            (the ones which are wrapped with Swappable).
            """
            if not self.func():
                for swappable in self:
                    yield swappable.pattern

        def swapped(self):
            """Iterate on swapped Swappable instances."""
            if self.func():
                yield from self

    groups: list[_SwappableGroup]

    def __init__(self):
        self.groups = []

    def add_group(self,
                  swapping_func: Callable[[], bool],
                  *patterns: Swappable,
                  app_name: str = '??') -> _SwappableGroup:
        """Add several Swappable instances which are swapped on the same condition.

        @param swapping_func: Callable which takes no argument and return a boolean ;
                              <True> result means all these URLs must bz swapped/ignored.
        @param patterns: Instances of <Swappable(url(..))>.
        @param app_name: Name of the app where the file urls.py stands.
        @return: An instance of <_SwappableGroup>.
        """
        group = self._SwappableGroup(swapping_func, *patterns, app_name=app_name)
        self.groups.append(group)

        return group

    def __iter__(self) -> Iterator[_SwappableGroup]:
        """Iterate on all groups."""
        return iter(self.groups)


swap_manager = _PatternSwapManager()
