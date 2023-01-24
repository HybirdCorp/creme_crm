import os

from django.core.checks.security.base import SECRET_KEY_INSECURE_PREFIX
from django.core.management.templates import TemplateCommand
from django.core.management.utils import get_random_secret_key

import creme


class Command(TemplateCommand):
    help = (
        "Creates a Creme project directory structure for the given project "
        # "name in the current directory or optionally in the given directory."
        "name in the current directory."
    )
    missing_args_message = "You must provide a project name."

    def add_arguments(self, parser):
        parser.add_argument('name', help='Name of the project.')
        # parser.add_argument('directory', nargs='?', help='Optional destination directory') TODO?
        parser.add_argument('--template', help='The path or URL to load the template from.')
        parser.add_argument(
            '--extension', '-e', dest='extensions',
            action='append',
            default=['py', 'cfg', 'md'],  # 'txt'
            help='The file extension(s) to render (default: %(default)s). '
                 'Separate multiple extensions with commas, or use '
                 '-e multiple times.'
        )
        # TODO?
        # parser.add_argument(
        #     '--name', '-n', dest='files',
        #     action='append', default=[],
        #     help='The file name(s) to render. Separate multiple file names '
        #          'with commas, or use -n multiple times.'
        # )

    def handle(self, **options):
        project_name = options.pop('name')
        self.verbosity = options['verbosity']
        # target = options.pop('directory') TODO?

        options['files'] = []

        if options['template'] is None:
            options['template'] = os.path.join(
                creme.__path__[0], 'creme_core', 'conf', 'project_template',
            )

        self.rewrite_template_suffixes = [
            (f'.{ext}-tpl', f'.{ext}') for ext in options['extensions']
        ]

        options['secret_key'] = SECRET_KEY_INSECURE_PREFIX + get_random_secret_key()
        options['creme_version'] = creme.__version__

        # target=None => current directory
        super().handle('project', project_name, target=None, **options)

        if self.verbosity >= 1:
            self.stdout.write(
                f'You should now MOVE in the folder "{project_name}{os.path.sep}" '
                f'and EDIT the file "{project_name}{os.path.sep}settings.py".\n'
                f'Then, run the following commands:\n'
                f' To create/upgrade the DataBase schema:\n'
                f'   > creme migrate --settings={project_name}.settings\n'
                f' To inject the default data (only for new DB) and the mandatory data:\n'
                f'   > creme creme_populate --settings={project_name}.settings\n'
                f' To build the static assets (JavaScript, CSS, images...):\n'
                f'   > creme generatemedia --settings={project_name}.settings\n'
                f' You COULD now run a DEVELOPMENT Web server to test the previous steps before '
                f' configuring a production a Web server:\n'
                f'   > creme runserver --settings={project_name}.settings\n'
                f'Do not forget that some features need the job manager to be launched; '
                f'you should configure a watch-dog for the following command:\n'
                f'  > creme creme_job_manager --settings={project_name}.settings\n'
            )
