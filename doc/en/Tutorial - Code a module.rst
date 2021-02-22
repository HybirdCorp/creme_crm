======================================
Developer's notebook for Creme modules
======================================

:Author: Guillaume Englert
:Version: 29-01-2021 for Creme 2.3
:Copyright: Hybird
:License: GNU FREE DOCUMENTATION LICENSE version 1.3
:Errata: Hugo Smett, Patix

.. contents:: Summary


Introduction
============

This document is addressed to people which want to add or modify some features
to the customer relationships management software Creme_. It's not an exhaustive
documentation of the Creme's API, it's a tutorial showing the creation of a module
module, step by step.


Requirements
============

- Get the bases of programming ; knowing the Python_ language would be nice.
- Knowing the HTML language a little.
- Knowing the software git_.

Creme is developed with a Python framework for websites et Web apps : Django_.
If you really want to code some modules for Creme, you should know Django.
Its documentation is complete & quite good ; see here : https://docs.djangoproject.com/en/3.0/.
To begin, reading the `tutorial <https://docs.djangoproject.com/en/3.0/intro/overview/>`_
should be enough.

Creme uses the JavaScript (JS) library jQuery_ too ; to implement some features
of your modules, you may have to use some JS on client side (Web browser) ;
in these cases knowing jQuery would be a good thing. Neverthless this is not mandatory
and we will mostly use example with no JS in this documentation.

.. _Creme: https://cremecrm.com
.. _Python: https://www.python.org
.. _git: https://git-scm.com
.. _Django: https://www.djangoproject.com
.. _jQuery: https://jquery.com

Management of a beavers' park
=============================

1. Presentation of the module
-----------------------------

The use case is: we want to create a module to manage a natural park with beavers.
We have to manage the population of beavers, and so having for all of them their
name, birthday, and also health.

A Creme module is an "app" in the Django's glossary. To be short, we'll use the
word "app" for our module.


2. First version of our module
------------------------------

Firstly you must have a working instance of Creme:

 - Fork of the official *git* repository, to get your own one.
 - Clone of your *git* repository (use the "v2.2" branch).
 - Configuration of your DBRMS.
 - Configuration of your Web server (the development server of Django is OK here).


Configuration of the file ``local_settings.py``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You should not use the cache system of templates when you code, in order
to avoid re-starting the server for each template edition : ::

    from .settings import TEMPLATES
    TEMPLATES[0]['OPTIONS']['loaders'] = (
        'django.template.loaders.app_directories.Loader',
        'django.template.loaders.filesystem.Loader',
    )

It's a good idea to activate warnings ; for example you'll be advertised that
you use deprecated code, which is useful when you upgrade the version of Creme
(generally the deprecated code is removed in the next version -- the deprecation
message will often indicate which function/class to use instead). The following
configuration allows the display of warnings, but only once for each one
(to avoid flooding your terminal with duplicated messages) : ::

    import warnings
    warnings.simplefilter('once')


Additional tools
~~~~~~~~~~~~~~~~

The app `django extensions <https://github.com/django-extensions/django-extensions>`_
is interesting, it provides some useful commands (``runserver_plus``,
``shell_plus``, ``clean_pyc``, …).


Use of git
~~~~~~~~~~

Although the code you'll write remain in its own directory, this directory
will be among the others modules of Creme. In a future version of Creme,
the separation between your code and Creme's one would be easier (and
documented of course).

Right now, we just work in our own branch : ::

    > git checkout -b beavers

Each time you add a feature, you can create a *commit* : ::

    > git commit -a

Can van visualise the modifications done since the last commit with : ::

    > git diff

At the end of your working session, you can save your work in your repository : ::

    > git push origin beavers

When you want to re-synchronise your code with Creme code (to get the last
minor update for example), you have to make a **rebase**.


Creation of the parent directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Move to our project, in the directory ``creme/`` : ::

    > cd creme_crm/creme

There is a command to create an app (``django-admin.py startapp``), nonetheless
this task is really easy, so we'er going to made this work ourselves, step by step.
First, we create the directory containing our app : ::

    > mkdir beavers

Notice that, by convention (and for technical reason we'll see just after),
we use the plural form of the term "beaver".

Move to our new directory : ::

    > cd beavers

In order to the directory *beavers* is considered by Python as a module, we
must add a file named ``__init__.py`` (it can remain empty) : ::

    > touch __init__.py


Creation of the first model
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now we create another directory, ``models/``, and move into it : ::

    > mkdir models
    > cd models


Then we create a file named ``beaver.py`` (notice the singular form) with our
favorite text editor, containing the following code : ::

    # -*- coding: utf-8 -*-

    from django.db.models import CharField, DateField
    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.models import CremeEntity


    class Beaver(CremeEntity):
        name     = CharField(_('Name'), max_length=100)
        birthday = DateField(_('Birthday'))

        class Meta:
            app_label = 'beavers'
            verbose_name = _('Beaver')
            verbose_name_plural = _('Beavers')
            ordering = ('name',)

        def __str__(self):
            return self.name


We've just created our first model class, ``Beaver``. This model will correspond
to a table à une table dans notre DataBase Management System (DBMS) : *beavers_beaver*.
At the moment, we only store for each beaver its name and its birthday.
Our model inherits ``CremeEntity``, and not ``DjangoModel``: it means that our
beavers can have Properties, de Relationships, can be displayed in a list-view,
and use many more services.

In addition to the fields, we declare to:

- The class ``Meta`` which allows to indicate the name of the model's app for example.
- The method ``__str__`` used to display the ``Beavers`` objects prettily.


One again, to make the directory ``models/`` a module, we must put inside a
second file named ``__init__.py``, containing : ::

    # -*- coding: utf-8 -*-

    from .beaver import Beaver


So, when Creme is starting, our model is automatically imported by Django, and
is linked to its table in the DBMS.


Install our module
~~~~~~~~~~~~~~~~~~

Edit the file ``creme/project_settings.py`` by copying from the general
configuration file ``creme/settings.py`` the tuple INSTALLED_CREME_APPS. ::

    INSTALLED_CREME_APPS = (
        # CREME CORE APPS
        'creme.creme_core',
        'creme.creme_config',
        'creme.media_managers',
        'creme.documents',
        'creme.activities',
        'creme.persons',

        # CREME OPTIONAL APPS (can be safely commented)
        'creme.assistants',
        'creme.graphs',
        'creme.reports',
        'creme.products',
        'creme.recurrents',
        'creme.billing',
        'creme.opportunities',
        'creme.commercial',
        'creme.events',
        'creme.crudity',
        'creme.emails',
        'creme.projects',
        'creme.tickets',
        'creme.vcfs',

        'creme.beavers',  # <-- NEW
    )

Notice that we have added our app at the end of the tuple.

**Remark** : we use ``creme/project_settings.py`` instead of
``creme/local_settings.py`` because the list of installed apps in the project
should probably be shared between the teammates (developer, administrators).


Create the table in the database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Still from the directory ``creme/``, run the following commands : ::

    > python creme/manage.py makemigrations beavers

It will create a directory ``creme/beavers/migrations/`` with 2 inner files
``__init__.py`` and ``0001_initial.py``. This last one indicates to Django the
description of the table which will contain our beavers : ::

    > python creme/manage.py migrate beavers
    Operations to perform:
        Apply all migrations: beavers
    Running migrations:
        Rendering model states... DONE
        Applying beavers.0001_initial... OK

As you can see, a table "beavers_beaver" has been created. If you inspect it
(with PHPMyAdmin for example), you'll see it has a column named "name", with
the type VARCHAR(100), and a column "birthday" with the type DATE.


Declare our app
~~~~~~~~~~~~~~~

First, we create a new file ``beavers/apps.py`` containing : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.apps import CremeAppConfig


    class BeaversConfig(CremeAppConfig):
        name = 'creme.beavers'
        verbose_name = _('Beavers management')
        dependencies = ['creme.creme_core']

        def register_entity_models(self, creme_registry):
            from .models import Beaver

            creme_registry.register_entity_models(Beaver)



The singleton ``creme_registry`` stores the models inheriting ``CremeEntity``
(call to ``creme_registry.register_entity_models()``) if we want they dispose
of global search, configuration for buttons and blocs... It's generally the case
when we inherit ``CremeEntity``.

We wrote the configuration of our app ; in order Django uses our class, we must
do a small other thing. Edit the file ``beavers/__init__.py`` and add the
following line : ::

    default_app_config = 'creme.beavers.apps.BeaversConfig'


If we launch Creme with the Django's development server, and we log in
with our Web browser (to the address defined by SITE_DOMAIN in the
configuration), what happens? ::

    > python creme/manage.py runserver


There is no trace of our new app. But don't worry, we will fix it.


Our first view: the list view
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Our goal is now to display the list of beavers, corresponding to the URL
'/beavers/beavers'.

We add first a new directory ``views/`` in ``beavers/``, and its usual file
``__init__.py`` : ::

    > mkdir views
    > cd views
    > touch __init__.py


In ``views/``, we create the file ``beaver.py`` like : ::

    # -*- coding: utf-8 -*-

    from creme.creme_core.views import generic

    from creme.beavers.models import Beaver


    class BeaversList(generic.EntitiesList):
        model = Beaver


We must now link this view to its URL. Take a look to the file ``creme/urls.py`` ;
we find the configuration of base paths for each app. We can see that for each
app in the tuple INSTALLED_CREME_APPS, the code imports the file ``urls.py`` in
the directory ``name_of_your_app/``.

So we do not have to modify ``creme/urls.py`` and we just create the file
``urls.py`` in ``beaver/`` : ::

    # -*- coding: utf-8 -*-

    from django.urls import re_path

    from .views import beaver

    urlpatterns = [
        re_path(r'^beavers[/]?$', beaver.BeaversList.as_view(), name='beavers__list_beavers'),
    ]

Notice that :

 - the last parameter of ``re_path()``, which gives a name to our URL. The
   convention of Creme is 'my_app' + '__list_' + 'my_models' for the list view.
 - the final '/' of our URL which is optional (it's the general policy for URLs
   in Creme).

Finally we add the method ``get_lv_absolute_url()`` in our model. This method
will make possible to return to the bevaars' list when we delete a beaver, for
example : ::

    # -*- coding: utf-8 -*-

    [...]

    from django.urls import reverse


    class Beaver(CremeEntity):
        [...]

        @staticmethod
        def get_lv_absolute_url():
            return reverse('beavers__list_beavers')


**Note** : the method ``reverse()``, which permit to find an URL by the name
given to the function ``re_path()`` used in our ``urls.py``.

We can now reach the list from our browser by typing it in the address bar…
well almost. Indeed Creme asks us to create a view-of-list. When it's done,
we get our beavers' list… and its empty. Of course, no beaver has been created
yet.


The creation view
~~~~~~~~~~~~~~~~~

Create a directory ``beavers/forms``, with the usual ``__init__.py`` : ::

    > mkdir forms
    > cd forms
    > touch __init__.py


In ``forms/``, we create then the file ``beaver.py`` : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.forms import CremeEntityForm

    from ..models import Beaver


    class BeaverForm(CremeEntityForm):
        class Meta(CremeEntityForm.Meta):
            model = Beaver


It's a simple form related to our model.

**Note** : most of creation views for entities which you find in the base apps
provided by Creme do not use a regular Django's form. They use the CustomForm
system of Creme instead, which allows teh users to configure the fields
themselves. CustomForms are explained later, and we will use in a first time
the regular forms, to be simpler.

Then we edit ``views/beaver.py``, by adding the following lines at the end (you
can move the ``import`` at the beginning of tye file, with other ``import``,
of course) : ::

    from ..forms.beaver import BeaverForm

    class BeaverCreation(generic.EntityCreation):
        model = Beaver
        form_class = BeaverForm


We add the entry referencing ``beaver.BeaverCreation`` in ``beavers/urls.py`` : ::

    urlpatterns = [
        re_path(r'^beavers[/]?$',    beaver.BeaversList.as_view(),    name='beavers__list_beavers'),
        re_path(r'^beaver/add[/]?$', beaver.BeaverCreation.as_view(), name='beavers__create_beaver'),
    ]


It remains a method ``get_create_absolute_url()`` to add in our model, and
the attributes ``creation_label`` and ``save_label``, which allows to name
correctly some interface elements (button, menu etc…) : ::

    # -*- coding: utf-8 -*-


    class Beaver(CremeEntity):
        [...]

        creation_label = _('Create a beaver')  # Label of tyhe creation form
        save_label	   = _('Save the beaver')  # Label of the save button

        [...]

        @staticmethod
        def get_create_absolute_url():
            return reverse('beavers__create_beaver')


If we reload our list view, a button 'Create a beaver' has appeared. When we
click it, we get the expected form. But when we submit our form (without
validation error), we get a error 500.
No panic: the class view ``EntityCreation`` just tried to display the detailed
view for our created castor. It has been created, but the view does not exist yet.


The detailed view
~~~~~~~~~~~~~~~~~

Add this class view (in ``views/beaver.py`` as seen previously) : ::

    class BeaverDetail(generic.EntityDetail):
        model = Beaver
        pk_url_kwarg = 'beaver_id'


Edit ``beavers/urls.py`` to add this URL : ::

    urlpatterns = [
        re_path(r'^beavers[/]?$',                   beaver.BeaversList.as_view(),    name='beavers__list_beavers'),
        re_path(r'^beaver/add[/]?$',                beaver.BeaverCreation.as_view(), name='beavers__create_beaver'),
        re_path(r'^beaver/(?P<beaver_id>\d+)[/]?$', beaver.BeaverDetail.as_view(),   name='beavers__view_beaver'),  # < -- NEW
    ]

If we refresh our page in the browser, we get the detailed views as expected.

**Note** : the icon of our entity does not work at the moment ; don't worry, it
will be fixed soon.

In order the next creations of beaver do not lead to error 404, we create the
method ``get_absolute_url()`` : ::

    # -*- coding: utf-8 -*-

    [...]


    class Beaver(CremeEntity):
        [...]

        def get_absolute_url(self):
            return reverse('beavers__view_beaver', args=(self.id,))


The edition view
~~~~~~~~~~~~~~~~

Currently, ours beavers cannot be edited yet (with the big pen we can see in
the detailed views).

Add this class view in ``views/beaver.py`` : ::

    class BeaverEdition(generic.EntityEdition):
        model = Beaver
        form_class = BeaverForm
        pk_url_kwarg = 'beaver_id'


Add the related URL : ::

    urlpatterns = [
        re_path(r'^beavers[/]?$',                        beaver.BeaversList.as_view(),    name='beavers__list_beavers'),
        re_path(r'^beaver/add[/]?$',                     beaver.BeaverCreation.as_view(), name='beavers__create_beaver'),
        re_path(r'^beaver/edit/(?P<beaver_id>\d+)[/]?$', beaver.BeaverEdition.as_view(),  name='beavers__edit_beaver'),  # < -- NEW
        re_path(r'^beaver/(?P<beaver_id>\d+)[/]?$',      beaver.BeaverDetail.as_view(),   name='beavers__view_beaver'),
    ]


And the method ``get_edit_absolute_url`` : ::

    # -*- coding: utf-8 -*-

    [...]


    class Beaver(CremeEntity):
        [...]

        def get_edit_absolute_url(self):
            return reverse('beavers__edit_beaver', args=(self.id,))


Add entries in the menu
~~~~~~~~~~~~~~~~~~~~~~~

In our ``apps.py``, we add the mrthod ``BeaversConfig.register_menu()`` and we
create first a new level 2 entry in the level 1 entry "Directory", which
redirects to our beavers list : ::


    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_menu(self, creme_menu):
            from .models import Beaver

            creme_menu.get('features', 'persons-directory') \
                      .add(creme_menu.URLItem.list_view('beavers-beavers', model=Beaver))


La méthode ``get()`` can retrieve elements in the menu tree. Here we fetch the
group with identifier 'features', then in this group we fetch thr container
with identifier 'persons-directory'.
If you want to know the menu structure, you can do ``print(str(creme_menu))``.

**Note** : the method ``add()`` can take e parameter ``priority`` to manage
entries orders (a lower priority means "before").

``creme_menu`` provides shortcuts to the most common menu Items,
like URLItem which corresponds to an entry redirecting to an URL.
And URLItem get a static method ``list_view()`` made specifically for
list-views (it will automatically use the right URL and the right label).

We add now an entry in the "window" which propose the creation for all types
of entities : ::

        creme_menu.get('creation', 'any_forms') \
                  .get_or_create_group('persons-directory', _('Directory'), priority=10) \
                  .add_link('create_beaver', Beaver)  # <- you can use a parameter 'priority'


In this example, we want to insert our entry in the group "Directory", so
we retrieve this group with ``get_or_create_group()``. To display the structure
of the groups in this window, you can do
``print(creme_menu.get('creation', 'any_forms').verbose_str)``.


Module initialisation
~~~~~~~~~~~~~~~~~~~~~

The majority of the modules expect some data exist in the data base, in order
to work correctly, or just to be more user friendly. For example, the first
time we displayed the beavers list-view, we had to create a view-of-list
(i.e. : columns to display in the list), named HeaderFilter in Creme's code.
We're going to write some code run at deployment, which create this view of list.

Let's create the file ``beavers/constants.py``, which contains some constants
of course : ::

    # -*- coding: utf-8 -*-

    # NB: this will be the identifier of or default HeaderFilter. To avoid
    #     collisions between apps, the convention is to build a value with
    #     the shape 'my_app' + 'hf_' + 'my_model'.
    DEFAULT_HFILTER_BEAVER = 'beavers-hf_beaver'


Then we create a file : ``beavers/populate.py``. ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import gettext as _

    from creme.creme_core.core.entity_cell import EntityCellRegularField
    from creme.creme_core.management.commands.creme_populate import BasePopulator
    from creme.creme_core.models import HeaderFilter, SearchConfigItem

    from .constants import DEFAULT_HFILTER_BEAVER
    from .models import Beaver


    class Populator(BasePopulator):
        dependencies = ['creme_core']

        def populate(self):
            HeaderFilter.create(
                pk=DEFAULT_HFILTER_BEAVER, name=_('Beaver view'), model=Beaver,
                cells_desc=[
                    (EntityCellRegularField, {'name': 'name'}),
                    (EntityCellRegularField, {'name': 'birthday'}),
                ],
            )

            SearchConfigItem.create_if_needed(Beaver, ['name'])

Explanations :

- we create a ``HeaderFilter`` with 2 columns, simply corresponding
  to the name et the birthday of our beavers. The class
  ``EntityCellRegularField`` corresponds to classical fields in the Beaver
  model (there are other classes, like ``EntityCellRelation`` for example).
- The line with ``SearchConfigItem`` is for the global search configuration :
  this one will use the field 'name' for beavers.

The code is run by the command ``creme_populate``. It 'populates' the data base
for our app. In ``creme/``, run : ::

    > python creme/manage.py creme_populate beavers


When we display our beavers' list again, the second HeaderFilter is present.

**Going further**: we improve now our beaver list-view to insure that when an
user logs in with a new session, the default HeaderFilter vue is used (without
this improvement the first HeaderFilter by alphabetical oder is used) : ::

    [...]
    from ..constants import DEFAULT_HFILTER_BEAVER  # <- NEW

    [...]

    class BeaversList(generic.EntitiesList):
        model = Beaver
        default_headerfilter_id = DEFAULT_HFILTER_BEAVER  # <- NEW


Icons management
~~~~~~~~~~~~~~~~

The icon system fetch in the images of the current theme, using the given name
and adding the size adapted to the context.

Creme is released with the icons for its included apps. For example, for the
theme "icecream", in the directory ``creme/static/icecream/images`` you find a
file "alert_22.png" ; its icon name is "alert" (this name is used, for example,
by some *templatetags*), and the le suffix "_22" indicates its width of
22 x 22 pixels.

You can add your own icons in ``creme/beavers/static/THEME/images/`` ;
(replace THEME with the name of the theme, "icecream" or "chantilly" for base
themes). Do not forget to run the command ``generatemedia`` when you add images.

In addition to explicitly named icons, Creme permit to automatically links an
icon to an entity type. Let's add a method in our file ``beavers/apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_icons(self, icon_registry):
            from .models import Beaver

            icon_registry.register(Beaver, 'images/contact_%(size)s.png')


Here we use the Contacts' icon which is provided by default ; you could use a
more specific icon of course.


Localisation (l10n)
~~~~~~~~~~~~~~~~~~~

Until now we've only used labels in english. Even if your browser is configured
to retrieve pages in french (for example) whenever it's possible, the interface
of the module *beavers* remains in english. But we've always used the functions
``gettext`` and ``gettext_lazy`` (imported as '_') to wrap our labels. So it
will be easy to localise our module.
In ``beavers/``, create a sub directory ``locale``, then run the command which
builds the translation file (in french here) : ::

    > mkdir locale
    > django-admin.py makemessages -l fr
    processing language fr


A file is created by the command (and the needed directories too) :
``locale/fr/LC_MESSAGES/django.po``

The file ``django.po`` looks like (dates will be different of course) : ::

    # SOME DESCRIPTIVE TITLE.
    # Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
    # This file is distributed under the same license as the PACKAGE package.
    # FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
    #
    #, fuzzy
    msgid ""
    msgstr ""
    "Project-Id-Version: PACKAGE VERSION\n"
    "Report-Msgid-Bugs-To: \n"
    "POT-Creation-Date: 2020-12-08 11:10+0100\n"
    "PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
    "Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
    "Language-Team: LANGUAGE <LL@li.org>\n"
    "MIME-Version: 1.0\n"
    "Content-Type: text/plain; charset=UTF-8\n"
    "Content-Transfer-Encoding: 8bit\n"
    "Plural-Forms: nplurals=2; plural=n>1;\n"

    #: apps.py:12
    msgid "Beavers management"
    msgstr ""

    #: apps.py:23
    msgid "All beavers"
    msgstr ""

    #: apps.py:24
    msgid "Create a beaver"
    msgstr ""

    #: populate.py:17
    msgid "Beaver view"
    msgstr ""

    #: populate.py:19 models/beaver.py:10
    msgid "Name"
    msgstr ""

    #: populate.py:20 forms/beaver.py:11 models/beaver.py:11
    msgid "Birthday"
    msgstr ""

    #: models/beaver.py:15
    msgid "Beaver"
    msgstr ""

    #: models/beaver.py:16
    msgid "Beavers"
    msgstr ""

Edit this file by filling the translations in strings "msgstr" : ::

    # FR LOCALISATION OF 'BEAVERS' APP
    # Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
    # This file is distributed under the same license as the PACKAGE package.
    # FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
    #
    msgid ""
    msgstr ""
    "Project-Id-Version: PACKAGE VERSION\n"
    "Report-Msgid-Bugs-To: \n"
    "POT-Creation-Date: 2020-12-08 11:10+0100\n"
    "PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
    "Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
    "Language-Team: LANGUAGE <LL@li.org>\n"
    "MIME-Version: 1.0\n"
    "Content-Type: text/plain; charset=UTF-8\n"
    "Content-Transfer-Encoding: 8bit\n"
    "Plural-Forms: nplurals=2; plural=n>1;\n"

    #: apps.py:12
    msgid "Beavers management"
    msgstr "Gestion des castors"

    #: apps.py:23
    msgid "All beavers"
    msgstr "Lister les castors"

    #: apps.py:24
    msgid "Create a beaver"
    msgstr "Créer un castor"

    #: populate.py:17
    msgid "Beaver view"
    msgstr "Vue de castor"

    #: populate.py:19 models/beaver.py:10
    msgid "Name"
    msgstr "Nom"

    #: populate.py:20 forms/beaver.py:11 models/beaver.py:11
    msgid "Birthday"
    msgstr "Anniversaire"

    #: models/beaver.py:15
    msgid "Beaver"
    msgstr "Castor"

    #: models/beaver.py:16
    msgid "Beavers"
    msgstr "Castors"


Now, you just have to compile our translation file with the following command : ::

    > django-admin.py compilemessages
    processing file django.po in [...]/creme_crm/creme/beavers/locale/fr/LC_MESSAGES

The file ``beavers/locale/fr/LC_MESSAGES/django.mo`` has been generated. If you
re-start the Web server, the labels are now in french, if your browser and your user
are configured to use french ; the *middleware*
'django.middleware.locale.LocaleMiddleware' must be in your ``settings.py`` too
(it's the default configuration).



3. Advanced principles
----------------------

Use of creme_config
~~~~~~~~~~~~~~~~~~~

Imagine we want to store the health of each castor : it could be used, for
example, by the list-view to only display sick beavers, and call a veterinary
if it's needed.

Create a file ``models/status.py`` : ::

    # -*- coding: utf-8 -*-

    from django.db.models import CharField, BooleanField
    from django.utils.translation import gettext_lazy as _, pgettext_lazy

    from creme.creme_core.models import CremeModel


    class Status(CremeModel):
        name      = CharField(_('Name'), max_length=100, unique=True)
        is_custom = BooleanField(default=True).set_tags(viewable=False)

        creation_label = pgettext_lazy('beavers-status', 'Create a status')

        def __str__(self):
            return self.name

        class Meta:
            app_label = 'beavers'
            verbose_name = _('Beaver status')
            verbose_name_plural = _('Beaver status')
            ordering = ('name',)


**Notes** : the attribute ``is_custom`` will be used by the module
*creme_config* as seen later. It's important to name it like that, and
its type must be ``BooleanField``. Notice the use of ``set_tags()`` which
permits to hide this field to the user (we'll see the tags again, later).
Giving a nice default order (attribute ``ordering`` of the class ``Meta``)
is important, because this order is used, for example, by forms (if you do
not explicitly give another one, of course).

**Notes** : we used the translation function ``pgettext_lazy()`` which takes
a context parameter. It's to avoid possible collisions with strings in other
apps. The term "status" being unclear, it could be used by other apps, and
we can imagine that in some languages (or customised translations), the
translation can be different depending on the case.
In Creme, we use contexts with prefix 'app_name-'.

Edit *models/__init__.py* : ::

    # -*- coding: utf-8 -*-

    from .status import Status  # <-- NEW
    from .beaver import Beaver


Let's generate a first migration which creates the corresponding table : ::

    > python creme/manage.py makemigrations beavers

A file named ``0002_status.py`` appears.

As we want to add a not nullable *ForeignKey* in our class ``Beaver`` (because
it's make the example more interesting), we create now a data migration
(previously we create schema migration) which adds in DB an instance of
``Status`` ; this instance will be used as default value by existing instances
of Beavers. It's a common use case : a production version you'll have to
upgrade without breaking existing data.

Let's create this migration (notice the parameter ``empty``) : ::

    > python creme/manage.py makemigrations beavers --empty

A file named from te current date has just ben created. Rename it
``0003_populate_default_status.py``, then open it in your editor.
It should look like this : ::

    # -*- coding: utf-8 -*-

    from django.db import migrations, models


    class Migration(migrations.Migration):

        dependencies = [
            ('beavers', '0002_status'),
        ]

        operations = [
        ]


Edit it to get : ::

    # -*- coding: utf-8 -*-

    from django.db import migrations, models


    def populate_status(apps, schema_editor):
        apps.get_model('beavers', 'Status').objects.create(id=1, name='Healthy', is_custom=False)


    class Migration(migrations.Migration):
        dependencies = [
            ('beavers', '0002_status'),
        ]

        operations = [
            migrations.RunPython(populate_status),
        ]


Then add a field 'status' in our model ``Beaver`` : ::

    from django.db.models import CharField, DateField, ForeignKey  # <- NEW
    from django.urls import reverse
    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.models import CremeEntity, CREME_REPLACE

    from .status import Status  # <- NEW


    class Beaver(CremeEntity):
        name     = CharField(_('Name'), max_length=100)
        birthday = DateField(_('Birthday'))
        status   = ForeignKey(Status, verbose_name=_('Status'), on_delete=CREME_REPLACE)  # <- NEW

        [....]


**Remark** : we use a special Creme value for the attribute ``on_delete`` :
``CREME_REPLACE``. This value is equivalent to the classical Django's
``PROTECT``, but in the configuration interface, if you delete a status value,
Creme will propose to replace this value in the instances of ``Beaver`` which
use it.

- There is too ``CREME_REPLACE_NULL`` which is equivalent to ``SET_NULL`` and
  will propose also a choice ``null`` for the concerned ``ForeignKey``.
- The classical values (``PROTECT``, ``SET_NULL`` …) work of course.

We now have to create the corresponding migration (no ``empty`` parameter since
it's a schema migration) : ::

    > python creme/manage.py makemigrations beavers
    You are trying to add a non-nullable field 'status' to beaver without a default; we can't do that (the database needs something to populate existing rows).
    Please select a fix:
    1) Provide a one-off default now (will be set on all existing rows)
    2) Quit, and let me add a default in models.py
    Select an option:

We anticipated this question, and so we can choose the option 1, then give the
default value "1" (because it's the ID of the ``Status`` created in the
previous migration).

We can now run our migrations : ::

    > python creme/manage.py migrate

By re-starting the server, when we add a beaver, we get a new field in the form
as expected. But only one choice of ``Status`` is available, it's not very useful.

First, we are going to improve our ``populate.py``, by creating some status at
deployment. So the users will get immediately several choices os status. In the
file ``beavers/constants.py``, we add some constants : ::

    # -*- coding: utf-8 -*-

    [...]

    STATUS_HEALTHY = 1
    STATUS_SICK = 2


We use these constants right now ; edit ``populate.py`` : ::

    [...]
    from .constants import STATUS_HEALTHY, STATUS_SICK
    from .models import Beaver, Status


    def populate(self):
        [...]

        already_populated = Status.objects.exists()

        if not already_populated:
            Status.objects.create(id=STATUS_HEALTHY, name=_('Healthy'), is_custom=False)
            Status.objects.create(id=STATUS_SICK,    name=_('Sick'),    is_custom=False)


By setting the attribute ``is_custom`` to ``False``, we make these 2 ``Status``
not deletable. The constants we added just before are the PKs of the 2 objects
``Status`` we create ; so we can easily retrieve these instances of ``Status``
later.

With the variable ``already_populated``, we are sure that les status are created
at first deployement, but if users modify the names of status in the
configuration interface, their modifications won't be overridden during an
update (and so a run of the command ``creme_populate``).

Run the command again : ::

    > python creme/manage.py creme_populate beavers


The creation form for Beaver propose these 2 new status.

The last thing is to indicate to Creme to manage this model in its
configuration. Once again, we have to add a method to our file
``beavers/apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_creme_config(self, config_registry):
            from . import models

            config_registry.register_model(models.Status)


If you go to 'General configuration' portal, in the
'Applications portals', the section 'Beavers configuration portal' has
appeared: it allows us to create new ``Status`` as expected.

**Going further** : you can specify the forms to use to create or edit status
if the ones which are automatically generated are not adapted. I could happen
with a business rule which cannot be described with regular model constraints
(like ``nullable``) : ::

    [...]

    config_registry.register_model(
        models.Status,
    ).creation(
        form_class=MyStatusCreationForm,
    ).edition(
        form_class=MyStatusEditionForm,
    )


You can customize the creation/edition URLs too (argument
"url_name" of the methods ``creation()/edition()``), and also the brick
which manage this model (method ``brick_class()``).

**A bit further** : if you want the **users can choose the order** of the
statuses (in forms, in list-views quick-search etc…), you have to add a field
``order`` like that : ::

    # -*- coding: utf-8 -*-

    [...]

    from creme.creme_core.models import CremeModel
    from creme.creme_core.models.fields import BasicAutoField  # <- NEW


    class Status(CremeModel):
        name      = CharField(_('Name'), max_length=100, unique=True)
        is_custom = BooleanField(default=True).set_tags(viewable=False)
        order     = BasicAutoField(_('Order'))  # <- NEW

        [...]

        class Meta:
            app_label = 'beavers'
            verbose_name = _('Beaver status')
            verbose_name_plural  = _('Beaver status')
            ordering = ('order',)  # <- NEW


Notice that a ``BasicAutoField`` is not editable and not visible by default,
and it manages automatically its incrementation, so you should normally don't have
to mind about this field.


Make our model appear in the quick search as best result
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We previously configured the fields to use when searching in our instances of
Beaver ; so when we launch a global search (up-right corner in the menu bar),
and we go in «All results», the found beavers (if there are some) are in a
result bloc.

If you want beavers to appear more often in the quick results (the list of
results displayed in real-time when you enter text in the search field) as best
result, you must set a high valer to the attribute ``search_score`` of your
model ``Beaver``. In Creme, by default, the model ``Contact`` gets a value of
101. So if you set a higher score, when a searched string is found in (at
least) one contact and one beaver, the beaver will be privileged, and it will
appear as best result : ::

    [...]

    class Beaver(CremeEntity):
        [...]

        search_score = 200


New types of relationship
~~~~~~~~~~~~~~~~~~~~~~~~~

Of course, you can create new types of relationship with the configuration
interface (Menu > Configuration > Types of relationship), then use them to link
some entities, filter in list-views, create some bricks related to this type…

If we want some types to be available just after the deplaoyment, the good way
is to create them in our script ``beavers/populate.py``. We are going to create
a type of relationship linking a veterinary (contact) and a beaver ; indeed we
create 2 types which are symmetrical : «the beaver gets as veterinary» et
«the veterinary takes care of the beaver».

First, we edit ``beavers/constants.py`` to add the 2 primary key : ::

    [...]

    REL_SUB_HAS_VET = 'beavers-subject_has_veterinary'
    REL_OBJ_HAS_VET = 'beavers-object_has_veterinary'


**Important** : your keys must follow this rules :

 - Starting by the name of your app, in order to avoid collision with types
   defined by other apps.
 - Then, one of the 2 keys must continue with '-subject_', and the other
   '-object_', so the configuration can distinguish the main meaning from the
   second one.
 - At the end, there is an arbitrary string (ideally it "describes" the type),
   which should be identical in the 2 symmetrical types, for consistency reason.

Then ``beavers/populate.py`` : ::

    [...]
    from creme.creme_core.models import RelationType

    [...]
    from creme import persons

    [...]
    from . import constants


    def populate(self):
        [...]

        Contact = persons.get_contact_model()

        RelationType.create(
            (constants.REL_SUB_HAS_VET, _('has veterinary'),       [Beaver]),
            (constants.REL_OBJ_HAS_VET, _('is the veterinary of'), [Contact]),
        )


**Notes** : we set constraints on entity types which can link (Beaver and
Contact here). We could also, if we'd create a property type «is a veterinary»
(for Contacts), set an additional constraint : ::

        RelationType.create(
            (constants.REL_SUB_HAS_VET, _('has veterinary'),       [Beaver]),
            (constants.REL_OBJ_HAS_VET, _('is the veterinary of'), [Contact], [VeterinaryPType]),
        )

The created types of relationship cannot be deleted from the configuration UI
(the argument ``is_custom`` of ``RelationType.create()`` is ``False`` by
default), which is generally a good thing.

**Going a bit further** : in some cases, we want to control precisely the
creation and the deletion of the relationships with a given type, because of
some business logic. For example, one the entities to link must have a
particular value in a field, or only some users are allowed to delete these
relationships. The solution is to declare these types as internal ;
the generic creation and deletion views for relationships ignore these kind of
types : ::

        RelationType.create(
            (constants.REL_SUB_HAS_VET, _('has veterinary'),       [Beaver]),
            (constants.REL_OBJ_HAS_VET, _('is the veterinary of'), [Contact]),
            is_internal=True,
        )

So you have to write the creation and deletion codes for these types.
Typically, for the creation, we create the relationship in the creation form
of an entity fiche (eg: we assign a veterinary during the beaver creation), or
in a specific view (eg: a brick which displays related veterinaries, and which
allow to add/remove ones).


Using bricks
~~~~~~~~~~~~

*This is a simple introduction. Bricks are a big part of Creme and explaining
all their details would need a complete document.*

Some general explanations
*************************

**Configurability** : if your brick is intended to be displayed on a detailed
view or on home views, the brick should be configurable. It means that in the
bricks configuration (Menu > Configuration > Blocks), the users can define the
presence and the position of your brick. So, this one must provides some
information to configuration UI, like its name or on which types de fiche the
brick can be displayed on (about detailed views). If your brick is displayed on
a specific view, this one will provide the list of bricks to use ; so the list
will be defined by the code (unless you code customised configuration system
for this view, of course).

**Reloading view** : when a change happens in a brick (eg: the user opened from
this brick a *popup* and did a modification), this brick is reloaded, without
reloading the whole page. If you use a generic view (detailed view or home),
Creme set automatically the reloading URL (it is stored in HTML), which
corresponds to an existing view ; so you have nothing to do. But if you code a
specifi view with some bricks, you could have to code your own reloading view
(if the ones provided by creme_core are not sufficient), and you'll have to
inject the URL in the template context of your page.

**Dependencies** : when a brick is reloaded, there are often other bricks to
reload in order to keep the page consistent (eg: when we add a product line in
an invoice, we reload the total brick too). Creme uses a dependencies system,
which is easy to use by developers, and which give good results.
Each brick declares a list of dependencies. When a brick must be reloaded, all
bricks in the page are inspected, and all briks which have at least one
dependence in common are reloaded too. Most of the time, the dependencies are
given as a list of model (eg: Contact, Organisation) ; these models the ones
containing the data displayed by the brick. But in some more complex use cases
it's possible to generate more clever dependencies.

Example: simple brick in detailed view
**************************************

We going to code a simple brick displaying the birthday and the age of a beaver.
Notice that in the section `Function fields`_ we write a function field which
does the same thing (for the age), but in a re-usable way, notably in a custom
brick ; so it's globally a better way.

Create the file ``creme/beavers/bricks.py`` : ::

    from datetime import date

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.gui.bricks import Brick

    from .models import Beaver


    class BeaverAgeBrick(Brick):
        # ID is used :
        #  - by the configuration to store the position of the brick.
        #  - by the reloading system, to know which brick have to be re-rendered & sent.
        # Once again, we use the app name to guaranty uniqueness.
        id_ = Brick.generate_id('beavers', 'beaver_age')

        # This brick displays data from beavers, so if the data of a beaver are modified by
        # another brick (notably if the birthday is edited) so we want to reload this brick
        # in order its render is up-to-date.
        dependencies = (Beaver,)

        # We create this template just after.
        template_name = 'beavers/bricks/age.html'

        # Name used by the configuration UI to designate this brick.
        verbose_name = _('Age of the beaver')

        # The configuration UI will only propose to set this brick on the beavers's detailed view
        # (NB: do not set this attribute in order to the brick can be displayed on all
        # entity types)
        target_ctypes = (Beaver,)

        # If we define this method, we indicate that the block can be displayed on detailed views
        # (another method is used for home:  home_display()).
        def detailview_display(self, context):
            # The current entity is injected in the context by the view generic.EntityDetail
            # & by the reloading view bricks.reload_detailview().
            beaver = context['object']

            birthday = beaver.birthday

            return self._render(self.get_template_context(
                context,
                age=(date.today().year - birthday.year) if birthday else None,
            ))

Now we add the corresponding template,
``creme/beavers/templates/beavers/bricks/age.html`` : ::

    {% extends 'creme_core/bricks/base/table.html' %}
    {% load i18n creme_bricks %}

    {% comment %}
        The CSS class "beavers-age-brick" is not indispensable, it just permits
        to modify more easily the look of the brick with a CSS file.
    {% endcomment %}
    {% block brick_extra_class %}{{block.super}} beavers-age-brick{% endblock %}

    {% block brick_header_title %}
        {% brick_header_title title=_('Age') %}
    {% endblock %}

    {# On ne met pas de titre à nos colonnes #}
    {% block brick_table_head %}{% endblock %}

    {# Content: we are in a brick with type 'table', so we use <tr>/<td> #}
    {% block brick_table_rows %}
        <tr>
            <td>
                <h1 class="beavers-birthday beavers-birthday-label">{% trans 'Birthday' %}</h1>
            </td>
            <td data-type="date">
                <h1 class="beavers-birthday beavers-birthday-value">{{object.birthday}}</h1>
            </td>
        </tr>
        <tr>
            <td>
                <h1 class="beavers-age beavers-age-label">{% trans 'Age' %}</h1>
            </td>
            <td>
                <h1 class="beavers-age beavers-age-value">
                    {% if not age %}
                        —
                    {% else %}
                        {% blocktrans count year=age %}{{year}} year{% plural %}{{year}} years{% endblocktrans %}
                    {% endif %}
                </h1>
            </td>
        </tr>
    {% endblock %}

In order our brick class is used by Creme, we must register it with ``beavers/apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_bricks(self, brick_registry):
            from . import bricks

            brick_registry.register(bricks.BeaverAgeBrick)

Now the brick is available in the configuration UI of bricks, when we create
or edit a configuration of beavers' detailed view.

If we want the brick to be present in the default configuration (ie: at
deployment), we have to improve our file ``beavers/populate.py`` : ::

    [...]
    from creme.creme_core import bricks as core_bricks
    from creme.creme_core.models import BrickDetailviewLocation

    from .bricks import BeaverAgeBrick
    from .models import Beaver

    def populate(self):
        [...]

        already_populated = Status.objects.exists()

        if not already_populated:
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT
            create_bdl = BrickDetailviewLocation.objects.create_if_needed

            # This is the brick which displays the different fields of beavers
            BrickDetailviewLocation.objects.create_for_model_brick(order=5, zone=LEFT, model=Beaver)

            # These bricks from creme_core are generally present on all detailed view
            create_bdl(brick=core_bricks.CustomFieldsBrick, order=40,  zone=LEFT,  model=Beaver)
            create_bdl(brick=core_bricks.PropertiesBrick,   order=450, zone=LEFT,  model=Beaver)
            create_bdl(brick=core_bricks.RelationsBrick,    order=500, zone=LEFT,  model=Beaver)
            create_bdl(brick=core_bricks.HistoryBrick,      order=30,  zone=RIGHT, model=Beaver)

            # Here our new brick
            create_bdl(brick=BeaverAgeBrick, order=40, zone=RIGHT, model=Beaver)

            # Classically we add the bricks from the app "assistants" too (we check it is installed of course).
            # You can look in an existing Creme app how to do if you're interested...


Using buttons
~~~~~~~~~~~~~

Some buttons can be placed in detailed views, just below the title brick,
where is displayed the entity name. You can can generally choose if these
buttons are displayed or not, by configuration.

We will use this feature to create a ``Ticket`` (from the app *tickets*),
destined to veterinaries, which we can create when a beaver is sick.

We start with a creation view for ``Ticket``. As the button will be placed on
the detailed view of beavers, and when we will create a ticket from the page
of a sick beaver, this ticket references automatically the beaver, we pass
the ID of the beaver in the URL, in order the view can retrieve it.

In a new view file ``beavers/views/ticket.py`` : ::

    # -*- coding: utf-8 -*-

    from django.shortcuts import get_object_or_404
    from django.utils.translation import gettext as _

    from creme.tickets.views.ticket import TicketCreation

    from ..models import Beaver


    class VeterinaryTicketCreation(TicketCreation):
        def get_initial(self):
            initial = super().get_initial()
            initial['title'] = _('Need a veterinary')

            beaver = get_object_or_404(Beaver, id=self.kwargs['beaver_id'])
            self.request.user.has_perm_to_view_or_die(beaver)  # We use the beaver's name just after
            initial['description'] = _('{} is sick.').format(beaver)

            return initial


In ``beavers/urls.py`` : ::

    [...]

    from .views import beaver, ticket  # <- UPDATE

    [...]

        re_path(r'^ticket/add/(?P<beaver_id>\d+)[/]?$',
                ticket.VeterinaryTicketCreation.as_view(),
                name='beavers__create_ticket',
                ),  # <- NEW

    [...]


Let's create the file ``beavers/buttons.py`` (this name is not mandatory, but
it's a convention) : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.gui.button_menu import Button

    from .constants import STATUS_HEALTHY, STATUS_SICK
    from .models import Beaver


    class CreateTicketButton(Button):
        id_           = Button.generate_id('beavers', 'create_ticket')
        verbose_name  = _('Create a ticket to notify that a beaver is sick.')
        template_name = 'beavers/buttons/ticket.html'
        permission    = 'tickets.add_ticket'

        def get_ctypes(self):
            return (Beaver,)

        def ok_4_display(self, entity):
            return (entity.status_id == STATUS_SICK)

        # def render(self, context):
        #     context['variable_name'] = 'VALUE'
        #     return super(CreateTicketButton, self).render(context)


Some explanations :

- The attribute ``permission`` is a string using Django's conventions for
  permissions, with a shape : 'APP-ACTION'.
- The method ``get_ctypes()`` can precise, if it exists, the entity types which
  are compatible with the button : the button will only be proposed in the
  configuration for these types.
- The method ``ok_4_display()`` if it is overridden, like here, permit to
  display the button with some conditions (the button is display if the method
  returns ``True``). In our example we display the button only for beavers with
  status "Sick".
- The mrthod ``render()`` allows you to customise the render, by adding data
  in the template context notably ; an example of code has been kept in
  comments.

Now we write the related template,
``beavers/templates/beavers/buttons/ticket.html`` : ::

    {% load i18n creme_widgets %}
    {% if has_perm %}
        <a class="menu_button menu-button-icon" href="{% url 'beavers__create_ticket' object.id %}">
            {% widget_icon name='ticket' size='instance-button' label=_('Linked ticket') %}
            {% trans 'Notify a veterinary' %}
        </a>
    {% else %}
        <span class="menu_button menu-button-icon forbidden" title="{% trans 'forbidden' %}">
            {% widget_icon name='ticket' size='instance-button' label=_('Linked ticket') %}
            {% trans 'Notify a veterinary' %}
        </span>
    {% endif %}

The variable ``has_perm`` is filled thanks to the attribute ``permission`` of
our button ; we display an inactive button if the user is not allowed to use
the view. Notice that the tag ``<a>`` references an URL which is not associated
to a view (yet).

We have to register our button with other Creme buttons, in order to
*creme_config* could propose it. So we add in ``beavers/apps.py`` the method
``register_buttons()`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_buttons(self, button_registry):  # <- NEW
            from . import buttons

            button_registry.register(buttons.CreateTicketButton)


If we go to the configuration menu (the small gear), then 'Button menu',
and we edit the configuration of a type different of Beaver, our button
is not proposed (as we expected). On the other hand, it is proposed if we
create a configuration for the le type Beaver. Add the button on this new
configuration.

When we go to the page of a sick beaver (ie: with the status "Sick"), the
button is appeared. If we click on it, we get a partially pre-filled form.


Using quick creation
~~~~~~~~~~~~~~~~~~~~

In the menu entry '+ Creation', their is the section 'Quick creation' which
gives the possibility to create some entities with a small popup (and not by
going to a new page with a big form).

The quick creation forms are generally, and for obvious reasons, simplified
versions of the entities forms. For example, the quick creation form for
Organisations has only 2 fields ("name" et "owner").

These forms are also used in some entity selection *widgets*, which allow to
create entities on-the-go.

In ``forms/beaver.py``, add a form class ; it must inherit the class
``CremeEntityQuickForm`` : ::

    [...]

    from creme.creme_core.forms import (
        CremeEntityForm,
        CremeEntityQuickForm,  # <== NEW
    )

    [...]

    class BeaverQuickForm(CremeEntityQuickForm):  # <== NEW
        class Meta(CremeEntityQuickForm.Meta):
            model = Beaver


Then in our ``apps.py``, add the method ``register_quickforms()`` like
that : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_quickforms(self, quickforms_registry):  # <- NEW
            from .forms.beaver import BeaverQuickForm
            from .models import Beaver

            quickforms_registry.register(Beaver, BeaverQuickForm)


**Beware** : register only models inheriting ``CremeEntity``. If you register
other types of classes, only super-users will see these entries (because the
credentials checking are avoided for them). It's an UI choice and an
implementation limitation ; it could change in the future.


CustomForms
~~~~~~~~~~~

As seen with the development of our first views with a form, Creme uses
generally for its own entity types some forms which users can configure
with a GUI : customisable forms (CustomForms).

Let's add a simple CustomForm to create our beavers. First, in the root of our
app (ie: ``beavers/``), we create le file ``custom_forms.py`` : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.gui.custom_form import CustomFormDescriptor

    from .models import Beaver

    BEAVER_CREATION_CFORM = CustomFormDescriptor(
        id='beavers-beaver_creation',
        model=Beaver,
        verbose_name=_('Creation form for beaver'),
    )

Be careful and give it a unique identifier ; by prefixing it with the app name
we should be safe. In our file ``populate.py``, we indicate the fields used by
the default configuration of our CustomForm : ::

    [...]

    from creme.creme_core.gui.custom_form import EntityCellCustomFormSpecial
    from creme.creme_core.models import CustomFormConfigItem

    from . import custom forms


    class Populator(BasePopulator):
        [...]

        def populate(self):
            [...]

            CustomFormConfigItem.objects.create_if_needed(
                descriptor=custom_forms.TICKET_CREATION_CFORM,
                groups_desc=[
                    {
                        'name': _('General information'),
                        'cells': [
                            # NB: adapt depending of the fields of your model of course
                            (EntityCellRegularField, {'name': 'user'}),
                            (EntityCellRegularField, {'name': 'name'}),
                            (EntityCellRegularField, {'name': 'birthday'}),
                            (EntityCellRegularField, {'name': 'status'}),
                            (EntityCellRegularField, {'name': 'description'}),
                        ],
                    }, {
                        'name': _('Properties'),
                        'cells': [
                            (
                                EntityCellCustomFormSpecial,
                                {'name': EntityCellCustomFormSpecial.CREME_PROPERTIES},
                            ),
                        ],
                    }, {
                        'name': _('Relationships'),
                        'cells': [
                            (
                                EntityCellCustomFormSpecial,
                                {'name': EntityCellCustomFormSpecial.RELATIONS},
                            ),
                        ],
                    },
                ],
        )

Then, we declare our form descriptor ; in our file ``beavers/apps.py``, we add
a new method : ::


    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_custom_forms(self, cform_registry):
            from . import custom_forms

            cform_registry.register(custom_forms.BEAVER_CREATION_CFORM)


If you run the command ``creme_populate``, you should get your form in the list
of configurable form (Menu > Configuration > Custom forms), related to your model.

The last thing is to modify our creation view, in order it uses our
CustomForm ; edit ``views/beaver.py`` : ::

    [...]

    from .. import custom_forms

    class BeaverCreation(generic.EntityCreation):
        model = Beaver
        form_class = custom_forms.BEAVER_CREATION_CFORM  # <== NEW


Now our creation view should use the configuration you gave to the form.

**Going a bit further** : there are several ways to make more specific treatments
in a Customform, using some attributes of ``CustomFormDescriptor`` :

- you can exclude fields with the attribute ``excluded_fields``.
- you can specify the base class the generated form will use with the
  attribute ``base_form_class``. Beware the class you pass must inherit the
  classe ``creme_core.forms.base.CremeEntityForm``, and it should avoid to
  define any fields (the idea is to put code in the methods``clean()`` or
  ``save()``).
- it's possible to add special fields, which does not necessarily correspond to
  model fields, with the attribute ``extra_sub_cells``. For example, the app
  ``products`` uses it to generate a field which manages the
  categories/sub-categories.
- it's even possible to declarer whole special groups (which are not
  configurable, and will just be present or not, depending on the
  configuration) with the attribute ``extra_group_classes``. You should use
  this solution in last resort (use the previous solutions if you can). But if
  you really need to, you can look at the app ``persons`` which uses it for the
  block "Addresses".


Function fields
~~~~~~~~~~~~~~~

They are fields which does not exist in data base, and which can compute
results or perform queries in order to show useful information to users. They
are available in list-views and in custom bricks.

In our example, the function field display the age of a beaver. Add a file
``function_fields.py`` : ::

    from datetime import date

    from django.utils.translation import gettext_lazy as _, gettext

    from creme.creme_core.core.function_field import FunctionField


    class BeaverAgeField(FunctionField):
        name         = 'beavers-age'
        verbose_name = _('Age')

        def __call__(self, entity, user):
            birthday = entity.birthday

            return self.result_type(
                gettext('{} year(s)').format(date.today().year - birthday.year)
                if birthday else
                gettext('N/A')
            )


The attribute ``name`` is used as identifier. The attribute ``verbose_name``
is used for example in the list-view as column title (like the attribute
``verbose_name`` of the model fields for example).

**Note** : the result must have the type ``FunctionFieldResult`` (or one of its
child classes, like ``FunctionFieldDecimal`` or ``FunctionFieldResultsList``),
which is the default value of ``FunctionField.result_type`` ; this type will
allow to format correctly the value, because we could display HTML or export
CSV.

Then in your ``apps.py``, add the method ``register_function_fields()`` like
this : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_function_fields(self, function_field_registry):  # <- NEW
            from . import function_fields

            function_field_registry.register(Beaver, function_fields.BeaverAgeField)


**Notes** : as you give the model related to your function field, it's easy to
expand a model from another app. And as functions fields are inherited, if you
add one to ``CremeEntity``, it will be available for every entity type.

**Going a bit further** : it's possible to put a search field in the column of
list-views corresponding to your ``FunctionField``. Set the class attribute
``search_field_builder`` with a class inheriting
``creme.creme_core.forms.listview.ListViewSearchField``. It's mostly a form
field (with especially a related widget), but its method ``to_python()``
must return an instance of ``django.db.models.query_utils.Q``. You can find
some examples of use in the following files :

- ``creme/creme_core/function_fields.py`` : it searches in the entities having
  a CremeProperty among a list of available CremeProperty.
- ``creme/assistants/function_fields.py`` : it searches in the entities having
  an Alert, through its title.


Search in the list-view
~~~~~~~~~~~~~~~~~~~~~~~

In the previous paragraph, we explained how to code a list-view search related
to function field. Indeed it's possible to do the same thing with every column.
Some search fields are defined by default (see
``creme/creme_core/gui/listview/search.py``), but you can, for example :

- override the existing behaviours.
- define the behaviours for your own class of model fields.

You'll have to create a class inheriting
``creme.creme_core.forms.listview.ListViewSearchField`` (recall: it's a form
field which generate an instance of ``django.db.models.query_utils.Q``). This
class must be registered into Creme, with the method
``register_search_fields()`` in your ``apps.py``.

**Example** : in the app ``persons``, the behaviour of the search for
``ForeignKeys`` related to the model ``Address`` has been customised, in order
to search in the sub-fields of ``Address`` instances.

The search field is defined in ``creme/persons/forms/listview.py`` : ::

    from django.db.models.query_utils import Q

    from creme.creme_core.forms import listview

    # We inherit the base class for search fields.
    class AddressFKField(listview.ListViewSearchField):

        # We want an simple text <input> as widget.
        widget = listview.TextLVSWidget

        def to_python(self, value):
            # We manage empty search case.
            if not value:
                return Q()

            [...]

            # Notice the attribute "cell" with type 'creme_core.core.entity_cell.EntityCell' ;
            # it's used here to get the name of the 'ForeignKey'.
            fk_name = self.cell.value

            # We build our instance of Q(), and return it
            q = Q()
            for fname in address_field_names:
                q |= Q(**{f'{fk_name}__{fname}__icontains': value})

            return q


In ``creme/persons/apps.py``, we register the search field : ::

    class PersonsConfig(CremeAppConfig):
        [...]

        def register_search_fields(self, search_field_registry):
            from django.db.models import ForeignKey

            from creme.creme_core.core.entity_cell import EntityCellRegularField

            from .forms.listview import AddressFKField

            # 'search_field_registry' is a tree registry ; we retrieve in the following order:
            #  - the sub-registry for regular fields.
            #  - the sub-registry for 'ForeignKeys'.
            # Then we declare our search field is related to the model 'Address'.
            search_field_registry[EntityCellRegularField.type_id]\
                                 .builder_4_model_field_type(ForeignKey)\
                                 .register_related_model(model=self.Address,
                                                         sfield_builder=AddressFKField,
                                                        )


Actions in the list-view
~~~~~~~~~~~~~~~~~~~~~~~~

In list-views, there is a column to trigger some actions (eg: clone an entity).
On each line, we find a menu to make actions related to the entity
corresponding to this line ; and in the list header there is a menu with
actions that use several entities in the same time.

You can code your own actions ; they can be available for all entities (by
associating them to the model ``CremeEntity``) or for a specific type like
beavers.

In this example, imagine we already have a view which generates barcode (as an
downloaded image) corresponding to a beaver ; then we create an action to
download the barcode from the actions menu of a beaver in the list-view.

Add a file ``actions.py`` in our app : ::

    from django.urls.base import reverse
    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.gui.actions import UIAction

    from creme.beavers.models import Beaver


    class GenerateBarCodeAction(UIAction):
        id = UIAction.generate_id('beavers', 'barcode')
        model = Beaver

        type = 'redirect'
        url_name = 'beavers__barcode'

        label = _('Generate a bar code')
        icon = 'download'

        @property
        def url(self):
            return reverse(self.url_name, args=(self.instance.id,))

        @property
        def is_enabled(self):
            return self.user.has_perm_to_view(self.instance)


Some explanations :

- ``id`` : must be unique (among the actions), and as usual it's used during
  registration of the action to retrieve it later.
- ``model`` : model for which the action is available. Here we set our specific
  model, because our action does not mean anything for other types of entity.
- ``type`` : it determines the behaviour of the action in the UI. To create a
  new type you need to write some JavaScript (we'll avoid that to keep this
  example simple). Here, the type "download" is a base type which redirect
  to an URL (so it's often used).
- ``icon`` :  name of the icon to use with ``label`` in the GUI ;
  beware the final file name is generated by Creme, like "download_22.png".
- ``is_enabled()`` : if ``False`` is returned, the entry is disabled.

**Notes** : the view named "beavers__barcode" remains to be coded of course,
but its not the objective of this example.

The last thing is to declare our action in our ``apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_actions(self, actions_registry):  # <- NEW
            from . import actions

            actions_registry.register_instance_actions(
                actions.GenerateBarCodeAction,
            )


**Going a bit further** : to code an action managing several entities at once,
an action class must inherit ``creme.creme_core.gui.actions.UIAction``
and must be registered with ``actions_registry.register_bulk_actions``.


Modifying existing apps
~~~~~~~~~~~~~~~~~~~~~~~

It's a common need to modify the behaviour of existing apps. Many companies
code their own CRM because it's hard for this kind of software to manage all
specific use cases.

The fact than you can directly modify the code of Creme is of course a good
thing ; whichever the modification you want, it will be possible with this way
(while mechanisms presented below will always have limits).

Moreover, if it's possible, you should use the tools proposed by
Creme/Django/Python (in this order of priority) to modify the code of existing
apps from your own code. So the design will remain modular and upgrade of Creme
will be easier.

By the way, it's a really good idea to write unit tests
(`Unit tests and tests driven development`_) to check your new behaviours
(particularly when you upgrade the version of Creme) ; in practice you can copy
the existing unit tests for modified code in your own tests files, and just
modify the copies as you wish (instead of coding them from scratch).


General approaches
******************

**Monkey patching** : this way is quite brutal and should be used carefully,
and avoided whenever it's possible.
Thanks to Python's dynamism, it's possible to override some elements of another
module.
For example, in ``creme/creme_core/apps.py``, we find this code which modifies
the method ``ForeignKey.formfield()`` (defined in Django) : ::

    [...]

    class CremeCoreConfig(CremeAppConfig):
        [...]

        @staticmethod
        def hook_fk_formfield():
            from django.db.models import ForeignKey

            from .models import CremeEntity

            from creme.creme_config.forms.fields import CreatorModelChoiceField

            # Here we store the original method...
            original_fk_formfield = ForeignKey.formfield

            def new_fk_formfield(self, **kwargs):
                [...]

                defaults = {'form_class': CreatorModelChoiceField}
                defaults.update(kwargs)

                # ... that we call here.
                return original_fk_formfield(self, **defaults)

            ForeignKey.formfield = new_fk_formfield  # We override with our own method.


**Global variables & class attributes** : the code of Creme/Django is often
designed to be easily modified from outside, without needing a complex API. You
just have to look the source code and understand it.
For example, dans les classes des champs de formulaire, le *widget* associé
est construit en utilisant la classe présente dans le bien nommé attribut ``widget``.
Il est alors facile de le modifier ; voici du code que l'on trouve à nouveau
dans ``creme/creme_core/apps.py`` : ::

    [...]

    class CremeCoreConfig(CremeAppConfig):
        [...]

        @staticmethod
        def hook_datetime_widgets():
            from django import forms

            from creme.creme_core.forms import widgets

            # We set the Creme widgets as default widgets. So, when a form is
            # generated from a model, the widgets are automatically the "right" ones.
            forms.DateField.widget     = widgets.CalendarWidget
            forms.DateTimeField.widget = widgets.DateTimeWidget
            forms.TimeField.widget     = widgets.TimeWidget

We could do the same thing with the class attributes of views (we are only
talking about class-based views, not functions ones of course).

In a global manner, behaviours in Creme are often stored in global
dictionaries, instead of ``if ... elif ... elif ...`` blocks. so it's easy to
add, remove or modify these behaviours.

**AppConfig** : Django allows, in the variable ``settings.INSTALLED_APPS``,
to sprcify the class of AppConfig used by an app.
Imagine you want to remove all the activities' statistics from the statistics
brick (see `Statistics brick`_). In ``project_settings.py``, perform the
following modification : ::

    INSTALLED_CREME_APPS = (
        [...]

        # 'creme.activities',  # replaced by:
        'creme.beavers.apps.BeaversActivitiesConfig',
        [...]
    )

Then in ``creme/beavers/apps.py``, we create effectively this configuration
class : ::

    [...]

    from creme.activities.apps import ActivitiesConfig

    # We inherit the original class, to keep all the other methods identical.
    class BeaversActivitiesConfig(ActivitiesConfig):
        def register_statistics(self, statistics_registry):
            pass  # the method does nothing now


Modifying the menu entries of another app
*****************************************

The API of the main menu has been designed to allow easy modification of the
entries from your code. All the following examples should be done in the method
``register_menu()`` of your ``AppConfig``.

Tips: if you to display (in the terminal) the menu's structure, in order to
know the different ID et priorities of ``Item``, use this : ::

    print(str(creme_menu))


**Modify a label** : ::

    creme_menu.get('features', 'persons-directory', 'persons-contacts').label = _('List of contacts')


**Modify the ordre** of an ``Item`` (it works even if the ``Item`` is a
``ContainerItem``) : ::

    creme_menu.get('features', 'persons-directory').change_priority(1, 'persons-contacts')


**Remove some entries** : ::

    creme_menu.get('features', 'persons-directory').remove('persons-contacts', 'commercial-salesmen')


**Move an entrie** from a container to another one. Indeed, we just combine an
adding and a deletion : ::

    features = creme_menu.get('features')
    features.get('activities-main').add(features.get('persons-directory').pop('persons-contacts'))


If you want to re-write the whole menu's code of an app, the best way is to
write your own ``AppConfig`` (as seen before) and to override the method
``register_menu()``.


Hooking forms
*************

In Creme, form classes have 3 methods which allow to change their behaviour
without modifying their code directly :

 - ``add_post_init_callback()``
 - ``add_post_clean_callback()``
 - ``add_post_save_callback()``

They take a function as only parameter ; as their names suggest, these
functions are callbacks, called respectively after the calls to __init__(),
clean() and save(). These callbacks must have only one parameter, the form
instance.

**Notes** : with CustomForms and form classes declared as class attribute of
view classes, hooking regular form classes became quite less useful.

The simplest way to hook the wanted forms is from the file ``apps.py``
of one of your own apps (like *beavers*), in the method ``all_apps_ready()``.
Here an example which adds a field in the creation form for users (notice you
should hook the method ``save()`` too, in order to use this new field ; this
task is left as exercise...) : ::

    # -*- coding: utf-8 -*-

    [...]


    class BeaversConfig(CremeAppConfig):
        name = 'creme.beavers'
        verbose_name = _('Beavers management')
        dependencies = ['creme.creme_core']

        def all_apps_ready(self):
            super(BeaversConfig, self).all_apps_ready()

            from django.forms.fields import BooleanField

            # NB: we perform imports of other apps here to avoid error of loading order
            from creme.creme_config.forms.user import UserAddForm

            def add_my_field(form):
                form.fields['loves_beavers'] = BooleanField(required=False, label=_('Loves beavers?'))

            UserAddForm.add_post_init_callback(add_my_field)

        [...]


**Technical note** : ``all_apps_ready()`` is an improvement from Creme to
Django, which only defines the method ``ready()``. If you need to import
directly or indirectly code from other apps, use ``all_apps_ready()`` rather
than ``ready()`` ; in other cases use ``ready()`` because it's more classical.

**Technical note** : in reason of the moment when *callbacks* are called, it's
possible, depending on the form you are caring about, that you cannot do what
you want (for example get a field created after the call to the callbacks).


Overriding the templates
************************

As seen before, it's possible, to modify from your app the attribute
``template_name`` of class-based views, in order to force a view in another app
to use a template of your app. The advantage is your template could extend the
replaced template ; it's useful when the new template si nearly equal to the
replaced one (it has to use smartly tags ``{% block %}`` of course).

But if if not possible (or wanted), there is another way to make another app
use your own templates : template overriding. You just have to use the Django's
templates loading system.

In your file ``settings.py``, you can find the following variable : ::

    TEMPLATES = [
        {
            ...

            'OPTIONS': {

                ...

                'loaders': [
                    # Don't use cached loader when developing (in your local_settings.py)
                    ('django.template.loaders.cached.Loader',
                        'django.template.loaders.filesystem.Loader',
                        'django.template.loaders.app_directories.Loader',
                    )),
                ],

                ...
            },
        },
    ]


The order of loaders is important ; this order makes the templates present in
the directory ``creme/templates/`` used instead of templates in directories
``templates/`` found in the apps directories.

Example : instead of modifying directly the template
``creme/persons/templates/persons/view_contact.html``, you can put your
modified version in the file ``creme/templates/persons/view_contact.html``.


Overriding labels
*****************

It's a current need to customise some labels ; for example, replace les
occurrences of 'Organisation' by 'Association'.

Run the following command : ::

    > python creme/manage.py i18n_overload -l en organisation Organisation


Then you have to edit the new translation file created in ``locale_overload/``
(it's indicated by the command). In our example, we replace 'Organisation' by
'Association'. Do not forget to remove the lines "#, fuzzy".
Finally, compile these new translations as seen before. In the directory
``locale_overload/`` : ::

    > django-admin.py compilemessages


Modifying an existing model
***************************

Another current need is to modify an existing model, provided by Creme, for
example adding some fields to Contact, or remove ones.

In you want to **add some fields**, the simplest way is to use some CustomFields, which
you add from the configuration GUI. But it's not possible (yet) to add business
logic to these fields, like computing automatically their value for example.

Another way is to create a model in your app, which references the existing
model (``ForeignKey``, ``ManyToManyField``, ``OneToOneField``). This is the
method used by the app ``geolocation`` to extend the addresses from the app
``persons`` with information of geographical localisation. You may have to use
additionally other techniques to get the expected result :

 - Use of Django's signals (``pre_save``, ``post_save`` …).
 - `Hooking forms`_ (vu précédemment)


if you want to **hide some fields**, remind you that lots of fields are
marked as optional, and so they can be hidden thanks to the configuration UI.

**In last resort**, if you really want to modify an existing model, there is the
possibility to swap it. Nonetheless, the model must be swappable ; this is the
case of all classes inheriting ``CremeEntity`` ( ``Contact``, ``Organisation``,
``Activity`` …), and ``Address`` too.

In a first time, we considerate that you want to perform this swapping at the
project beginning ; it means that you don't have a production DB using the model
you want to modify. So, you start the development and you already know that you
want modify this model.

In our example we swap ``tickets.Ticket``.

First, we create an app destined to extend ``tickets`` ; we name it
``my_tickets``. So, we have to do the same things than for theapp ``Beavers`` :
create a directory ``creme/my_tickets/``, containing files ``__init__.py``,
``apps.py``, ``models.py``, ``urls.py`` … This app must be added in
INSTALLED_CREME_APPS ; beware it must be avant ``tickets``.

Our ``AppConfig`` must declare that it extends ``tickets`` : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.apps import CremeAppConfig


    class MyTicketsConfig(CremeAppConfig):
        name = 'creme.my_tickets'
        verbose_name = _('Tickets')
        dependencies = ['creme.tickets']
        extended_app = 'creme.tickets'  # <= HERE !!
        credentials  = CremeAppConfig.CRED_NONE  # <= and HERE !!


In ``models.py``, we must define a model which will replace
``tickets.models.Ticket``. The easier way is to inherit
``tickets.models.AbstractTicket`` (notice that all entity type use a similar
scheme). It's important to keep ``Ticket`` as model name, in order to avoid
lots of annoying behaviours or bugs : ::

    # -*- coding: utf-8 -*-

    from django.db.models import DecimalField
    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.models import CremeModel

    from creme.tickets.models import AbstractTicket


    class Ticket(AbstractTicket):
        estimated_cost = DecimalField(
            _('Estimated cost (€)'), blank=True, null=True, max_digits=10, decimal_places=2,
        )  # <= ADDITIONAL FIELD

        class Meta(AbstractTicket.Meta):
            app_label = 'my_tickets'


In ``settings.py``, found a variable with shape ``<APP>_<MODEL>_MODEL`` ; in
our case this is : ::

    TICKETS_TICKET_MODEL = 'tickets.Ticket'

We override this variable in our file ``project_settings.py`` : ::

    TICKETS_TICKET_MODEL = 'my_tickets.Ticket'

It indicates the concrete class to use instead of ``tickets.Ticket``.

We can now generate the migrations as seen before.

If you look at ``tickets/urls.py``, you can see the way URLs are defined is
sometimes a bit different from the usual way.
For example : ::

    [...]

    urlpatterns += swap_manager.add_group(
        tickets.ticket_model_is_custom,
        Swappable(re_path(r'^tickets[/]?$',                        ticket.TicketsList.as_view(),    name='tickets__list_tickets')),
        Swappable(re_path(r'^ticket/add[/]?$',                     ticket.TicketCreation.as_view(), name='tickets__create_ticket')),
        Swappable(re_path(r'^ticket/edit/(?P<ticket_id>\d+)[/]?$', ticket.TicketEdition.as_view(),  name='tickets__edit_ticket'), check_args=Swappable.INT_ID),
        Swappable(re_path(r'^ticket/(?P<ticket_id>\d+)[/]?$',      ticket.TicketDetail.as_view(),   name='tickets__view_ticket'), check_args=Swappable.INT_ID),
        app_name='tickets',
    ).kept_patterns()

    [...]

These URLs (we can see that ``re_path()`` is called, the code is wrapped in
other calls) are only defined when the model ``Ticket`` is not swapped.

These views cannot respect your business logic ; for example the creation view
can crash if you added in ``my_tickets.Ticket`` a model field which is
mandatory and not editable at the same time. Since we chose to define our own
customised model, we must provide our own URLs which are sure to work.

In our case, the base views should be enough (forms are smart enough to use the
new editable fields), and so you can define ``my_tickets/urls.py`` like : ::

    # -*- coding: utf-8 -*-

    from django.urls import re_path

    from creme.tickets.views import ticket


    urlpatterns += [
        re_path(r'^my_tickets[/]?$',                        ticket.TicketsList.as_view(),    name='tickets__list_tickets'),
        re_path(r'^my_ticket/add[/]?$',                     ticket.TicketCreation.as_view(), name='tickets__create_ticket'),
        re_path(r'^my_ticket/edit/(?P<ticket_id>\d+)[/]?$', ticket.TicketEdition.as_view(),  name='tickets__edit_ticket'),
        re_path(r'^my_ticket/(?P<ticket_id>\d+)[/]?$',      ticket.TicketDetail.as_view(),   name='tickets__view_ticket'),
    ]

**Note** : the most important is to define URLs with the same name (used by
``reverse()``), and the same arguments ("ticket_id" here). To avoid errors,
Creme checks at starting that all swapped URLs have been defined elsewhere.

In the most complex cases, you'll probably want to use your own forms or
templates. You may have to define your own views. Try to avoid "copy/paste"
each time it's possible ; the base apps provide class-based views which can
easily be extended. For example, if you want to define the creation view
``my_tickets.Ticket`` with your own form (writing it won't be treated, you
already know how to do), you could write something like that : ::

    # -*- coding: utf-8 -*-

    from creme.tickets.views.ticket import TicketCreation

    from creme.my_tickets.forms import MyTicketForm  # <= to be writen !


    class TicketCreation(TicketCreation):
        form_class = MyTicketForm


**Going a bit further** : you've maybe noticed that in ``settings.py`` there
are variable looking like forme ``<APP>_<MODEL>_FORCE_NOT_CUSTOM``
(for example ``TICKETS_TICKET_FORCE_NOT_CUSTOM``). As seen before, it's better
to swap before the creation of the data base. But you could think that a model
will be swapped in the future, without being sure about that. And even by swapping
it immediately, you could have not enough time to code its views. The variables
``*_FORCE_NOT_CUSTOM`` are useful in this case. You can swap some model as a
precaution, but force Creme to considerate these models as not customised ;
so 'normal' views (and unit tests too) will be used anyway. Nevertheless, you
must be careful and use only models which are identical to the base model
(eg: just inherit from abstract models). Otherwise, the base views may work
not correctly. So use these variables carefully.

**How-to swap a model in a second time?** imagine you have a production
instance of Creme, and then you realise that to do want you want you have to
swap a model (ie: it's the not swapped version of this model which is currently
used in your code/DB).

Beware! You should test the following step on a copy of your production DB, and
always have a backup before applying modifications (it's a general advice, but
it's particularly true with the tricky following manipulations).


#. Write a swapping model (in your own app of course), which must be
   **exactly identical** to the model used in DB. Indeed, you just have to
   inherit the corresponding abstract model (eg: ``AbstractTicket``)
   **with no new field** (yet).

#. Edit the setting ``<APP>_<MODEL>_MODEL`` to reference your model.

#. Beware, it's the trickiest step: rename the table corresponding to the base
   model (with PHPMyAdmin or pgAdmin for example), by giving it the name Django
   Django would give to the table of your model. The important thing is to
   follow the Django's convention. In the tickets' example we seen before,, it
   means rename the table "tickets_ticket" into "my_tickets_ticket". Normally,
   the modern RDBMS do a nice job, and the related constraints (like the
   ForeignKeys to this table) are correctly modified. But some old versions of
   MySQL seem to keep broken constraints, so it's important to test with an
   environment identical to your production environment.

#. Modify, in the table "django_content_type" the line corresponding to the
   model. Eg: the line app_label="tickets"/model="ticket" should now contain
   app_label="my_tickets" (model="ticket" does not change if you kept
   ``Ticket`` like recommended).

#. Generate the migration for your new model. nonetheless, like the table
   already exist in the base, we have to 'fake' this migration : ::

        > python creme/manage.py migrate my_tickets --fake-initial

#. As seen before, you have to manage the views of your new model.


Overriding existing URLs
************************

Imagine you want to make an existing URL to correspond to one of your view.
As seen before, when you swap a model, you have to re-define some of its
related views (creation, list-view, etc…) ; you could be in a different use
case :

- you did not swap the concerned model, and don't want to just to modify a view.
- the concerned view is not one of the views which have to be re-defined when
  swapping a model.

**Remark**: with class-based views, there are (as seen before), many ways to
modify an existing view from your app, without needing to re-write it totally.

As URLs are named in the differents ``urls.py``, if your app is installed
before the app (ie: in ``settings.INSTALLED_CREME_APPS``) which contains the
URL you want to redirect to your own view, you jst have to declare an URL with
the same name (and with the same arguments). Creme always retrieve URLs by
their name, so your URL will be used.

In this example, we modify the creation view for memo. In
``creme/assistants/urls.py``, we find this code : ::

    [...]

    urlpatterns = [
        re_path(
            r'^memo/',
            include([
                re_path(
                    r'^add/(?P<entity_id>\d+)[/]?$',
                    memo.MemoCreation.as_view(),
                    name='assistants__create_memo',
                ),
                [...]
            ])),

        [...]
    ]


In your app (which must be before ``creme.assistants.py`` in
``settings.INSTALLED_CREME_APPS``), declare this URL : ::

    urlpatterns = [
        re_path(
            r'^my_memo/add/(?P<entity_id>\d+)[/]?$',
            views.MyMemoCreation.as_view(),
            name='assistants__create_memo',
        ),

        [...]
    ]

It works well, but there is a potential issue: the original URL still exists
(it's just not used in the GUI). It means we can still reach the masked view.
It could happen with an external une application software which does has not
been modified to use the new URL, or with a malicious user. So if the masked
view allows some actions which should be forbidden (your own view performs some
additional checking), and is not just a new UI, we must improve our solution,
by using exactly the same URL (not only its name in Creme).

By default, the URLs in your app start by the app's name nom. But we can give
explicitly this prefix, to use the same than the app ``assistants``. It will
impact all URLs in your app, so it's better to write a small app which is use
only for this job. Create an app ``my_assistants`` ; in its file
``my_assistants/apps.py``, set the URL prefix like : ::

    [...]

    class MyAssistantsConfig(CremeAppConfig):
        name = 'creme.my_assistants'

        @property
        def url_root(self):
            return 'assistants/'

        [...]


Then in ``my_assistants/urls.py`` : ::

    from django.urls import re_path

    from . import views

    urlpatterns = [
        # Notice the URL must be the same than the original one.
        # In our case, not 'my_memo/', replaced by a 'memo/' as in "assistants"
        re_path(
            r'^memo/add/(?P<entity_id>\d+)[/]?$',
            views.MyMemoCreation.as_view(),
            name='assistants__create_memo',
        ),
    ]


This method remains fragile, because if the masked URL changes in a future
(major) version of Creme, your view does not mask it anymore without
triggering error (the 2 URLs just cohabit). So you must use this method
carefully, and be careful when you upgrade Creme.

**Specific case: removing a feature**: in some case you may want to disable an
existing base view. For example, you want Memos to be only created by a Job
which import then from an ERP system. To make this task correctly the creation
views for Memos cannot be reached.

So you should too remove menu entries and buttons which redirect to these
creation views, in order to get a clean UI without useless element ; these
things are treated in other parts of this document.

Creme provides a generic view which returns an error page to the user : ::

    from django.urls import re_path

    from creme.creme_core.views.generic.placeholder import ErrorView

    urlpatterns = [
        re_path(
            r'^memo/add/(?P<entity_id>\d+)[/]?$',
            ErrorView.as_view(message='Memo are only created by ERP.'),
            name='assistants__create_memo',
        ),
    ]



Further with models: Tags
~~~~~~~~~~~~~~~~~~~~~~~~~

Creme provides a tag system for model fields in order ta add them semantic, and
have a more precise behaviour for some services. Currently, it's not possible
to create its own tags.

Example of use (with 2 tags configured at once) : ::

    [...]

    class Beaver(CremeEntity):
        [...]
        internal_data = CharField('Data', max_length=100).set_tags(viewable=False, clonable=False)


List of tags and their related feature:

 - ``viewable``: classical fields (``IntegerField``, ``TextField``, …) are
   visible to the users. Sometimes, we want to store internal information that
   users should not see. Set this tag to ``False``, and it will be hidden
   everywhere.
 - ``clonable``: by setting this tag to ``False``, the field's value is not
   copied when the entity is cloned.
 - ``optional``: by setting this tag to ``True``, the field can be hidden by
   users in the fields' configuration UI ; the field is then removed from
   forms. It's obvious that this field does not need to be fille by form
   without causing an error ; for example it could be ``nullable`` or having a
   value for ``default``.
 - ``enumerable``: when a ``ForeignKey`` gets thsi tag with a ``False`` value,
   (default value is ``True``), Creme knows this FK could take an infinity of
   values, and so these values should never be proposed as choices, in filters
   for example.


Edition of a single field
~~~~~~~~~~~~~~~~~~~~~~~~~

All fields declared as ``editable=True`` in your entity models (it's the
default value) can be edited in the related detailed views, from the
information bricks (and in list-views too). A not editable cannot be edited
this way.

Sometimes, you want some fields are present in the creation form of your
entity, but you exclude then from the edition form (attribute ``exclude`` of
the class ``Meta`` in the form). In the same manner, you could want to avoid
the edition of some fields in the detailed view : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_bulk_update(self, bulk_update_registry):
            bulk_update_registry.register(
                Beaver,
                exclude=['my_field1','my_field2'],
            )

If you want to customise th edition form for a particular field, because it has
some business logic for example : ::


    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_bulk_update(self, bulk_update_registry):
            from .forms.my_field import MyBulkEditForm

            bulk_update_registry.register(
                Beaver,
                innerforms={'my_field3': MyBulkEditForm},
            )


The forms passed as parameter must inherit
``creme.creme_core.forms.bulk.BulkForm`` (``BulkDefaultEditForm`` is often a
good choice as parent class).


Entity cloning
~~~~~~~~~~~~~~

By default, entities can be cloned. If you want a model cannot be cloned,
define its following method : ::

    class Beaver(CremeEntity):
        [...]

        @staticmethod
        def get_clone_absolute_url():
            return ''


If you want to managed cloning with a better granularity, you have the tag
``clonable`` seen previously, and you can override the following methods :

 - ``_pre_save_clone(self, source)`` (preferred)
 - ``_post_save_clone(self, source)`` (preferred)
 - ``_post_clone(self, source)`` (preferred)
 - ``_clone_m2m(self, source)``
 - ``_clone_object(self)``
 - ``_copy_properties(self, source)``
 - ``_copy_relations(self, source, allowed_internal=())``
 - ``clone(self)``


Import of CSV files
~~~~~~~~~~~~~~~~~~~

If you want to enable CSV/XLS import for your entity model, you have to add
this in your ``apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_mass_import(self, import_form_registry):
            import_form_registry.register(Beaver)


So the import form will be automatically generated. If you want to customise
this form, look at the code of apps ``persons``, ``activities`` or
``opportunities`` (it's out of the scope of this tutorial).


Merging 2 entities
~~~~~~~~~~~~~~~~~~

To enable the merging of your entity type, look how the apps ``persons`` or
``document`` do, in the method ``register_merge_forms()`` of ``apps.py`` (it's
out of the scope of this tutorial).

**Notes** : if you created a model related to an entity type which can be
merged, you can control more precisely what happens during the merge thanks to
the signals ``creme.creme_core.signals.pre_merge_related`` and
``creme.creme_core.signals.pre_replace_related``. and if your model is linked
through a OneToOneField, you **must** manage the merge, because Creme cannot
manage automatically the case where the 2 merged entities are linked (one of
the 2 linked instances has to be removed, and some of the information may be
stored in the other one etc…).


SettingValues
~~~~~~~~~~~~~

This feature allow users to fill some typed values through a configuration UI
(contrarily to values in ``settings.py`` which can only be changed by the
administrator), in order to the code behave specifically depending of the
values.


Global settings
***************

The model ``SettingValue`` allow to retrieve some global values, ie their are
used for all the users.

In your file ``constants.py`` define the identifier of the setting key : ::

    BEAVER_KEY_ID = 'beavers-my_key'


As usual, you should prefix with the app's name, in order to avoid collisions
with keys in others apps ; so to guaranty uniqueness. If the key is not unique
an exception is raised at start.

In a new file ``setting_keys.py`` at your app's root : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.core.setting_key import SettingKey

    from .constants import BEAVER_KEY_ID


    beaver_key = SettingKey(
        id=BEAVER_KEY_ID,
        description=_('*Set a description here*'),
        app_label='beavers',
        type=SettingKey.BOOL,
    )

We've just created a boolean value. Other available types are :

 - STRING
 - INT
 - BOOL
 - HOUR
 - EMAIL


In ``populate.py``, we now create the related instance of ``SettingValue``, and
we set its default value : ::

    [...]

    from creme.creme_core.models import SettingValue

    from .setting_keys import beaver_key


    class Populator(BasePopulator):
        [...]

        def populate(self):
            [...]

            SettingValue.objects.get_or_create(key_id=beaver_key.id, defaults={'value': True})


Now we register the key in Creme. In ``apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_setting_key(self, setting_key_registry):
            from .setting_keys import beaver_key

            setting_key_registry.register(beaver_key)


The value can now be set by users in the configuration portal of the app.

And to use the value in your code : ::

    from creme.creme_core.models import SettingValue

    from creme.beavers.constants import BEAVER_KEY_ID


    if SettingValue.objects.get(key_id=BEAVER_KEY_ID).value:
        [...]


User's settings
***************

It's about every user can set its own value.

It's very similar to the previous section(the 2 APIs are voluntarily close in
order to be consistent/simple, ahd share code when it's possible).

In ``beavers/constants.py`` define the key identifier (same remark on
prefix/uniqueness) : ::

    BEAVER_USER_KEY_ID = 'beavers-my_user_key'


In ``setting_keys.py`` at the app's root : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.core.setting_key import UserSettingKey

    from .constants import BEAVER_USER_KEY_ID


    beaver_user_key = UserSettingKey(
        id=BEAVER_USER_KEY_ID,
        description=_('*Set a description here*'),
        app_label='beavers',
        type=UserSettingKey.BOOL,
    )


We do not create an initial value in our ``populate.py``, because users are
generally created after the app's installation.

Register the key in ``apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_user_setting_keys(self, user_setting_key_registry):
            from .setting_keys import beaver_user_key

            user_setting_key_registry.register(beaver_user_key)


The value can now be set by each user in its personal configuration
(Menu > Creme > My settings).

Now you can use the value in your code. Notice that an instance of
``auth.get_user_model()`` must be used ; in this example we write a view and so
we can use ``request.user`` : ::

    [...]

    from .setting_keys import beaver_user_key

    [...]

    @login_required
    def a_view(request):
        [...]

        if request.user.settings.get(beaver_user_key, False):
            [...]


**A bit further** : when you instantiate a SettingKey/UserSettingKey, there is
a parameter ``hidden``, with ``False`` as default value. If this parameter is
``True``, Creme dies not automatically display a configuration UI for this
key ; so you can write a more adapted UI, for example :

  - to validate more finely the input values.
  - to group several keys in a same form.


Statistics brick
~~~~~~~~~~~~~~~~

Il existe depuis Creme 1.7 un bloc qui est capable d'afficher des statistiques,
comme le nombre total de contacts par exemple, sur l'accueil (ou bien la vue
«Ma page»). Dans une installation fraîche de Creme 1.7, ce bloc est présent
dans la configuration de base.

Si vous voulez afficher vos propres statistiques, il faut enregistrer une
fonction qui les génèrent de cette manière dans votre ``apps.py`` : ::


    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_statistics(self, statistics_registry):  # <- NEW
            statistics_registry.register(
                id='beavers-beavers',
                label=Beaver._meta.verbose_name_plural,
                func=lambda: [Beaver.objects.count()],
                perm='beavers',
                priority=10,
            )

Some explanations on parameters :

 - ``id`` : a unique string identifying a statistic, which allows for example
   to delete a statistic from another app. As usual, you should prefix with the
   app's name.
 - ``label`` : the name used in the brick.
 - ``func`` : a function with no argument which returns some objects to
    display ; this function will be called each time the brick is displayed.
   Here it's a list containing a simple integer, but it could contain for
   example ``string`` for more complex values (ex: «50 beavers per km²»).
 - ``perm`` : a permission ``string``, to check if the current user is allowed
   to view the statistic. Generally the permission corresponds to the app
   containing the used models.
 - ``priority`` : integer. Higher the value, higher the statistic is displayed
   in the brick.


Jobs
~~~~

Th job system manages tasks :

 - which take a long time to be completed ; a progress bar is displayed, and
   the user can change the page (or even quit its browser) without stopping the
   job. The job is correctly resumed even if the server crashes (power outage etc…).
   Eg: Creme uses these features to import CSV/XLS.
 - which have to be run periodically (or at least at a given date) without user
   trigger them. It replaces favourably a command associated to CRON rules,
   because the administrator has nothing specific to do (when it
   installs/uninstalls an app for example).
   Eg: Creme uses these features to sent the email campaigns.

Let's write the outline of a Job which performing a daily task which fetch the
health of a beaver, for example by reading a file created by another software
or by using a Web service (this part of the code won't be written here anyway).

First, we create the type of our job, which contains the task's code. Our app
must contains a package ``creme_jobs`` ; if your app get several job types, you
can use a directory ``beavers/creme_jobs/``.
Here we just create a single file ``beavers/creme_jobs.py`` : ::


    # -*- coding: utf-8 -*-

    from django.conf import settings
    from django.utils.translation import gettext_lazy as _, gettext

    from creme.creme_core.creme_jobs.base import JobType


    class _BeaversHealthType(JobType):
        id           = JobType.generate_id('beavers', 'beavers_health')
        verbose_name = _('Check the health of the beavers')
        periodic     = JobType.PERIODIC

        def _execute(self, job):
            [...]
            # put here the code which retrieve data

        def get_description(self, job):
            # You have to return a list of strings ; it is used in the detailed view of the job.
            # Using a list allow to return additional information like the URL of the external API.
            return [
                gettext('Check the health of the beavers by connecting to our health service'),
                gettext('URL is {}').format(settings.BEAVERS_HEALTH_URL),
            ]


    beavers_health_type = _BeaversHealthType()

    # Your package MUST contains a variable "jobs" which is a sequence
    # with instances of your types.
    # Creme fetches this variable to know the types of jobs.
    jobs = (beavers_health_type,)

**Explanations** : we define here a type of Job, which will be used by some
instances of ``creme_core.models.Job``.
As usual, we create an identifier (attribute ``id``) for our class which is
used to retrieve it from string in DB. The field ``verbose_name`` is used in
the UI to represent our job (in the list of jobs for example). The attribute
``periodic`` indicates the type of periodicity of this job type ; the value
can be :

 - ``JobType.NOT_PERIODIC`` : instances of ``Job`` with this value are created
   on-the-go, then run once as soon as possible by the jobs manager. For
   example, the CSV import works like that ; each import generates a ``Job``
   which contain all needed data (filled by the import form).
 - ``JobType.PERIODIC`` : only one instance of ``Job`` can have this type ;
   it should be created in ``populate.py`` (see after) and will be deleted when
   uninstalling the corresponding app. The job is run periodically.
   Eg: consulting an inbox, if a file is present through FTP…
 - ``JobType.PSEUDO_PERIODIC`` : as in the previous case, there is only one
   instance of ``Job`` ; it is run depending of the data stored in the DB and
   which define the next run. For example, if a job have to send e-mails
   in 17 hours then in 3 days.

As we created a periodic job, we must create the instance of ``Job`` in our
``populate.py`` : ::

    from django.conf import settings

    from creme.creme_core.management.commands.creme_populate import BasePopulator
    from creme.creme_core.models import Job
    from creme.creme_core.utils.date_period import date_period_registry
    [...]

    from .creme_jobs import beavers_health_type
    [...]

    class Populator(BasePopulator):
        dependencies = ['creme_core']

        def populate(self):
            [...]

            Job.objects.get_or_create(
                type_id=beavers_health_type.id,
                defaults={
                    'language':    settings.LANGUAGE_CODE,
                    # BEWARE: we must define a period
                    'periodicity': date_period_registry.get_period('days', 1),
                    'status':      Job.STATUS_OK,
               },
            )

**Errors management** : your jobs will likely encounter some issues ; in our
example the Web service could be unavailable. It's a good idea to display in
the UI what happened during the last run. Most of the methods in ``JobType``
take a parameter ``job`` which is the instance of the related ``Job``. There
are some base models allowing to create some results related to this job (they
are displayed in the errors' bricks of the detailed view of the job). Here an
example : ::

    [...]
    from creme.creme_core.models import JobResult


    class _BeaversHealthType(JobType):
        [...]

        def _execute(self, job):
            try:
                [...]
            except MyConnectionError as e:
                JobResult.objects.create(
                    job=job,
                    messages=[
                        gettext('An error occurred during connection.'),
                        gettext('Original error: {}').format(e),
                    ],
                )


You can create your own exception types and your own errors' bricks
(see ``JobType.results_bricks``).

**Setting of the job** : a periodic job can be configured through a form
reachable from the list of jobs ; it allows to set the job's period. It's
possible that a job proposes a more complex configuration form, wit the
method ``JobType.get_config_form_class()`` ; additional data can be stored
in the ``Job`` instance, which owns a property ``data`` (beware data must be
compatible with JSON serialization).


Customising enumerations in filters and list-views
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's possible to change the behaviour of enumerations related to instances
referenced by a ``ForeignKey`` (or a ``ManyToManyField``), which are used in
filter forms (eg: choices for the field ``Beaver.status``) and the quick search
of list-views. As seen previously, these ``ForeignKey`` must have their tag
``enumerable`` to ``True`` in order to return a choices list.

If you just want to shrink the possible choices for a given ``ForeignKey``,
use the attribute "limit_choices_to" of this ``ForeignKey`` (it will affect
all forms for the corresponding model automatically).

The enumeration system of Creme is more powerful ; it allows to get more
adapted labels or to regroup some choices. For example, Creme uses it to
customise the enumeration of ``ForeignKey`` referencing the model
``EntityFilter`` (it currently only happens in the model ``reports.Report``) ;
filters are grouped by the entity type they are related to.

This is how it is made (file ``creme_core/apps.py``) : ::

    def register_enumerable(self, enumerable_registry):
        from . import enumerators, models

        enumerable_registry.register_related_model(
            models.EntityFilter,
            enumerators.EntityFilterEnumerator,
        )


List of different services
~~~~~~~~~~~~~~~~~~~~~~~~~~

- You can customise the display of model fields (detailed view, list-view) with
  ``creme_core.gui.field_printers.field_printers_registry``.
- You can register algorithms for email recalls with
  ``creme_core.core.reminder.reminder_registry``.
- You can register new periodicity in
  ``creme_core.utils.date_period.date_period_registry``.
- You can register new date ranges in
  ``creme_core.utils.date_range.date_range_registry``.
- The app **billing** allows the registration of algorithms de generating
  invoice number. Look at ``billing/apps.py``, in the method
  ``register_billing_algorithm()`` to know how to do.
- The app **recurrents** can generate objects regularly. Look at files
  ``recurrents_register.py`` in ``billing`` or ``tickets``.
- The app **crudity** can create objects from external data, like e-mails.


Unit tests and tests driven development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Creme uses as many as possible the
`Test Driven Development <http://fr.wikipedia.org/wiki/Test_Driven_Development>`_
(TDD). So features' tests are written at the same time than features. So code
can be improvement with no regression, or at least they are very limited.

When you are fluent with adding code in Creme, you can consider to test and
debug your code without constantly refresh your Web browser.

For our module *beavers*, here an example which tests the creation view.
Add a file ``beavers/tests.py`` : ::

    # -*- coding: utf-8 -*-

    import datetime

    from creme.creme_core.tests.base import CremeTestCase

    from .models import Beaver, Status


    class BeaverTestCase(CremeTestCase):
        def test_createview(self):
            user = self.login()

            self.assertEqual(0, Beaver.objects.count())
            url = Beaver.get_create_absolute_url()
            self.assertGET200(url)

            name   = 'Hector'
            status = Status.objects.all()[0]
            response = self.client.post(
                url,
                follow=True,
                data={
                    'user':     user.pk,
                    'name':     name,
                    'birthday': '2020-01-14',
                    'status':   status.id,
                },
            )
            self.assertNoFormError(response)

            beavers = Beaver.objects.all()
            self.assertEqual(1, len(beavers))

            beaver = beavers[0]
            self.assertEqual(name,   beaver.name)
            self.assertEqual(status, beaver.status)
            self.assertEqual(
                datetime.date(year=2020, month=1, day=14),
                beaver.birthday,
            )

To run the tests : ::

    > python creme/manage.py test beavers

**Hint** : use SQLite when you write new code. You can even, when you are in a
TDD phase (ie you don't check the result in your browser yet), avoid writing
migrations for each change in a model, with the following lines in your
``local_settings.py`` : ::

    import sys

    # BEWARE ! It only works with SQLite
    if 'test' in sys.argv:
        MIGRATION_MODULES = {
            'auth':           None,
            'creme_core':     None,
            'creme_config':   None,
            'documents':      None,
            'assistants':     None,
            'activities':     None,
            'persons':        None,
            'graphs':         None,
            'reports':        None,
            'products':       None,
            'recurrents':     None,
            'billing':        None,
            'opportunities':  None,
            'commercial':     None,
            'events':         None,
            'crudity':        None,
            'emails':         None,
            'sms':            None,
            'projects':       None,
            'tickets':        None,
            'cti':            None,
            'vcfs':           None,
            'polls':          None,
            'mobile':         None,
            'geolocation':    None,

            'beavers':        None,
        }

When your code seems OK, take the time to run tests with MySQL and/or
PostgreSQL ; you have to comment the previous lines an write the migrations.

**Hint** : when you run the tests with MySQL/PostgreSQL, use the option
``--keepdb`` of the command ``test`` in order to reduce the launch time of the
command after the fisrt run ; it's useful to fix failing tests (but you cannot
modify models between 2 runs).
