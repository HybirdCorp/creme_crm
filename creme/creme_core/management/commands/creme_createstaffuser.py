from django.contrib.auth.management.commands import createsuperuser
from django.core.management.base import CommandError


class Command(createsuperuser.Command):
    help = 'Used to create a staff superuser.'

    def handle(self, *args, **options):
        mngr = self.UserModel._default_manager

        if not mngr.filter(is_superuser=True, is_staff=False).exists():
            raise CommandError(
                'No existing super-user found (to assign the staff Contact). '
                'The command "creme_populate" has not been run?!'
            )

        # HOOK: we hook the method create_superuser() which is called by super()
        #       (we cannot override a method to call properly our own method
        #        without copy all the code of super() )
        create_superuser = mngr.create_superuser

        def create_staff_user(**user_data):
            user_data['is_staff'] = True
            return create_superuser(**user_data)

        mngr.create_superuser = create_staff_user
        # HOOK - end -----------------------------------------------------------

        try:
            super().handle(*args, **options)
        finally:
            # un-HOOK (useful for unit tests)
            mngr.create_superuser = create_superuser
