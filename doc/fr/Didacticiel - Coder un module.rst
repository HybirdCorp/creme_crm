======================================
Carnet du développeur de modules Creme
======================================

:Author: Guillaume Englert
:Version: 29-09-2014 pour la version 1.5 de Creme
:Copyright: Hybird
:License: GNU FREE DOCUMENTATION LICENSE version 1.3
:Errata: Hugo Smett

.. contents:: Sommaire


Introduction
============

Ce document est destiné à des personnes voulant ajouter ou modifier des fonctionnalités
au logiciel de gestion de la relation client Creme_. Il ne s'agit pas d'une documentation
exhaustive de l'API de Creme, mais d'un didacticiel montrant la création d'un module, pas à pas.


Pré-requis
==========

- Avoir des bases en programmation de manière générale ; connaître le langage Python_ est un gros plus.
- Connaître un minimum le langage HTML

Creme est développé en utilisant un cadriciel (framework) Python spécialisé dans
la création de sites et applications Web : Django_.
Si vous comptez réellement développer des modules pour Creme, la connaissance de
Django sera sûrement nécessaire. Heureusement la documentation de celui-ci est vraiment
complète et bien faite ; vous la trouverez ici : http://docs.djangoproject.com/en/1.4/.
Dans un premier temps, avoir lu le `didacticiel <http://docs.djangoproject.com/en/1.4/intro/tutorial01/>`_
devrait suffire.

Creme utilise aussi la bibliothèque Javascript JQuery_ ; il se peut que pour
programmer certaines fonctionnalités de vos modules vous deviez utiliser du
Javascript (JS) du côté du client (navigateur Web) ; connaître JQuery serait
alors un avantage. Cependant ce n'est pas obligatoire et nous utiliserons des
exemples principalement sans JS dans le présent document.

.. _Creme: http://cremecrm.com
.. _Python: http://www.python.org
.. _Django: http://www.djangoproject.com
.. _JQuery: http://jquery.com


Gestion d'un parc de castors
============================

1. Présentation du module
-------------------------

Nous nous plaçons dans le cas suivant : nous souhaitons créer un module permettant
de gérer un parc naturel possédant des castors. Il faudra donc gérer la population
des castors eux mêmes, et donc connaître pour chacun d'eux son nom, son âge, mais
aussi son état de santé.

Un module Creme se présente sous la forme d'une "app" dans la nomenclature Django.
Pour des raisons de brièveté, nous parlerons nous aussi d'"app" pour notre module.


2. Première version de notre module gestion d'un parc de castors
----------------------------------------------------------------

Avant tout assurez vous d'avoir une instance de Creme fonctionnelle :

 - Clone du dépôt *hg*.
 - Configuration de votre SGBDR.
 - Configuration de votre serveur Web (le serveur de développement livré avec
   Django est un bon choix ici).
 - Configuration du fichier ``local_settings.py``. Pensez par exemple à ne pas
   utiliser le système de cache des templates quand vous développez, afin de ne
   pas avoir à relancer le serveur à chaque modification de template : ::

    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )

Nous vous conseillons d'utiliser l'app `django extensions <https://github.com/django-extensions/django-extensions>`_
qui apporte des commandes supplémentaires intéressantes (``runserver_plus``,
``shell_plus``, ``clean_pyc``, …).


Création du répertoire parent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Plaçons nous dans notre projet, dans le répertoire ``creme/`` : ::

    > cd creme_crm/creme

Il existe une commande pour créer une app (``django-admin.py startapp``), cependant
la tâche étant très simple, nous allons faire ce travail nous-mêmes, petit à petit.
D'abord nous créons le répertoire contenant notre app : ::

    > mkdir beavers

Notez que par convention (et pour des raisons techniques que nous verrons juste après),
nous mettons le terme "beaver" ("castor") au pluriel.

Plaçons nous, dans notre répertoire fraîchement créé : ::

    > cd beavers

Afin que le répertoire *beavers* soit considéré par Python comme un module, nous
devons y mettre un fichier (qui peut tout à fait être vide) nommé ``__init__.py`` : ::

    > touch __init__.py


Création du premier modèle
~~~~~~~~~~~~~~~~~~~~~~~~~~

Maintenant créons un autre répertoire, ``models/``, dans lequel nous nous plaçons ensuite : ::

    > mkdir models
    > cd models


Puis créons dedans un fichier nommé ``beaver.py`` (notez le singulier) à l'aide notre
éditeur de texte préféré, contenant le texte suivant : ::

    # -*- coding: utf-8 -*-

    from django.db.models import CharField, DateField
    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.models import CremeEntity


    class Beaver(CremeEntity):
        name     = CharField(_(u'Name'), max_length=100)
        birthday = DateField(_(u'Birthday'))

        creation_label = _('Add a beaver')

        class Meta:
            app_label = "beavers"
            verbose_name = _(u'Beaver')
            verbose_name_plural = _(u'Beavers')
            ordering = ('name',)

        def __unicode__(self):
            return self.name

        def get_absolute_url(self):
            return "/beavers/beaver/%s" % self.id

        def get_edit_absolute_url(self):
            return "/beavers/beaver/edit/%s" % self.id

        @staticmethod
        def get_lv_absolute_url():
            return "/beavers/beavers"


Nous venons de créer notre première classe de modèle, ``Beaver``. Ce modèle correspondra
à une table dans Système de Gestion de Base de Données (SGBD) : *beavers_beaver*.
Pour le moment, on ne stocke pour chaque castor que son nom et sa date de naissance.
Notre modèle dérive de ``CremeEntity``, et non d'un simple ``DjangoModel`` : ceci
permettra aux castors de disposer de Propriétés, de Relations, de pouvoir être affichés
dans une vue en liste, ainsi que beaucoup d'autres services.

En plus des champs contenus en base (fields), nous déclarons :

- la classe ``Meta`` qui permet d'indiquer notamment l'app à laquelle appartient notre modèle.
- la méhode ``__unicode__`` qui permet d'afficher de manière agréable les objets ``Beavers``.
- 3 méthodes renvoyant des URL, ``get_absolute_url()`` pour l'url de la vue détaillée,
  ``get_edit_absolute_url()``, pour la vue d'édition, et enfin ``get_lv_absolute_url()``
  pour la vue en liste.
- le champ ``creation_label`` qui permet de nommer correctement les éléments d'interface
  (bouton, menu etc…) qui permettent de créer un castor, plutôt qu'un simple "New".


Là encore, pour que le répertoire ``models/`` soit un module, nous devons y mettre
un second fichier nommé ``__init__.py``, et qui contient : ::

    # -*- coding: utf-8 -*-

    from beaver import Beaver


Ainsi, au démarrage de Creme, notre modèle sera importé automatiquement par Django, et
sera notamment relié à sa table dans le SGDB.

    **Note technique** : Django (et donc Creme) n'utilisant pas les imports absolus,
    nommer notre app au pluriel, et notre fichier de modèle (et plus tard de formulaire
    et de vue) au singulier, permet d'éviter des problèmes d'imports.


Installer notre module
~~~~~~~~~~~~~~~~~~~~~~

Si ce n'est pas déjà fait, créez dans le répertoire ``creme/`` un fichier nommé
``local_settings.py``. Éditez le maintenant en copiant depuis le fichier de
configuration générale ``creme/settings.py`` le tuple INSTALLED_CREME_APPS. ::

    INSTALLED_CREME_APPS = (
        #CREME CORE APPS
        'creme.creme_core',
        'creme.creme_config',
        'creme.media_managers',
        'creme.documents',
        'creme.assistants',
        'creme.activities',
        'creme.persons',

        #CREME OPTIONNAL APPS (can be safely commented)
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
        'creme.activesync',
        'creme.vcfs',

        'creme.beavers', # <-- NEW
    )

Notez que par rapport à la configuration de base, nous avons ajouté à la fin du
tuple notre app.

Toujours depuis le répertoire ``creme/``, lancez la commande suivante : ::

    > python manage.py syncdb
    Creating table beavers_beaver
    No fixtures found.

Comme vous pouvez le voir, un table "beavers_beaver" a bien été créée. Si vous
l'examinez (avec PHPMyAdmin par exemple), vous verrez qu'elle possède bien une
colonne nommée "name", de type VARCHAR(100), et une colonne "birthday" de type DATE.


Faire apparaître notre module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Il va bien falloir remplir cette base de données avec des castors. Pourtant si nous
lançons Creme avec le serveur de développement de Django, et que nous y connectons
avec notre navigateur Web (à l'adresse définie par SITE_DOMAIN dans la configuration),
que se passe-t-il ? ::

    > python manage.py runserver


Après s'être connecté dans Creme (en tant que super utilisateur, pour éviter
d'avoir à configurer les droits), aucune trace de notre nouvelle app. Mais pas
d'inquiétude, nous allons y remédier. Tout d'abord, créons un nouveau fichier
``beavers/creme_core_register.py`` qui contient : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.registry import creme_registry
    from creme.creme_core.gui.menu import creme_menu

    from creme.beavers.models import Beaver

    creme_registry.register_entity_models(Beaver)
    creme_registry.register_app('beavers', _(u'Beavers management'), '/beavers')

    reg_item = creme_menu.register_app('beavers', '/beavers/').register_item
    reg_item('/beavers/beavers',    _(u'All beavers'),     'beavers')
    reg_item('/beavers/beaver/add', Beaver.creation_label, 'beavers.add_beaver')

Explications :

- Le singleton ``creme_registry`` permet d'enregistrer les modèles dérivants de
  ``CremeEntity`` (méthode ``register_entity_models()``) et que l'on veut disposer
  sur eux des services tels que la recherche globale, la configuration des boutons
  et des blocs par exemple. C'est le cas la plupart du temps où l'on dérive de
  ``CremeEntity``.
- On enregistre ensuite notre app (méthode ``register_app()``). Il faut en effet
  avoir enregistré notre app auprès de Creme avant de pouvoir insérer l'entrée
  de notre app dans le menu principal (``creme_menu.register_app``).
- Dans les 2 dernières lignes du fichiers nous créons 2 entrées dans le menu de
  notre app : l'une pour afficher la liste des castors, l'autre pour créer un
  nouveau castor. Notez que l'url de la vue en liste est la même que celle
  renvoyée par la méthode ``get_lv_absolute_url()`` vue précédemment.

Si nous relançons le serveur, et rechargeons notre page dans le navigateur, nous
voyons bien une nouvelle entrée dans le menu rétractable à gauche, portant le
label "Beavers management". Et si on entre dans le menu, il contient bien les 2
liens attendus (liste et création). Cependant si vous cliquez sur ces derniers,
vous obtenez une erreur 404 (mais plus pour longtemps).


Notre première vue : la vue de liste
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Nous allons à présent créer la vue permettant d'afficher la liste des castors,
auquelle on accède par l'url: '/beavers/beavers', que l'on a utilisé dans
``creme_core_register.py``.

Premièrement, jetons un coup d'œil au fichier ``creme/urls.py`` ; on y trouve
la configuration des chemins de base pour chaque app. Nous remarquons ici que
pour chaque app présente dans le tuple INSTALLED_CREME_APPS, on récupère le fichier
``urls.py`` se trouvant dans le répertoire ``nom_de_votre_appli/``.
Créons donc ce fichiers ``urls.py`` contenu dans ``beaver/`` : ::

    # -*- coding: utf-8 -*-

    from django.conf.urls import patterns


    urlpatterns = patterns('creme.beavers.views',
        (r'^beavers$',    'beaver.listview'),
        (r'^beaver/add$', 'beaver.add'),
    )

Si nous essayons à nouveau d'accéder dans notre navigateur à la liste des
castors, nous provoquons une erreur 500 : c'est logique puisque nous déclarons
dans notre ``beavers/urls.py`` avoir un fichier de vue "beaver" contenant une
fonction ``listview``, ce qui n'est pas (encore) le cas. Remédions y ; ajoutons
d'abord un nouveau répertoire nommé ``views/`` dans ``beavers/``, ainsi que le
``__init__.py`` habituel: ::

    > mkdir views
    > cd views
    > touch __init__.py


Dans ``views/``, nous créons alors le fichier ``beaver.py`` : ::

    # -*- coding: utf-8 -*-

    from django.contrib.auth.decorators import login_required, permission_required

    from creme.creme_core.views import generic

    from creme.beavers.models import Beaver


    @login_required
    @permission_required('beavers')
    def listview(request):
        return generic.list_view(request, Beaver)


Et là nous obtenons enfin un résultat intéressant lorsque nous nous rendons sur
l'url de liste : on nous demande de créer une vue pour cette liste. Ceci fait,
on arrive bien sur une liste des castors... vide. Forcément, aucun castor n'a
encore été créé.


La vue de création
~~~~~~~~~~~~~~~~~~

Intéressons nous à notre url '/beavers/beaver/add', que nous avons utilisée dans
``beavers/urls.py`` ainsi que dans ``beavers/creme_core_register.py``. Nous avons
en effet dans notre menu de gauche une entrée 'Add a beaver' qui donne toujours
une erreur 404.
Créez un répertoire ``beavers/forms``, avec le coutumier ``__init__.py`` : ::

    > mkdir forms
    > cd forms
    > touch __init__.py

Dans ``forms/``, nous créons alors le fichier ``beaver.py`` : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.forms import CremeEntityForm, CremeDateField

    from ..models import Beaver


    class BeaverForm(CremeEntityForm):
        birthday = CremeDateField(label=_(u'Birthday'))

        class Meta(CremeEntityForm.Meta):
            model = Beaver


Il s'agit assez simplement d'un formulaire lié à notre modèle ; la seule subtilité
est l'utilisation du champ ``CremeDateField`` afin de disposer d'un 'widget' pour
remplir la date en cliquant.
Puis nous modifions ``views/beaver.py``, en ajoutant ceci à la fin (vous pouvez
ramener le ``import`` au début, avec les autres directives ``import`` bien sûr) : ::

    from ..forms.beaver import BeaverForm

    @login_required
    @permission_required('beavers')
    @permission_required('beavers.add_beaver')
    def add(request):
        return generic.add_entity(request, BeaverForm)


Quand nous cliquons sur notre entrée 'Add a beaver', nous obtenons bien le formulaire
attendu. Mais quand nous validons notre formulaire correctement rempli, nous générons
une erreur 404 à nouveau. Pas de panique : la vue ``add_entity`` a juste demandé à
afficher la vue de détail de notre castor. Celui-ci a bien été créé, mais sa vue
détaillée n'existe pas encore.


La vue détaillée
~~~~~~~~~~~~~~~~

Ajoutons cette fonction de vue (dans ``views/beaver.py`` donc, si vous suivez) : ::

    @login_required
    @permission_required('beavers')
    def detailview(request, beaver_id):
        return generic.view_entity(request, beaver_id, Beaver, '/beavers/beaver')


Il faut aussi éditer ``beavers/urls.py`` pour ajouter cette url : ::

    urlpatterns = patterns('creme.beavers.views',
        (r'^beavers$',                   'beaver.listview'),
        (r'^beaver/add$',                'beaver.add'),
        (r'^beaver/(?P<beaver_id>\d+)$', 'beaver.detailview'), # < -- NEW
    )


En rafraîchissant notre page dans le navigateur, nous obtenons bien la vue détaillée
espérée. Il nous manque encore une vue de base : la vue d'édition.


La vue d'édition
~~~~~~~~~~~~~~~~

Si nous cliquons sur le bouton d'édition (le gros stylo dans la vue détaillée),
nous avons encore une erreur 404. Ajoutons cette vue dans ``views/beaver.py`` : ::

    @login_required
    @permission_required('beavers')
    def edit(request, beaver_id):
        return generic.edit_entity(request, beaver_id, Beaver, BeaverForm)

et rajoutons l'url associée : ::

    urlpatterns = patterns('creme.beavers.views',
        (r'^beavers$',                        'beaver.listview'),
        (r'^beaver/add$',                     'beaver.add'),
        (r'^beaver/edit/(?P<beaver_id>\d+)$', 'beaver.edit'),  # < -- NEW
        (r'^beaver/(?P<beaver_id>\d+)$',      'beaver.detailview'),
    )


La vue de portail
~~~~~~~~~~~~~~~~~

La plupart des apps possède un portail ; il sert notamment à afficher les blocs
relatifs aux entités de l'app en question (par exemple tous les ToDos attachés
à des castors dans notre cas), ainsi que des statistiques. C'est très simple à
mettre en place ; nous afficherons le nombre de castors en tout dans nos
statistiques. Ajouter le fichier ``views/portal.py`` suivant : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import ugettext as _

    from creme.creme_core.views.generic import app_portal

    from creme.creme_config.utils import generate_portal_url

    from creme.beavers.models import Beaver


    def portal(request):
        stats = (
                    (_('Number of beavers'), Beaver.objects.count()),
                )

        return app_portal(request, 'beavers', 'beavers/portal.html', Beaver,
                          stats, config_url=generate_portal_url('beavers')
                         )

Il faut mettre à jour le fichier ``beavers/urls.py`` : ::

    [...]

    urlpatterns = patterns('creme.beavers.views',
        (r'^$', 'portal.portal'), # <- NEW

        (r'^beavers$',                        'beaver.listview'),
        (r'^beaver/add$',                     'beaver.add'),
        (r'^beaver/edit/(?P<beaver_id>\d+)$', 'beaver.edit'),
        (r'^beaver/(?P<beaver_id>\d+)$',      'beaver.detailview'),
    )

Rien dans l'interface ne permet d'accéder au portail pour le moment. Nous mettons
donc une entrée supplémentaire dans le menu de gauche en éditant
``creme_core_register.py`` : ::

    [...]

    reg_item = creme_menu.register_app('beavers', '/beavers/').register_item
    reg_item('/beavers/',           _(u'Portal'),          'beavers') # <- NEW
    reg_item('/beavers/beavers',    _(u'All beavers'),     'beavers')
    reg_item('/beavers/beaver/add', Beaver.creation_label, 'beavers.add_beaver')


Si vous tentez d'accéder au portail, vous déclenchez une erreur. En effet, il
reste encore un tout petit peu de travail pour qu'il fonctionne. Toute à l'heure
dans ``views/portal.py``, dans la fonction ``app_portal()`` nous avons fait
référence à un fichier 'template' qui n'existe pas : ``beavers/portal.html``.
Remédions y ; tout d'abord créez un répertoire ``templates`` dans ``beavers/``, et
qui contiendra lui même un répertoire ``beavers`` (attention il faut suivre) : ::

    > mkdir templates
    > cd templates
    > mkdir beavers


Ne reste plus qu'à créer le fameux fichier ``beavers/templates/beavers/portal.html`` : ::

    {% extends "creme_core/generics/portal.html" %}
    {% load i18n %}
    {% block title %}{% trans "Beaver portal" %}{% endblock %}
    {% block list_url %}/beavers/beavers{% endblock %}
    {% block list_msg %}{% trans "List of beavers" %}{% endblock %}

Vous remarquerez qu'il ne sert qu'à surcharger des blocs du portail génériques ;
d'autres blocs sont surchargeables, par exemple celui pour rajouter une icône
à votre portail.


Initialisation du module
~~~~~~~~~~~~~~~~~~~~~~~~

La plupart des modules partent du principe que certaines données existent en base,
que ce soit pour leur bon fonctionnement ou pour rendre l'utilisation de ce module
plus agréable. Par exemple, quand nous avons voulu aller sur notre liste de castor
la première fois, nous avons du créer une vue (i.e. : les colonnes à afficher dans
la liste). Nous allons écrire du code qui sera exécuté au déploiement, et créera
la vue de liste. Créons un nouveau fichier : ``beavers/populate.py``. ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import ugettext as _

    from creme.creme_core.core.entity_cell import EntityCellRegularField
    from creme.creme_core.models import HeaderFilter, SearchConfigItem
    from creme.creme_core.utils import create_or_update as create
    from creme.creme_core.management.commands.creme_populate import BasePopulator

    from .models import *


    class Populator(BasePopulator):
        dependencies = ['creme_core']

        def populate(self):
            HeaderFilter.create(pk='beavers-hf_beaver', name=_(u'Beaver view'), model=Beaver,
                                cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                            (EntityCellRegularField, {'name': 'birthday'}),
                                           ],
                               )

            SearchConfigItem.create_if_needed(Beaver, ['name'])

Explications :

- Nous créons une vue de liste (``HeaderFilter``) avec 2 colonnes, correspondant
  tout simplement au nom et la date de naissance de nos castors. Pour les
  colonnes, la classe ``EntityCellRegularField`` correspond à des champs
  normaux de nos castors (il y a d'autres classes, comme ``EntityCellRelation``
  par exemple).
- La ligne avec ``SearchConfigItem`` sert à configurer la recherche globale :
  elle se fera sur le champ 'name' pour les castors.

Le code est exécuté par la commande ``creme_populate``. La commande permet de ne
'peupler' que notre app. Dans ``creme/``, exécutez : ::

    > python manage.py creme_populate beavers

En réaffichant votre liste de castors, la deuxième vue est bien là.


Localisation (l10n)
~~~~~~~~~~~~~~~~~~~

Jusqu'ici nous avons mis uniquement des labels en anglais. Donc même si votre
navigateur est configuré pour récupérer les pages en français quand c'est possible,
l'interface du module *beavers* reste en anglais. Mais nous avons toujours utilisé
les méthodes ``ugettext`` et ``ugettext_lazy`` (importées en tant que '_') pour
'wrapper' nos labels. Il va donc être facile de localiser notre module.
Dans ``beavers/``, créez un répertoire ``locale``, puis lancez la commande qui
construit le fichier de traduction (en français ici) : ::

    > mkdir locale
    > django-admin.py makemessages -l fr -e html
    processing language fr


Un fichier est alors créé par la dernière commande (ainsi que les répertoires
nécessaires) : ``locale/fr/LC_MESSAGES/django.po``

Le fichier ``django.po`` ressemble à quelque chose comme ça (les dates seront
évidement différentes) : ::

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
    "POT-Creation-Date: 2011-03-26 13:29+0100\n"
    "PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
    "Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
    "Language-Team: LANGUAGE <LL@li.org>\n"
    "MIME-Version: 1.0\n"
    "Content-Type: text/plain; charset=UTF-8\n"
    "Content-Transfer-Encoding: 8bit\n"
    "Plural-Forms: nplurals=2; plural=n>1;\n"

    #: creme_core_register.py:11
    msgid "Beavers management"
    msgstr ""

    #: creme_core_register.py:14
    msgid "All beavers"
    msgstr ""

    #: creme_core_register.py:15
    msgid "Add a beaver"
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

Éditez ce fichier en mettant les traductions adéquates dans les chaînes "msgstr" : ::

    # FR LOCALISATION OF 'BEAVERS' APP
    # Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
    # This file is distributed under the same license as the PACKAGE package.
    # FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
    #
    #, fuzzy
    msgid ""
    msgstr ""
    "Project-Id-Version: PACKAGE VERSION\n"
    "Report-Msgid-Bugs-To: \n"
    "POT-Creation-Date: 2011-03-26 13:29+0100\n"
    "PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
    "Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
    "Language-Team: LANGUAGE <LL@li.org>\n"
    "MIME-Version: 1.0\n"
    "Content-Type: text/plain; charset=UTF-8\n"
    "Content-Transfer-Encoding: 8bit\n"
    "Plural-Forms: nplurals=2; plural=n>1;\n"

    #: creme_core_register.py:11
    msgid "Beavers management"
    msgstr "Gestion des castors"

    #: creme_core_register.py:14
    msgid "All beavers"
    msgstr "Lister les castors"

    #: creme_core_register.py:15
    msgid "Add a beaver"
    msgstr "Ajouter un castor"

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


Il suffit maintenant de compiler notre fichier de traduction avec la commande
suivante : ::

    > django-admin.py compilemessages
    processing file django.po in [...]/creme_crm/creme/beavers/locale/fr/LC_MESSAGES

Le fichier ``beavers/locale/fr/LC_MESSAGES/django.mo`` est bien généré. Si vous
relancez le serveur Web, les différents labels apparaissent en français, pour peu
que votre navigateur soit configuré pour, et que que le middleware
'django.middleware.locale.LocaleMiddleware' soit bien dans votre ``settings.py``
(ce qui est le cas par défaut).



3. Principes avancés
--------------------

Utilisation de creme_config
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Admettons que nous voulions donner un état de santé pour chacun de nos castors :
cela pourrait par exemple être utilisé dans la vue en liste pour n'afficher que
les castors malades, et appeler un vétérinaire en conséquence.


Tout d'abord **supprimez tous les castors** que vous avez crées, depuis la vue
en liste et sa suppression multiple par exemple (nous pourrions essayer de migrer
la base de données, mais cela sortirais du champ de ce chapitre en tout cas).
Ensuite créez un fichier ``models/status.py`` : ::

    # -*- coding: utf-8 -*-

    from django.db.models import CharField, BooleanField
    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.models import CremeModel


    class Status(CremeModel):
        name      = CharField(_(u'Name'), max_length=100, blank=False, null=False, unique=True)
        is_custom = BooleanField(default=True)

        def __unicode__(self):
            return self.name

        class Meta:
            app_label = 'beavers'
            verbose_name = _(u'Beaver status')
            verbose_name_plural  = _(u'Beaver status')
            ordering = ('name',)


**Notes** : l'attribut ``is_custom`` ; il sera utilisé par le module *creme_config*
comme nous allons le voir plus tard. Il est important qu'il se nomme ainsi, et
qu'il soit de type ``BooleanField``. Donner un ordre par défaut (attribut ``ordering``
de la classe ``Meta``) agréable pour l'utilisateur est important, puisque c'est cet
ordre qui sera utilisé par exemple dans les formulaires (à moins que vous n'en
précisiez un autre explicitement, évidement).


Modifiez *models/__init__.py* : ::

    # -*- coding: utf-8 -*-

    from status import Status # <-- NEW
    from beaver import Beaver


Puis ajoutons un champ 'status' dans notre modèle ``Beaver`` : ::

    from django.db.models import CharField, DateField, ForeignKey # <- NEW
    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.models import CremeEntity

    from status import Status # <- NEW


    class Beaver(CremeEntity):
        name     = CharField(_(u'Name'), max_length=100)
        birthday = DateField(_(u'Birthday'))
        status   = ForeignKey(Status, verbose_name=_(u'Status')) # <- NEW

        [....]


Supprimez la table *beavers_beaver*, puis lancez la commande *syncdb* comme
précédemment : ::

    > python manage syncdb
    Creating table beavers_status
    Creating table beavers_beaver
    Installing index for beavers.Beaver model
    No fixtures found.

En relançant le serveur, pus en voulant ajouter un castor, on a une mauvaise
surprise : le statut est nécessaire, mais aucun n'existe ; de plus pas moyen de
créer de statut.
Nous allons tout d'abord enrichir notre ``populate.py`` en créant au déploiement
des statuts. Les utilisateurs auront donc dès le départ des statuts utilisables.
Créez le fichier ``beavers/constants.py``, qui contiendra comme son nom l'indique
des constantes : ::

    # -*- coding: utf-8 -*-

    STATUS_HEALTHY = 1
    STATUS_SICK = 2


Utilisons tout de suite ces constantes ; modifiez ``populate.py`` : ::

    [...]
    from creme.beavers.constants import STATUS_HEALTHY, STATUS_SICK

    [...]

    def populate(self):
        [...]

        create(Status, STATUS_HEALTHY, name=_(u'Healthy'), is_custom=False)
        create(Status, STATUS_SICK,    name=_(u'Sick'),    is_custom=False)


En mettant l'attribut ``is_custom`` à ``False``, on rend ces 2 ``Status`` non
supprimables. Les constantes créées juste avant sont les PK des 2 objets ``Status``
que l'ont créé ; on pourra ainsi y accéder facilement plus tard. Relancez la
commande pour 'peupler' : ::

    > python manage.py creme_populate beavers


Le formulaire de création de Beaver nous propose bien ces 2 statuts. Créez
maintenant le fichier ``beavers/creme_config_register.py`` tel que : ::

    # -*- coding: utf-8 -*-

    from models import Status

    to_register = ((Status, 'status'),)


Ce fichier va être chargé par le module de configuration générale de Creme,
*creme_config*, qui va chercher une séquence de tuple (Model, Nom) dans la
variable ``to_register``.
Si vous allez sur le portail de la 'Configuration générale', dans le
'Portails des applications', la section 'Portail configuration Gestion des castors'
est bien apparue : elle nous permet bien de créer des nouveaux ``Status``.

**Allons un peu loin** : vous pouvez **précisez le formulaire** à utiliser pour
créer/modifier les statuts en 3ème paramètre du tuple, soit (Model, Nom, Formulaire),
si celui qui est généré automatiquement ne vous convient pas. Ça pourrait être le
cas s'il y a une contrainte métier à respecter, mais qui n'est pas exprimable via
les contraintes habituelles des modèles, comme ``nullable``.

**Allons un peu loin** : si vous pouvez que les **utilisateurs puissent choisir l'ordre**
des statuts (dans les formulaire, dans la recherche rapide des vue de liste etc…),
vous devez rajouter un champ ``order`` comme ceci : ::

    # -*- coding: utf-8 -*-

    from django.db.models import CharField, BooleanField, PositiveIntegerField # <- NEW
    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.models import CremeModel


    class Status(CremeModel):
        name      = CharField(_(u'Name'), max_length=100, blank=False, null=False, unique=True)
        is_custom = BooleanField(default=True)
        order     = PositiveIntegerField(_(u"Order"), default=1, editable=False).set_tags(viewable=False) # <- NEW

        def __unicode__(self):
            return self.name

        class Meta:
            app_label = 'beavers'
            verbose_name = _(u'Beaver status')
            verbose_name_plural  = _(u'Beaver status')
            ordering = ('order',)  # <- NEW


Utilisation de South (migrations)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

South est l'app de référence dans le mode Django quand il s'agit de faire de
gérer les migrations de Base de Données. En effet, avec les versions successives
de code, on est souvent amené à créer de nouvelles tables (pour les nouveaux
modèles), à supprimer des tables, ajouter/supprimer/renommer des champs…

South permet de créer les scripts de migrations de manière automatique la plupart
du temps, ainsi que d'exécuter ces mêmes scripts. La documentation officielle se
trouve `ici <http://south.readthedocs.org/en/latest/>`_.

En admettant que ``south`` soit bien activée dans vos INSTALLED_APPS, vous devriez
avant de mettre votre module *beavers* en production créer son script de migration
initiale : ::

    > python manage.py schemamigration beavers --initial

Un fichier ``beavers/migrations/0001_initial.py`` est alors créé.

**Attention** : dans les faits vous devriez en fait avoir l'erreur suivante : ::

    [...]
    ValueError: South does not support on_delete with SET(function) as values.

La solution consiste à commenter temporairement (le temps de générer la migration)
la ligne suivante du fichier ``creme_core/models/fields.py`` (à la ligne 70
actuellement) : ::

    kwargs['on_delete'] = SET(_transfer_assignation)#[...]


**Explication** : Django gère les suppressions des objets référencés par ForeignKey
suivant 4 méthodes : CASCADE, PROTECT, SET_NULL et SET. Les 3 premières sont
triviales à comprendre, la dernière prend une fonction qui permet de coder le
comportement à utiliser lors de la suppression. Malheureusement South ne gère
pas ce dernier cas, et refuse de générer les migrations quand on s'en sert. Or
South n'évolue plus en ce moment, car son auteur est en train de l"intégrer
directement dans Django, et va devenir à terme la façon standard de gérer les
tables (la commande ``syncdb`` va plus ou moins disparaître).
À terme le problème de SET devrait disparaître (ainsi que des tas de bugs de South
venant de sa non intégration), mais pour le moment on n'a pas le choix que de
contourner les problèmes. D'où le hack qui consiste à commenter la ligne susnommée,
qui fait que South voit cette FK comme étant en mode CASCADE, la valeur par défaut.


Le script de migration est joué lorsque la commande ``migrate`` est lancée, au
déploiement de votre instance de Creme.

Lorsque vous ferez évoluer votre app *beavers*, vous devrez potentiellement
utiliser les commandes ``schemamigration`` et ``datamigration`` pour générer de
nouveaux scripts de migrations.

Facilitez vous la vie en désactivant ``south`` pendant la phase de développement,
mais ne cédez pas à la tentation de vous en passer totalement, vous le regretteriez
à moyen terme.


Utilisation des blocs
~~~~~~~~~~~~~~~~~~~~~

[TODO]


Utilisation des boutons
~~~~~~~~~~~~~~~~~~~~~~~

Des boutons peuvent être disposés dans les vues détaillées, juste en dessous de
la barre de titre, où se trouve le nom de la fiche visionnée. Ces boutons peuvent
généralement être affichés ou non selon la configuration.

Utilisons donc cette fonctionnalité pour créer un ``Ticket`` (venant de l'app
*tickets*) à destination des vétérinaires, que l'on pourra créer lorsqu'un
castor est malade.

Créons le ficher ``beavers/buttons.py`` (ce nom n'est pas une obligation, mais
une convention) : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.gui.button_menu import Button

    from creme.beavers.models import Beaver
    from creme.beavers.constants import STATUS_HEALTHY, STATUS_SICK


    class CreateTicketButton(Button):
        id_           = Button.generate_id('beavers', 'create_ticket')
        verbose_name  = _(u'Create a ticket to notify that a beaver is sick.')
        template_name = 'beavers/templatetags/button_ticket.html'
        permission    = 'tickets.add_ticket'

        def get_ctypes(self):
            return (Beaver,)

        def ok_4_display(self, entity):
            return (entity.status_id == STATUS_SICK)

        #def render(self, context):
            #context['variable_name'] = 'VALUE'
            #return super(CreateTicketButton, self).render(context)


    create_ticket_button = CreateTicketButton()

Quelques explications :

- L'attribut ``permission`` est une string dans la pure tradition Django pour les
  permissions, de la forme : 'APP-ACTION'.
- La méthode ``get_ctypes()`` peut préciser, si elle existe, les types d'entités
  avec lesquels le bouton est compatible : le bouton ne sera proposé à la
  configuration que pour ces types là.
- La méthode ``ok_4_display()`` si elle est surchargée, comme ici, permet de
  n'afficher le bouton qu'à certaines conditions (le bouton est affiché si la
  méthode renvoie ``True``). Ici on le l'affiche que pour les Castors avec le
  statut "Sick".
- La méthode ``render()`` vous permet de personnaliser le rendu du bouton, en
  enrichissant le contexte du template notamment ; un exemple de code a été
  laissé en commentaire.

Maintenant au tour du fichier template associé, ``beavers/templates/beavers/templatetags/button_ticket.html``: ::

    {% load i18n %}
    {% load creme_core_tags %}
    {% if has_perm %}
        <a class="menu_button" href="/beavers/ticket/add/{{object.pk}}">
            <img src="{% creme_media_url 'images/ticket_32.png' %}" border="0" title="{% trans "Linked ticket" %}" alt="{% trans "Linked ticket" %}" />
            {% trans "Notify a veterinary" %}
        </a>
    {% else %}
        <span class="menu_button forbidden" title="{% trans "forbidden" %}">
            <img src="{% creme_media_url 'images/ticket_32.png' %}" border="0" title="{% trans "Linked ticket" %}" alt="{% trans "Linked ticket" %}" />
            {% trans "Notify a veterinary" %}
        </span>
    {% endif %}

La variable ``has_perm`` est renseignée grâce à l'attribut ``permission`` de
notre bouton ; nous en faisons usage pour n'afficher qu'un bouton inactif si
l'utilisateur n'a pas les droits suffisants. Notez que la balise ``<a>`` fait
référence à une url à laquelle nous n'avons pas (encore) associé de vue.


Il faut enregistrer notre bouton avec les autres boutons de Creme, afin que
*creme_config* puisse proposer notre bouton. Pour ça, nous rajoutons à la fin
de ``beavers/creme_core_register.py`` : ::

    from creme.creme_core.gui.button_menu import button_registry

    from creme.beavers.buttons import create_ticket_button

    button_registry.register(create_ticket_button)

Si nous allons dans le menu 'Configuration générale', puis 'Gestion du menu bouton',
et que nous éditons la configuration d'un type autre que Castor, notre bouton
n'est pas proposé (c'est ce que nous voulions). En revanche, il est bien proposé
s'il l'on créé une configuration pour le type Castor. Ajoutons le afin de pouvoir
continuer.

En nous rendant sur la fiche d'un castor malade (avec le statut "Sick"), le
bouton est bien apparu. Il provoque une erreur 404 comme on s'y attendait. Nous
n'avons plus qu'à faire la vue de création de ``Ticket``.
Dans ``beavers/urls.py`` : ::

    [...]

    (r'^ticket/add/(?P<beaver_id>\d+)$',  'ticket.add'),

    [...]

Dans un nouveau fichier de vue ``beavers/views/ticket.py`` : ::

    # -*- coding: utf-8 -*-

    from django.shortcuts import get_object_or_404
    from django.utils.translation import ugettext as _
    from django.contrib.auth.decorators import login_required, permission_required

    from creme.creme_core.views.generic import add_entity

    from creme.tickets.forms.ticket import TicketCreateForm

    from creme.beavers.models import Beaver


    @login_required
    @permission_required('tickets')
    @permission_required('tickets.add_ticket')
    def add(request, beaver_id):
        beaver = get_object_or_404(Beaver, pk=beaver_id)

        return add_entity(request, TicketCreateForm,
                          extra_initial={'title':       _(u'Need a veterinary'),
                                         'description': _(u'%s is sick.') % beaver,
                                        }
                         )

Maintenant notre vue nous affiche bien un formulaire pré-rempli en partie.

Utilisation de la création rapide
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

En haut de chaque page se trouve le panneau de création rapide, qui permet de
créer entre 1 et 9 fiches du même type, en même temps. Les formulaires de création
rapide sont en général, et pour des raisons évidentes, des versions simplifiées
des formulaires desdites entités. Par exemple, le formulaire de création rapide
des Sociétés n'a que 2 champs ("nom" et "propriétaire"). Ces formulaires sont
aussi utilisés dans certains *widgets* de sélection de fiche, qui permettent de
créer des fiches à la volée.

Si vous souhaitez ajouter la possibilité de création rapide à vos castors, c'est
très simple. Dans votre ``creme_core_register.py``, ajoutez ces quelques lignes : ::

    from creme.creme_core.gui import quickforms_registry # A fusionner avec les autres imports depuis creme.creme_core.gui...

    from .forms.beaver import BeaverForm


    quickforms_registry.register(Beaver, BeaverForm)


Ici nous utilisons le formulaire classique des castors, et non une version
simplifiée, car :

 - il est déjà simple.
 - l'écriture d'un tel formulaire (dans ``beavers/forms/quick.py`` classiquement)
   est laissée en exercice au lecteur !

**Attention** : n'enregistrez que des classes dérivant de ``CremeEntity``. Si
vous enregistrez d'autres types de classes, les droits de création ne seront
accordés qu'aux super-utilisateurs (car leurs tests de droit sont évités), en
clair les utilisateurs lambda ne verrons pas la classe dans la liste des créations
rapides possibles. C'est à la fois un choix d'interface et une limitation de
l'implémentation, cela pourrait donc changer à l'avenir, mais en l'état il en
est ainsi.


Champs fonctions
~~~~~~~~~~~~~~~~

[TODO]

Hooking des formulaires
~~~~~~~~~~~~~~~~~~~~~~~

Les formulaires Creme possèdent 3 méthodes qui permettent de changer leur
comportement sans avoir à modifier leur code directement, ce qui est utile pour
adapter les apps existantes de manière propre :

 - ``add_post_init_callback()``
 - ``add_post_clean_callback()``
 - ``add_post_save_callback()``

Elles prennent chacune une fonction comme seul paramètre ; comme leur nom
le suggère, ces fonctions (*callbacks*) sont respectivement appelées après les
appels à __init__(), clean() et save(). Ces callbacks doivent avoir un et un
seul paramètre, l'instance du formulaire.

Le plus simple est de *hooker* les formulaires voulus depuis le ``creme_config_register.py``
d'une de vos apps personnelles (comme *beavers*).
 
[TODO: à compléter]


Surcharge des templates
~~~~~~~~~~~~~~~~~~~~~~~

Une des manières les plus simple de modifier une app existante pour l'adapter à
ses propres besoin consiste à surcharger tout ou partie de ses templates.

Pour cela, Creme s'appuie sur le système de chargement des templates de Django.
Si vous regardez votre fichier ``settings.py``, vous pouvez y trouver la variable
suivante : ::

    TEMPLATE_LOADERS = (
        ('django.template.loaders.cached.Loader', (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        )),
    )

L'ordre des *loaders* est important ; cet ordre va faire que les templates présent
dans le répertoire ``creme/templates/`` seront chargés en priorité par rapport
aux templates présent dans les répertoires ``templates/`` que l'on trouve dans
les répertoires des apps.

Exemple : plutôt que de modifier directement le template ``creme/persons/templates/persons/view_contact.html``,
vous pouvez mettre votre version modifiée dans le fichier ``creme/templates/persons/view_contact.html``.


Surcharge de label
~~~~~~~~~~~~~~~~~~

Il est assez courant de vouloir personnaliser certains labels ; par exemple,
vouloir remplacer les occurrences de 'Société' par 'Association'.

Dans le répertoire ``creme/``, il faut lancer la commande suivante (notez que
'organisation' est le terme utilisé en anglais pour 'société') : ::

    > python manage.py i18n_overload -l fr organisation Organisation


Il faut ensuite éditer le fichier de traduction nouvellement créé dans
``locale_overload/`` (indiqué par la commande), en modifiant les phrases en
français. Dans notre exemple, on remplacera donc 'société' par 'collectivité'.
N'oubliez pas de supprimer les lignes "#, fuzzy".
Il ne restera alors plus qu'à compiler ces nouvelles traductions comme déjà
vu auparavant. En se plaçant dans le répertoire ``locale_overload/`` : ::

    > django-admin.py compilemessages


Modification d'un modèle existant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Il arrive aussi régulièrement de vouloir modifier un modèle existant, fourni de
base par Creme, par exemple ajouter des champs à Contact, ou bien en supprimer.

Dans le cas où vous voulez ajouter des champs, la méthode la plus simple est
d'utiliser des champs personnalisés (Custom fields), que vous pouvez ajouter
depuis l'interface, dans la configuration générale. Le problème est qu'il n'est
pas (encore) possible d'ajouter des règles métier à ces champs, comme calculer
leur valeur automatiquement par exemple.

En dernier recours, vous pouvez alors utiliser la fonction ``contribute_to_model()``
qui permet d'ajouter et supprimer des champs à un modèle. Pour cela il suffit de
créer un modèle abstrait, et ses champs seront ajoutés à la classe que l'on veut
modifier ; on peut aussi passer la liste des champs que l'on veut supprimer.
Par exemple dans votre module *models* : ::

    from django.db.models import Model, CharField
    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.utils.contribute_to_model import contribute_to_model

    from creme.persons.models import Contact


    class _ContributingContact(Model):
        nickname = CharField(_(u'Nickname'), max_length=75, null=True, blank=True)

        class Meta:
            abstract = True


    contribute_to_model(_ContributingContact, Contact,
                        fields_2_delete=('url_site', 'sector')
                       )

Ce code va ajouter un champ *nickname* et enlever 2 champs à ``Contact``. Il vous
faut ensuite générer la migration South ; dans notre exemple nous avons modifié
``Contact``, donc la migration concerne l'app *persons* (et non pas la vôtre).

**Problèmes connus** de ``contribute_to_model()`` :

 - Les champs ManyToManyField ne sont pas pris en compte.
 - Si la fonction marche bien sur les classes terminales, elle est difficilement
   compatible avec les classes mères (en tant que cible à modifier) à cause de
   l'implémentation actuelle. Quand une classe mère est utilisée pour un modèle,
   Django copie les champs dans la classe fille. Par conséquent, si
   ``contribute_to_model()`` est appelée alors que la dérivation a déjà été faite,
   les nouveaux champs ne sont pas accessible dans la classe fille comme on le
   souhaiterait. Conclusion : vous pouvez vous en servir pour modifier ``Contact``
   ou ``Organisation`` sans problème, en revanche évitez de modifier ``CremeEntity``
   de cette manière.


Liste des différents services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- L'app *billing* permet d'enregistrer des algorithmes de génération de numéros
  de facture. Regardez le fichier ``billing/billing_register.py``.
- L'app *recurrents* permet de générer des objets de manière récurrente. Regardez
  les fichiers ``recurrents_register.py`` dans ``billing`` ou ``tickets``.
- L'app *crudity* permet de créer des objets depuis des données externes, comme
  les e-mails par exemple.


Tests unitaires et développement piloté par les tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Creme utilise autant que possible le `Développement Piloté par les Tests <http://fr.wikipedia.org/wiki/Test_Driven_Development>`_.
Ainsi les tests des fonctionnalités sont écrits en même temps que les
fonctionnalités elles-mêmes. En fournissant en permanence un filet de sécurité
aux développeurs, le code peut constamment être amélioré sans régression, ou du
moins en les limitant considérablement.

Une fois un peu à l'aise avec la programmation de code Creme, vous pourrez
envisager de tester et déboguer votre code en rafraîchissant vos vues dans
votre navigateur Web.

Pour notre module *beavers*, voici un exemple qui teste la vue de création.
Créez un fichier ``beavers/tests.py`` : ::

    # -*- coding: utf-8 -*-

    try:
        import datetime

        from creme.creme_core.tests.base import CremeTestCase

        from .models import Beaver, Status
    except Exception as e:
        print 'Error in <%s>: %s' % (__name__, e)


    class BeaverTestCase(CremeTestCase):
        @classmethod
        def setUpClass(cls):
            CremeTestCase.setUpClass()
            cls.populate('creme_config', 'beavers')

    def test_createview(self):
        self.login()

        self.assertEqual(0, Beaver.objects.count())
        url = '/beavers/beaver/add'
        self.assertGET200(url)

        name   = 'Hector'
        status = Status.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user':     self.user.pk,
                                          'name':     name,
                                          'birthday': '2008-6-7',
                                          'status':   status.id,
                                         }
                                   )
        self.assertNoFormError(response)

        beavers = Beaver.objects.all()
        self.assertEqual(1, len(beavers))

        beaver = beavers[0]
        self.assertEqual(name,   beaver.name)
        self.assertEqual(status, beaver.status)
        self.assertEqual(datetime.date(year=2008, month=6, day=7),
                         beaver.birthday
                        )


[TODO: tester ce code]

Remarques:
 - Les imports initiaux sont mis dans un bloc try/except, car si une erreur se
   produit au moment de l'importation des modules, l'exception est capturée
   silencieusement par l'infrastructure de test, et vos tests ne seront pas
   exécutés (tout se passera comme s'il y avait 0 test).
 - La méthode setUpClass est appelée une seule fois, avant que les tests soient
   exécutés. Y lancer les commandes *populate* utiles permet d'être bien plus
   rapide que si on les lance dans la méthode ``setUp()``, exécutée avant
   chaque test de la classe.

Vous pouvez alors lancer vos tests : ::

    > python manage.py test beavers
   