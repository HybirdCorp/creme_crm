from hashlib import sha1
import os
import posixpath
import sys
import re
from subprocess import Popen, PIPE

from django.utils.encoding import smart_str
from django.conf import settings

from mediagenerator.generators.bundles.base import Filter
from mediagenerator.utils import find_file, read_text_file, get_media_dirs

_RE_FLAGS = re.MULTILINE | re.UNICODE
multi_line_comment_re = re.compile(r'/\*.*?\*/', _RE_FLAGS | re.DOTALL)
one_line_comment_re = re.compile(r'//.*', _RE_FLAGS)
import_re = re.compile(r'''@import\s*  # import keyword
                           ["']        # opening quote
                           (.+?)       # the module name
                           ["']        # closing quote
                           \s*;        # statement terminator
                           ''',
                       _RE_FLAGS | re.VERBOSE)

if not hasattr(os.path, 'relpath'):
    # backport os.path.relpath from Python 2.6
    # Copyright (c) 2001-2010 Python Software Foundation; All Rights Reserved

    # Return the longest prefix of all list elements.
    def commonprefix(m):
        "Given a list of pathnames, returns the longest common leading component"
        if not m: return ''
        s1 = min(m)
        s2 = max(m)
        for i, c in enumerate(s1):
            if c != s2[i]:
                return s1[:i]
        return s1

    def relpath(path, start=os.path.curdir):
        """Return a relative version of a path"""

        if not path:
            raise ValueError("no path specified")

        start_list = [x for x in os.path.abspath(start).split(os.path.sep) if x]
        path_list = [x for x in os.path.abspath(path).split(os.path.sep) if x]

        # Work out how much of the filepath is shared by start and path.
        i = len(commonprefix([start_list, path_list]))

        rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
        if not rel_list:
            return os.path.curdir
        return os.path.join(*rel_list)

    os.path.relpath = relpath


class Less(Filter):
    takes_input = False

    def __init__(self, **kwargs):
        self.config(kwargs, path=(), main_module=None)
        if isinstance(self.path, str):
            self.path = (self.path,)

        # we need to be able to mutate self.path
        self.path = [*self.path]

        super().__init__(**kwargs)

        assert self.filetype == 'css', (
            f'Less only supports compilation to CSS. '
            f'The parent filter expects "{self.filetype}".')
        assert self.main_module, 'You must provide a main module'

        # lessc can't cope with nonexistent directories, so filter them
        media_dirs = [directory for directory in get_media_dirs()
                      if os.path.exists(directory)]
        self.path += tuple(media_dirs)

        self._compiled = None
        self._compiled_hash = None
        self._dependencies = {}

    @classmethod
    def from_default(cls, name):
        return {'main_module': name}

    def get_output(self, variation):
        self._regenerate(debug=False)
        yield self._compiled

    def get_dev_output(self, name, variation):
        assert name == self.main_module + '.css'
        self._regenerate(debug=True)
        return self._compiled

    def get_dev_output_names(self, variation):
        self._regenerate(debug=True)
        yield self.main_module + '.css', self._compiled_hash

    def _regenerate(self, debug=False):
        if self._dependencies:
            for name, mtime in self._dependencies.items():
                path = self._find_file(name)
                if not path or os.path.getmtime(path) != mtime:
                    # Just recompile everything
                    self._dependencies = {}
                    break
            else:
                # No changes
                return

        modules = [self.main_module]
        # get all the transitive dependencies of this module
        while True:
            if not modules:
                break

            module_name = modules.pop()
            path = self._find_file(module_name)
            assert path, f'Could not find the Less module {module_name}'
            mtime = os.path.getmtime(path)
            self._dependencies[module_name] = mtime

            source = read_text_file(path)
            dependencies = self._get_dependencies(source)

            for name in dependencies:
                # Try relative import, first
                transformed = posixpath.join(posixpath.dirname(module_name), name)
                path = self._find_file(transformed)
                if path:
                    name = transformed
                else:
                    path = self._find_file(name)

                assert path, f'The Less module {module_name} could not find the dependency {name}'

                if name not in self._dependencies:
                    modules.append(name)

        main_module_path = self._find_file(self.main_module)
        self._compiled = self._compile(main_module_path, debug=debug)
        self._compiled_hash = sha1(smart_str(self._compiled)).hexdigest()

    def _compile(self, path, debug=False):
        try:
            relative_paths = [self._get_relative_path(directory)
                              for directory in self.path]

            shell = sys.platform == 'win32'

            cmd = Popen(['lessc',
                         '--include-path={}'.format(':'.join(relative_paths)),
                         path],
                        stdin=PIPE, stdout=PIPE, stderr=PIPE,
                        shell=shell, universal_newlines=True,
                        cwd=settings.PROJECT_ROOT)
            output, error = cmd.communicate()

            # some lessc errors output to stdout, so we put both in the assertion message
            assert cmd.wait() == 0, f'Less command returned bad result:\n{error}\n{output}'
            return output.decode('utf-8')
        except Exception as e:
            raise ValueError(
                "Failed to run Less compiler for this "
                "file. Please confirm that the \"lessc\" application is "
                "on your path and that you can run it from your own command "
                "line.\n"
                "Error was: {}".format(e)
            )

    def _get_dependencies(self, source):
        clean_source = multi_line_comment_re.sub('\n', source)
        clean_source = one_line_comment_re.sub('', clean_source)

        return [name for name in import_re.findall(clean_source)
                if not name.endswith('.css')]

    def _find_file(self, name):
        if not name.endswith('.less'):
            name = name + '.less'

        return find_file(name, media_dirs=self.path)

    def _get_relative_path(self, abs_path):
        """Given an absolute path, return a path relative to the
        project root.

        >>> self._get_relative_path('/home/bob/bobs_project/subdir/foo')
        'subdir/foo'

        """
        return os.path.relpath(abs_path, settings.PROJECT_ROOT)
