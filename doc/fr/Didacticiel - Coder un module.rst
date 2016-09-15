======================================
Carnet du développeur de modules Creme
======================================

:Author: Guillaume Englert
:Version: 14-09-2016 pour la version 1.7 de Creme
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
complète et bien faite ; vous la trouverez ici : https://docs.djangoproject.com/fr/1.8/.
Dans un premier temps, avoir lu le `didacticiel <https://docs.djangoproject.com/fr/1.8/intro/overview/>`_
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

    from .settings import TEMPLATES
    TEMPLATES[0]['OPTIONS']['loaders'] = (
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

        class Meta:
            app_label = "beavers"
            verbose_name = _(u'Beaver')
            verbose_name_plural = _(u'Beavers')
            ordering = ('name',)

        def __unicode__(self):
            return self.name


Nous venons de créer notre première classe de modèle, ``Beaver``. Ce modèle correspondra
à une table dans Système de Gestion de Base de Données (SGBD) : *beavers_beaver*.
Pour le moment, on ne stocke pour chaque castor que son nom et sa date de naissance.
Notre modèle dérive de ``CremeEntity``, et non d'un simple ``DjangoModel`` : ceci
permettra aux castors de disposer de Propriétés, de Relations, de pouvoir être affichés
dans une vue en liste, ainsi que beaucoup d'autres services.

En plus des champs contenus en base (fields), nous déclarons :

- La classe ``Meta`` qui permet d'indiquer notamment l'app à laquelle appartient notre modèle.
- La méhode ``__unicode__`` qui permet d'afficher de manière agréable les objets ``Beavers``.


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

Éditez le fichier ``creme/project_settings.py``  en y copiant depuis le fichier de
configuration générale ``creme/settings.py`` le tuple INSTALLED_CREME_APPS. ::

    INSTALLED_CREME_APPS = (
        # CREME CORE APPS
        'creme.creme_core',
        'creme.creme_config',
        'creme.media_managers',
        'creme.documents',
        'creme.assistants',
        'creme.activities',
        'creme.persons',

        # CREME OPTIONNAL APPS (can be safely commented)
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

        'creme.beavers',  # <-- NEW
    )

Notez que par rapport à la configuration de base, nous avons ajouté à la fin du
tuple notre app.

**Remarque** : nous utilisons ``creme/project_settings.py`` plutôt que
``creme/local_settings.py`` dans la mesure où la liste des apps installées dans
le projet devrait sûrement être partagée avec les différents membres de l'équipe
(développeurs, administrateurs).


Créer la table dans la base de données
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Toujours depuis le répertoire ``creme/``, lancez les commandes suivantes : ::

    > python manage.py makemigrations beavers

Cela devrait créer un répertoire ``creme/beavers/migrations/`` avec dedans un
fichier ``__init__.py`` et un fichier ``0001_initial.py``. Ce dernier donne
à Django la description de la table qui va contenir nos castors : ::

    > python manage.py migrate beavers
    Operations to perform:
        Apply all migrations: beavers
    Running migrations:
        Rendering model states... DONE
        Applying beavers.0001_initial... OK

Comme vous pouvez le voir, une table "beavers_beaver" a bien été créée. Si vous
l'examinez (avec PHPMyAdmin par exemple), vous verrez qu'elle possède bien une
colonne nommée "name", de type VARCHAR(100), et une colonne "birthday" de type DATE.


Déclarer notre app
~~~~~~~~~~~~~~~~~~

Tout d'abord, créons un nouveau fichier ``beavers/apps.py`` qui contient : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.apps import CremeAppConfig


    class BeaversConfig(CremeAppConfig):
        name = 'creme.beavers'
        verbose_name = _(u'Beavers management')
        dependencies = ['creme.creme_core']

        def register_creme_app(self, creme_registry):
            creme_registry.register_app('beavers', _(u'Beavers management'), '/beavers')

        def register_entity_models(self, creme_registry):
            from .models import Beaver

            creme_registry.register_entity_models(Beaver)


Explications :

- Le singleton ``creme_registry`` permet d'enregistrer les modèles dérivants de
  ``CremeEntity`` (appel à ``creme_registry.register_entity_models()``) et que
  l'on veut disposer sur eux des services tels que la recherche globale, la
  configuration des boutons et des blocs par exemple. C'est le cas la plupart du
  temps où l'on dérive de ``CremeEntity``.
- On enregistre ensuite notre app (appel à ``creme_registry.register_app()``). Il
  faut en effet avoir enregistré notre app auprès de Creme avant de pouvoir insérer
  l'entrée de notre app dans le menu principal (voir en dessous) par exemple.


Nous venons de définir la configuration de notre app pour Django ; mais afin qu'il
vienne chercher notre classe, il reste un petite chose à faire. Éditez le fichier
``beavers/__init__.py`` pour y mettre la ligne suivante : ::

    default_app_config = 'creme.beavers.apps.BeaversConfig'


Si nous lançons Creme avec le serveur de développement de Django, et que nous y
connectons avec notre navigateur Web (à l'adresse définie par SITE_DOMAIN dans
la configuration), que se passe-t-il ? ::

    > python manage.py runserver


Il n'y a aucune trace de notre nouvelle app. Mais pas d'inquiétude, nous allons
y remédier.



Notre première vue : la vue de liste
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Nous allons à présent créer la vue permettant d'afficher la liste des castors,
à laquelle on accède par l'URL: '/beavers/beavers'.

Premièrement, jetons un coup d'œil au fichier ``creme/urls.py`` ; on y trouve
la configuration des chemins de base pour chaque app. Nous remarquons ici que
pour chaque app présente dans le tuple INSTALLED_CREME_APPS, on récupère le fichier
``urls.py`` se trouvant dans le répertoire ``nom_de_votre_appli/``.
Créons donc ce fichiers ``urls.py`` contenu dans ``beaver/`` : ::

    # -*- coding: utf-8 -*-

    from django.conf.urls import url

    from .views import beaver

    urlpatterns = [
        url(r'^beavers$', beaver.listview, name='beavers__list_beavers'),
    ]

Notez le dernier paramètre de ``url()``, qui permet de nommer notre URL. La
conventions Creme est de la forme 'mon_app' + '__list_' + 'mes_modeles' pour la
vue en liste.

Si nous essayons à nouveau d'accéder dans notre navigateur à la liste des
castors (ou n'importe quelle autre en fait), en la tapant à la main dans la
barre d'adresse, nous provoquons une erreur 500 : c'est logique puisque nous
déclarons dans notre ``beavers/urls.py`` avoir un fichier de vue "beaver"
contenant une fonction ``listview``, ce qui n'est pas (encore) le cas.

Remédions y ; ajoutons d'abord un nouveau répertoire nommé
``views/`` dans ``beavers/``, ainsi que le ``__init__.py`` habituel : ::

    > mkdir views
    > cd views
    > touch __init__.py


Dans ``views/``, nous créons alors le fichier ``beaver.py`` : ::

    # -*- coding: utf-8 -*-

    from creme.creme_core.auth.decorators import login_required, permission_required
    from creme.creme_core.views import generic

    from creme.beavers.models import Beaver


    @login_required
    @permission_required('beavers')
    def listview(request):
        return generic.list_view(request, Beaver)


Rajoutons enfin la méthode ``get_lv_absolute_url()`` dans notre modèle. Cette
méthode permettra par exemple de revenir sur la liste des castors lorsqu'on
supprimera une fiche castor : ::

    # -*- coding: utf-8 -*-

    [...]

    from django.core.urlresolvers import reverse


    class Beaver(CremeEntity):
        [...]

        @staticmethod
        def get_lv_absolute_url():
            return reverse('beavers__list_beavers')


**Note** : la méthode ``reverse()``, qui permet de retrouver une URL par le nom
donné à la fonction ``url()`` utilisée dans notre ``urls.py``.

Et là nous obtenons enfin un résultat intéressant lorsque nous nous rendons sur
l'URL de liste : on nous demande de créer une vue pour cette liste. Ceci fait,
on arrive bien sur une liste des castors... vide. Forcément, aucun castor n'a
encore été créé.


La vue de création
~~~~~~~~~~~~~~~~~~

Créez un répertoire ``beavers/forms``, avec le coutumier ``__init__.py`` : ::

    > mkdir forms
    > cd forms
    > touch __init__.py


Dans ``forms/``, nous créons alors le fichier ``beaver.py`` : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.forms import CremeEntityForm

    from ..models import Beaver


    class BeaverForm(CremeEntityForm):
        class Meta(CremeEntityForm.Meta):
            model = Beaver


Il s'agit d'un formulaire lié à notre modèle tout simple.

Puis nous modifions ``views/beaver.py``, en ajoutant ceci à la fin (vous pouvez
ramener les ``import`` au début, avec les autres directives ``import`` bien sûr) : ::

    from django.utils.translation import ugettext_lazy as _

    from ..forms.beaver import BeaverForm

    @login_required
    @permission_required('beavers')
    @permission_required('beavers.add_beaver')
    def add(request):
        return generic.add_entity(request, BeaverForm,
                                  extra_template_dict={'submit_label': _('Save the beaver')},
                                 )


Rajoutons l'entrée qui référence ``beaver.add`` dans ``beavers/urls.py`` : ::

    urlpatterns = [
        url(r'^beavers$',    beaver.listview, name='beavers__list_beavers'),
        url(r'^beaver/add$', beaver.add,      name='beavers__create_beaver'),
    ]


Il reste à mettre une méthode ``get_create_absolute_url()`` dans notre modèle,
ainsi que le champ ``creation_label`` qui permet de nommer correctement les
éléments d'interface (bouton, menu etc…) qui permettent de créer un castor : ::

    # -*- coding: utf-8 -*-


    class Beaver(CremeEntity):
        [...]

        creation_label = _('Add a beaver')

        [...]

        @staticmethod
        def get_create_absolute_url():
            return reverse('beavers__create_beaver')


Si nous rechargeons la vue des castors, un bouton 'Add a beaver' est apparu.
Quand nous cliquons dessus, nous obtenons bien le formulaire attendu. Mais quand
nous validons notre formulaire correctement rempli, nous générons une erreur 404
à nouveau. Pas de panique : la vue ``add_entity`` a juste demandé à
afficher la vue détaillée de notre castor. Celui-ci a bien été créé, mais cette
vue n'existe pas encore.


La vue détaillée
~~~~~~~~~~~~~~~~

Ajoutons cette fonction de vue (dans ``views/beaver.py`` donc, si vous suivez) : ::

    @login_required
    @permission_required('beavers')
    def detailview(request, beaver_id):
        return generic.view_entity(request, beaver_id, Beaver)


Il faut aussi éditer ``beavers/urls.py`` pour ajouter cette URL : ::

    urlpatterns = [
        url(r'^beavers$',                   beaver.listview,   name='beavers__list_beavers'),
        url(r'^beaver/add$',                beaver.add,        name='beavers__create_beaver'),
        url(r'^beaver/(?P<beaver_id>\d+)$', beaver.detailview, name='beavers__view_beaver'),  # < -- NEW
    ]

En rafraîchissant notre page dans le navigateur, nous obtenons bien la vue
détaillée espérée.

Pour que les prochaines création de castor n'aboutisse pas sur une erreur 404,
nous créons la méthode ``get_absolute_url()`` : ::

    # -*- coding: utf-8 -*-

    [...]


    class Beaver(CremeEntity):
        [...]

        def get_absolute_url(self):
            return reverse('beavers__view_beaver', args=(self.id,))


La vue d'édition
~~~~~~~~~~~~~~~~

Contrairement aux autres types de fiche, nos castors ne peuvent pas être modifiés
globalement (avec le gros stylo dans les vues détaillées)

Ajoutons cette vue dans ``views/beaver.py`` : ::

    @login_required
    @permission_required('beavers')
    def edit(request, beaver_id):
        return generic.edit_entity(request, beaver_id, Beaver, BeaverForm)


Rajoutons l'URL associée : ::

    urlpatterns = [
        url(r'^beavers$',                        beaver.listview,   name='beavers__list_beavers'),
        url(r'^beaver/add$',                     beaver.add,        name='beavers__create_beaver'),
        url(r'^beaver/edit/(?P<beaver_id>\d+)$', beaver.edit,       name='beavers__edit_beaver'),  # < -- NEW
        url(r'^beaver/(?P<beaver_id>\d+)$',      beaver.detailview, name='beavers__view_beaver'),
    ]


Ainsi que la méthode ``get_edit_absolute_url`` : ::

    # -*- coding: utf-8 -*-

    [...]


    class Beaver(CremeEntity):
        [...]

        def get_edit_absolute_url(self):
            return reverse('beavers__edit_beaver', args=(self.id,))


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

    # -*- coding: utf-8 -*-

    from django.conf.urls import url

    from .views import beaver, portal  # <- UPDATE


    urlpatterns = [
        url(r'^$', portal.portal),  # <- NEW

        [...]
    ]


Si vous tentez d'accéder au portail, vous déclenchez une erreur. En effet, il
reste encore un tout petit peu de travail pour qu'il fonctionne. Toute à l'heure
dans ``views/portal.py``, dans la fonction ``app_portal()`` nous avons fait
référence à un fichier 'template' qui n'existe pas : ``beavers/portal.html``.
Remédions y ; tout d'abord créez un répertoire ``templates`` dans ``beavers/``, et
qui contiendra lui-même un répertoire ``beavers`` (attention il faut suivre) : ::

    > mkdir templates
    > cd templates
    > mkdir beavers


Ne reste plus qu'à créer le fameux fichier ``beavers/templates/beavers/portal.html`` : ::

    {% extends "creme_core/generics/portal.html" %}
    {% load i18n %}
    {% block title %}{% trans "Beaver portal" %}{% endblock %}
    {% block list_url %}{% url 'beavers__list_beavers' %}{% endblock %}
    {% block list_msg %}{% trans "List of beavers" %}{% endblock %}

Vous remarquerez qu'il ne sert qu'à surcharger des blocs du portail génériques ;
d'autres blocs sont surchargeables, par exemple celui pour rajouter une icône
à votre portail.


Faire apparaître les entrées dans le menu
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dans notre fichier ``apps.py``, nous ajoutons la méthode ``BeaversConfig.register_menu()``
et nous créons 3 entrées dans le menu de notre app : une pour afficher le portail,
une pour la liste des castors, et une pour créer un nouveau castor : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_menu(self, creme_menu):
            from django.core.urlresolvers import reverse_lazy

            reg_item = creme_menu.register_app('beavers', '/beavers/').register_item
            reg_item('/beavers/', _(u'Portal'), 'beavers')
            reg_item(reverse_lazy('beavers__list_beavers'),  _(u'All beavers'),     'beavers')
            reg_item(reverse_lazy('beavers__create_beaver'), Beaver.creation_label, 'beavers.add_beaver')


**Note** : nous utilisons ``reverse_lazy()`` et pas ``reverse()`` afin de
prévenir des problèmes de chargement trop précoce.

Si nous relançons le serveur, et rechargeons notre page dans le navigateur, nous
voyons bien une nouvelle entrée dans le menu rétractable à gauche, portant le
label "Beavers management". Et si on entre dans le menu, il contient bien les 3
liens attendus.


Initialisation du module
~~~~~~~~~~~~~~~~~~~~~~~~

La plupart des modules partent du principe que certaines données existent en base,
que ce soit pour leur bon fonctionnement ou pour rendre l'utilisation de ce module
plus agréable. Par exemple, quand nous avons voulu aller sur notre liste de castor
la première fois, nous avons du créer une vue (i.e. : les colonnes à afficher dans
la liste). Nous allons écrire du code qui sera exécuté au déploiement, et créera
la vue de liste.

Créez le fichier ``beavers/constants.py``, qui contiendra comme son nom l'indique
des constantes : ::

    # -*- coding: utf-8 -*-

    # NB: ceci sera l'identifiant de notre vue de liste par défaut. Pour éviter
    #     les collisions entres apps, la convention est de construire une valeur
    #     de la forme 'mon_app' + 'hf_' + 'mon_model'.
    DEFAULT_HFILTER_BEAVER = 'beavers-hf_beaver'


Puis créons un fichier : ``beavers/populate.py``. ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import ugettext as _

    from creme.creme_core.core.entity_cell import EntityCellRegularField
    from creme.creme_core.management.commands.creme_populate import BasePopulator
    from creme.creme_core.models import HeaderFilter, SearchConfigItem

    from .constants implémentation DEFAULT_HFILTER_BEAVER
    from .models import Beaver


    class Populator(BasePopulator):
        dependencies = ['creme_core']

        def populate(self):
            HeaderFilter.create(pk=DEFAULT_HFILTER_CONTACT, name=_(u'Beaver view'), model=Beaver,
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


**Allons plus loin**: améliorons maintenant notre liste de castors afin de nous
assurer que lorsqu'un utilisateur se connecte avec une session neuve, la vue par
défaut est utilisée (sinon c'est la première par ordre alphabétique): ::

    [...]
    from ..constants import DEFAULT_HFILTER_BEAVER  # <- NEW

    [...]

    @login_required
    @permission_required('beavers')
    def listview(request):
        return generic.list_view(request, Beaver,
                                 hf_pk=DEFAULT_HFILTER_BEAVER,  # <- NEW
                                )



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
    > django-admin.py makemessages -l fr
    processing language fr


Un fichier est alors créé par la dernière commande (ainsi que les répertoires
nécessaires) : ``locale/fr/LC_MESSAGES/django.po``

Le fichier ``django.po`` ressemble à quelque chose comme ça (les dates seront
évidemment différentes) : ::

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
    "POT-Creation-Date: 2015-12-08 18:24+0100\n"
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
    msgid ""
    msgstr ""
    "Project-Id-Version: PACKAGE VERSION\n"
    "Report-Msgid-Bugs-To: \n"
    "POT-Creation-Date: 2015-10-22 18:24+0100\n"
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
que votre navigateur soit configuré pour, et que que le *middleware*
'django.middleware.locale.LocaleMiddleware' soit bien dans votre ``settings.py``
(ce qui est le cas par défaut).



3. Principes avancés
--------------------

Utilisation de creme_config
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Admettons que nous voulions donner un état de santé pour chacun de nos castors :
cela pourrait par exemple être utilisé dans la vue en liste pour n'afficher que
les castors malades, et appeler un vétérinaire en conséquence.

Créez un fichier ``models/status.py`` : ::

    # -*- coding: utf-8 -*-

    from django.db.models import CharField, BooleanField
    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.models import CremeModel


    class Status(CremeModel):
        name      = CharField(_(u'Name'), max_length=100, blank=False, null=False, unique=True)
        is_custom = BooleanField(default=True).set_tags(viewable=False)

        def __unicode__(self):
            return self.name

        class Meta:
            app_label = 'beavers'
            verbose_name = _(u'Beaver status')
            verbose_name_plural  = _(u'Beaver status')
            ordering = ('name',)


**Notes** : l'attribut ``is_custom`` ; il sera utilisé par le module *creme_config*
comme nous allons le voir plus tard. Il est important qu'il se nomme ainsi, et
qu'il soit de type ``BooleanField``. Notez l'utilisation de ``set_tags()`` qui permet
de cacher ce champ à l'utilisateur (nous reviendrons plus tard sur les tags).
Donner un ordre par défaut (attribut ``ordering`` de la classe ``Meta``) agréable
pour l'utilisateur est important, puisque c'est cet ordre qui sera utilisé par
exemple dans les formulaires (à moins que vous n'en précisiez un autre
explicitement, évidemment).


Modifiez *models/__init__.py* : ::

    # -*- coding: utf-8 -*-

    from status import Status  # <-- NEW
    from beaver import Beaver


Nous allons générer une première migration qui généré la table correspondante : ::

    > python manage.py makemigrations beavers

Un fichier nommé ``0002_status.py`` est alors créé.

Dans la mesure où nous avons l'intention d'ajouter une *ForeignKey* non nullable
dans notre classe ``Beaver`` (cela rend l'exercice plus intéressant), nous
allons maintenant créér une migration de données (par opposition à migration de
schéma) qui rajoute en base une instance de ``Status`` qui servira de valeur par
défaut pour les instances de castor existantes. Ça sera tout à fait le genre
de chose qui vous arriveront en pratique : une version en production qu'il faut
faire évoluer sans casser les données existantes.

Générer donc cette migration (notez le paramètre ``empty``) : ::

    > python manage.py makemigrations beavers --empty

Un fichier noméé en fonction de la date du jour vient d'être créé. Une fois
celui-ci rénommé en ``0003_populate_default_status.py``, ouvrez le.
Il devrait ressembler à ça: ::

    # -*- coding: utf-8 -*-
    from __future__ import unicode_literals

    from django.db import migrations, models


    class Migration(migrations.Migration):

        dependencies = [
            ('beavers', '0002_status'),
        ]

        operations = [
        ]


Éditez le pour obtenir : ::

    # -*- coding: utf-8 -*-
    from __future__ import unicode_literals

    from django.db import migrations, models


    def populate_status(apps, schema_editor):
        apps.get_model('beavers', 'Status').objects.create(id=1, name=u'Healthy', is_custom=False)


    class Migration(migrations.Migration):
        dependencies = [
            ('beavers', '0002_status'),
        ]

        operations = [
            migrations.RunPython(populate_status),
        ]


Puis ajoutons un champ 'status' dans notre modèle ``Beaver`` : ::

    from django.core.urlresolvers import reverse
    from django.db.models import CharField, DateField, ForeignKey  # <- NEW
    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.models import CremeEntity

    from status import Status  # <- NEW


    class Beaver(CremeEntity):
        name     = CharField(_(u'Name'), max_length=100)
        birthday = DateField(_(u'Birthday'))
        status   = ForeignKey(Status, verbose_name=_(u'Status'))  # <- NEW

        [....]


Il faut maintenant générer la migration correspondante (pas de ``empty``
puisque c'est une migration de schéma) : ::

    > python manage.py makemigrations beavers
    You are trying to add a non-nullable field 'status' to beaver without a default; we can't do that (the database needs something to populate existing rows).
    Please select a fix:
    1) Provide a one-off default now (will be set on all existing rows)
    2) Quit, and let me add a default in models.py
    Select an option:

Nous avions anticipé cette question, et pouvons donc choisir l'option 1, puis
donner la valeur par défaut "1" (puisque c'est l'ID du ``Status`` créé dans la
migration précédente).

On peut maintenant exécuter nos migrations : ::

    > python manage.py migrate

En relançant le serveur, lorsqu'on ajoute un castor, on a bien un nouveau champ
dans le formulaire. En revanche un seul choix de ``Status`` est disponible, ce
qui est peu utile.

Nous allons tout d'abord enrichir notre ``populate.py`` en créant au déploiement
des statuts. Les utilisateurs auront donc dès le départ plusieurs statuts
utilisables. Dans le fichier ``beavers/constants.py``, on rajoute des
constantes : ::

    # -*- coding: utf-8 -*-

    [...]

    STATUS_HEALTHY = 1
    STATUS_SICK = 2


Utilisons tout de suite ces constantes ; modifiez ``populate.py`` : ::

    [...]
    from .constants import STATUS_HEALTHY, STATUS_SICK
    from .models import Beaver, Status


    def populate(self):
        [...]

		already_populated = Status.objects.exists()

		if not already_populated:
	        Status.objects.create(id=STATUS_HEALTHY, name=_(u'Healthy'), is_custom=False)
    	    Status.objects.create(id=STATUS_SICK,    name=_(u'Sick'),    is_custom=False)


En mettant l'attribut ``is_custom`` à ``False``, on rend ces 2 ``Status`` non
supprimables. Les constantes créées juste avant sont les PK des 2 objets ``Status``
que l'ont créés ; on pourra ainsi y accéder facilement plus tard.

Avec la variable ``already_populated``, on s'assure que les statuts sont créés
au premier lancement, mais que si les utilisateurs modifient le nom des statuts
dans l'interface de configuration, leurs modifications ne seront pas écrasées
lors d'une mise à jour (et donc d'un lancement de la commande ``creme_populate``).

Relancez la commande pour 'peupler' : ::

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
les contraintes habituelles des modèles (comme ``nullable``).

**Allons un peu loin** : si vous voulez que les **utilisateurs puissent choisir l'ordre**
des statuts (dans les formulaire, dans la recherche rapide des vue de liste etc…),
vous devez rajouter un champ ``order`` comme ceci : ::

    # -*- coding: utf-8 -*-

    from django.db.models import CharField, BooleanField
    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.models import CremeModel
    from creme.creme_core.models.fields import BasicAutoField  # <- NEW


    class Status(CremeModel):
        name      = CharField(_(u'Name'), max_length=100, blank=False, null=False, unique=True)
        is_custom = BooleanField(default=True).set_tags(viewable=False)
        order     = BasicAutoField(_(u"Order"))  # <- NEW

        def __unicode__(self):
            return self.name

        class Meta:
            app_label = 'beavers'
            verbose_name = _(u'Beaver status')
            verbose_name_plural  = _(u'Beaver status')
            ordering = ('order',)  # <- NEW


Notez qu'un ``BasicAutoField`` est par défaut non éditable et non visible, et
qu'il gère l'auto-incrémentation tout seul, donc normalement vous n'aurez pas à
vous occuper de lui.


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

    from .constants import STATUS_HEALTHY, STATUS_SICK
    from .models import Beaver


    class CreateTicketButton(Button):
        id_           = Button.generate_id('beavers', 'create_ticket')
        verbose_name  = _(u'Create a ticket to notify that a beaver is sick.')
        template_name = 'beavers/templatetags/button_ticket.html'
        permission    = 'tickets.add_ticket'

        def get_ctypes(self):
            return (Beaver,)

        def ok_4_display(self, entity):
            return (entity.status_id == STATUS_SICK)

        # def render(self, context):
            # context['variable_name'] = 'VALUE'
            # return super(CreateTicketButton, self).render(context)


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
référence à une URL à laquelle nous n'avons pas (encore) associé de vue.


Il faut enregistrer notre bouton avec les autres boutons de Creme, afin que
*creme_config* puisse proposer notre bouton. Pour ça, nous rajoutons dans
``beavers/apps.py`` la méthode ``register_buttons()`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_buttons(self, button_registry):  # <- NEW
            from .buttons import create_ticket_button

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

    from .views import beaver, portal, ticket  # <- UPDATE

    [...]

        url(r'^ticket/add/(?P<beaver_id>\d+)$',  ticket.add),

    [...]

Dans un nouveau fichier de vue ``beavers/views/ticket.py`` : ::

    # -*- coding: utf-8 -*-

    from django.contrib.auth.decorators import login_required, permission_required
    from django.shortcuts import get_object_or_404
    from django.utils.translation import ugettext as _

    from creme.creme_core.views.generic import add_entity

    from creme.tickets.forms.ticket import TicketCreateForm

    from ..models import Beaver


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
très simple. Dans votre ``apps.py``, ajoutez la méthode ``register_quickforms()``
telle que : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_quickforms(self, quickforms_registry):  # <- NEW
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
clair les utilisateurs lambda ne verront pas la classe dans la liste des créations
rapides possibles. C'est à la fois un choix d'interface et une limitation de
l'implémentation, cela pourrait donc changer à l'avenir, mais en l'état il en
est ainsi.


Champs fonctions
~~~~~~~~~~~~~~~~

Ce sont des champs qui n'existent pas en base de données, et qui permettent
d'effectuer des calculs ou des requêtes afin de présenter des l'information
utile aux utilisateurs. Ils sont être disponibles dans les vues en listes et
les blocs personnalisés. ::

    [...]
    from datetime import date

    from creme.creme_core.core.function_field import FunctionField


    class _BeaverAgeField(FunctionField):
        name         = "get_age"
        verbose_name = _(u'Age')


    class Beaver(CremeEntity):
        [...]

        function_fields = CremeEntity.function_fields.new(_ResolvingDurationField())

        [...]

        def get_age(self):
            birthday = self.birthday

            if not birthday:
                return 'N/A

            return '%s year(s)' % (date.today().year - birthday.year)


**Notes** Dans le cas le plus simple, le *name* du FunctionField, qui lui sert
d'identifiant (quand on enregistre une vue de liste par exemple) est aussi le
nom d'une méthode de votre entité. Vous pouvez aussi définir le code de votre
champ fonction dans ce dernier (c'est pratique pour en rajouter dans une entité
d'une app dont vous ne voulez pas toucher le code) : ::

    from creme.creme_core.core.function_field import FunctionField,  FunctionFieldResult

    class _BeaverAgeField(FunctionField):
        name         = 'compute_age'
        verbose_name = _(u'Age')

        def __call__(self, entity, user):
            birthday = entity.birthday

            if not birthday:
                age = 'N/A
            else:
                age = '%s year(s)' % (date.today().year - birthday.year)

            return FunctionFieldResult(age)


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

Le plus simple est de *hooker* les formulaires voulus depuis le ``apps.py``,
d'une de vos apps personnelles (comme *beavers*), dans la méthode
``all_apps_ready()``. Ici un exemple qui rajoute un champ dans le formulaire des
Contacts (notez qu'il faudrait aussi *hooker* la méthode ``save()`` pour
utiliser ce champ ; cet exercice est laissé au lecteur) : ::

    # -*- coding: utf-8 -*-

    [...]


    class BeaversConfig(CremeAppConfig):
        name = 'creme.beavers'
        verbose_name = _(u'Beavers management')
        dependencies = ['creme.creme_core']

        def all_apps_ready(self):
            super(BeaversConfig, self).all_apps_ready()

            from django.forms.fields import BooleanField

            # NB: on fait les import des autres apps ici pour éviter les
            #     problème d'ordre de chargement.
            from creme.persons.forms.contact import ContactForm

            def add_my_field(form):
                form.fields['loves_beavers'] = BooleanField(required=False, label=_(u"Loves beavers?"))

            ContactForm.add_post_init_callback(add_my_field)

        def register_creme_app(self, creme_registry):
            [...]


**Note technique** : ``all_apps_ready()`` est un ajout de Creme à Django qui ne
définit que la méthode ``ready()``. Si vous avez besoin de faire des imports
qui directement ou indirectement provoque l'import de code présent dans d'autres
apps, alors utilisez plutôt ``all_apps_ready()`` ; sinon préférez ``ready()``
qui est plus classique.

**Note technique** : en raison du moment où les *callbacks* sont appelées, il
est tout à fait possible, selon le formulaire qui vous préoccupe, que vous ne
puissiez pas faire ce que vous voulez (par exemple avoir accès à un champ créé
après l'appel à la *callbacks*. Cela reste donc un moyen simple mais limité ;
pour des changements plus ambitieux vous devrez vous rabattre sur des méthodes
plus avancées:

 - Utiliser le *monkey patching* sur le formulaire concerné ; attention cette
   méthode est plutôt brutale et doit être utiliser avec prudence (voire évitée).
 - Définir votre propre modèle personnalisé (Contact dans notre exemple), ce qui
   oblige à définir les vues de base sur celui-ci. On peut alors aisément
   définir notre propre vue et utiliser notre propre formulaire, quitte à ce
   qu'il dérive du formulaire qu'ont veut améliorer. C'est plus propre mais
   nécessite plus de travail. Nous verrons cela plus loin dans le chapitre
   `Modification d'un modèle existant`_


Surcharge des templates
~~~~~~~~~~~~~~~~~~~~~~~

Une des manières les plus simples de modifier une app existante pour l'adapter à
ses propres besoin consiste à surcharger tout ou partie de ses templates.

Pour cela, Creme s'appuie sur le système de chargement des templates de Django.
Si vous regardez votre fichier ``settings.py``, vous pouvez y trouver la
variable suivante : ::

    TEMPLATES = [
        {
            ...

            'OPTIONS': {

                ...

                'loaders': [
                    ('django.template.loaders.cached.Loader', ( #Don't use cached loader when developping (in your local_settings.py)
                        'django.template.loaders.filesystem.Loader',
                        'django.template.loaders.app_directories.Loader',
                    )),
                ],

                ...
            },
        },
    ]


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


Plus loin avec les modèles: les Tags
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Creme permet de *tagger* les champs de modèles afin de leur rajouter de la
sémantique, et d'affiner le comportement de certains services. Pour le moment
en tout cas, il n'est pas possible de créer ses propres *tags*.

Exemple d'utilisation (avec 2 tags configurés en même temps) : ::

    [...]

    class Beaver(CremeEntity):
        [..]
        internal_data = CharField('Data', max_length=100).set_tags(viewable=False, clonable=False)


Listes des *tags* et leur utilité:

 - ``viewable``: les champs d'informations classiques (``IntegerField``,
   ``TextField``, …) sont visible par l'utilsateur. Or, parfois on souhaite
   stocker des informations internes que l'utilisateurs ne devraient pas voir.
   Il suffit de mettre ce *tag* à ``False``, et il sera caché dans toute
   l'application.
 - ``clonable``: en mettant ce *tag* à ``False``, la valeur du champ n'est pas
   copiée lorsque l'entité est clonée.
 - ``optional``: en mettant ce *tag* à ``True``, le champ peut être caché par
   l'utilisation dans la "Configuration des champs" de la "Configuration générale".
   Le champs est alors enlevé des formulaires ; il est donc évident que le champ
   doit supporter de ne pas être rempli par les formulaires sans provoquer
   d'erreur ; par exemple en étant ``nullable`` ou avoir une valeur pour ``default``.
 - ``enumerable``: lorsqu'une ``ForeignKey`` a ce *tag* positionné à ``False``
   (la valeur par défaut étant ``True``), Creme considère que cette FK peut
   prendre une infinité de valeurs, et ces valeurs ne devraient donc jamais
   être présentées en tant que choix, dans les filtres notamment.


Modification champ à champ
~~~~~~~~~~~~~~~~~~~~~~~~~~

Tous les champs déclarés comme ``editable=True`` dans vos modèles d'entités
(c'est le cas par défaut) peuvent être modifié dans les vues détaillés desdits
modèles dans les blocs d'informations (ainsi que dans les vues en liste).
Un champ non éditable ne pourra pas être modifié de cette manière.

Parfois, vous voulez que des champs soient présents dans le formulaire de
création de la fiche, mais vous les excluez du formulaire d'édition (attribut
``exclude`` de la classe ``Meta`` dudit formulaire). De la même manière, vous
voudrez que ces champs ne puissent pas être modifiés non plus dans la vue
détaillée : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_bulk_update(self, bulk_update_registry):
            bulk_update_registry.register(Beaver,
                                          exclude=['my_field1','my_field2'],
                                         )

Vous pouvez aussi vouloir personnaliser le formulaire d'édition pour un champ
en particulier, parce qu'il est associé à des règles métiers par exemple : ::


    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_bulk_update(self, bulk_update_registry):
            from .forms.my_field import MyBulkEditForm

            bulk_update_registry.register(Beaver,
                                          innerforms={'my_field3': MyBulkEditForm},
                                         )


Les formulaires donnés en paramètre doivent hériter de
``creme.creme_core.forms.bulk.BulkForm`` (``BulkDefaultEditForm`` est souvent
un bon choix comme classe mère).


Clonage de fiche
~~~~~~~~~~~~~~~~

De base, les entités peuvent être clonées. Si vous souhaitez qu'un modèle ne
puisse pas l'être, définissez lui la méthode suivante : ::

    class Beaver(CremeEntity):
        [..]

        @staticmethod
        def get_clone_absolute_url():
            return ''


Si vous souhaitez gérer finement ce qui se passe lors d'un clonage, en plus du
*tag* ``clonable`` vu précédemment, vous pouvez surcharger les méthodes
suivantes :

 - ``_pre_save_clone(self, source)`` (à préferer)
 - ``_post_save_clone(self, source)`` (à préferer)
 - ``_post_clone(self, source)`` (à préferer)
 - ``_clone_m2m(self, source)``
 - ``_clone_object(self)``
 - ``_copy_properties(self, source)``
 - ``_copy_relations(self, source, allowed_internal=())``
 - ``clone(self)``


Import de fichiers CSV
~~~~~~~~~~~~~~~~~~~~~~

Si vous souhaitez que votre modèle d'entité puisse être importé via des fichiers
CSV/XLS, vous devez rajouter dans votre ``apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_mass_import(self, import_form_registry):
            import_form_registry.register(Beaver)


De cette manière, le formulaire d'import sera généré automatiquement. Dans le
cas où vous voudriez personnaliser ce formulaire, regardez le code des apps
``persons``, ``activities`` ou ``opportunities`` (cela sort du cadre de
ce tutoriel).


Fusion de 2 fiches
~~~~~~~~~~~~~~~~~~

Si vous voulez rendre un type d'entité fusionnable, regardez comment les apps
``persons`` ou ``document`` s'y prennent, dans la méthode
``register_merge_forms()`` de votre ``apps.py`` (cela sort du cadre de
ce tutoriel).

**Notes** : si vous avez créé un modèle relié un type d'entité fusionnable, vous
pouvez gérer plus finement ce qui ce passe lors d'une fusion grâce aux signaux
``creme.creme_core.signals.pre_merge_related`` et
``creme.creme_core.signals.pre_replace_related``. Et si votre modèle est relié
par un OneToOneField, vous **devez** gérer la fusion, car Creme ne peut
évidemment pas gérer le cas où chacune des entités est relié (il faut donc au
moins supprimer une des instances reliées, en récupérant ou non des informations
au passage etc…).


Valeurs de réglages
~~~~~~~~~~~~~~~~~~~

Le modèle ``SettingValue`` permet de proposer aux utilisateurs de donner des
valeurs typées de configuration à Creme, afin que ce dernier puisse adopter
des comportements différents selon les envies des utilisateurs.

Dans votre fichier ``contants.py`` définissez l'identifiant de la clé de
configuration : ::

    BEAVER_KEY_ID = 'beavers-my_key'


Dans un fichier ``setting_keys.py`` à la racine de votre app mettez : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.core.setting_key import SettingKey

    from .constants import BEAVER_KEY_ID


    beaver_key = SettingKey(id=BEAVER_KEY_ID,
                            description=_('*Set a description here*'),
                            app_label='beavers',
                            type=SettingKey.BOOL,
                           )

Ici on a créé une valeur de type booléen. Les types actuellement disponibles
étant :

 - STRING
 - INT
 - BOOL
 - HOUR
 - EMAIL


Dans votre fichier ``populate.py``, nous allons créé l'instance de
``SettingValue`` associée, en lui donnant donc sa valeur par défaut : ::

    [...]

    from creme.creme_core.models import SettingValue

    from .setting_keys import beaver_key


    class Populator(BasePopulator):
        [...]

        def populate(self):
            [...]

            SettingValue.objects.get_or_create(key_id=beaver_key.id, defaults={'value': True})


Il faut maintenant exposer la clé à Creme. Dans votre ``apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_setting_key(self, setting_key_registry):
            from .setting_keys import beaver_key

            setting_key_registry.register(beaver_key)


La valeur peut alors être configurée par les utilisateurs dans le portal de
configuration de l'app.

Et pour utiliser la valeur dans votre code : ::

    from creme.creme_core.models import SettingValue

    from creme.beavers.constants import BEAVER_KEY_ID


    if SettingValue.objects.get(key_id=BEAVER_KEY_ID).value:
        [...]


Modification d'un modèle existant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Il arrive aussi régulièrement de vouloir modifier un modèle existant, fourni de
base par Creme, par exemple ajouter des champs à Contact, ou bien en supprimer.

Dans le cas où vous voulez ajouter des champs, la méthode la plus simple est
d'utiliser des champs personnalisés (Custom fields), que vous pouvez ajouter
depuis l'interface, dans la configuration générale. Le problème est qu'il n'est
pas (encore) possible d'ajouter des règles métier à ces champs, comme calculer
leur valeur automatiquement par exemple.

Vous pouvez aussi créer un modèle dans votre app, et qui a un lien vers le
modèle existant (*ForeignKey*, *ManyToManyField*, *OneToOneField*). C'est
comme ça que procède par exemple l'app ``geolocation`` pour enrichir les adresses
de l'app ``persons`` avec des informations de localisation géographique. Il
faudra sûrement utiliser en plus d'autres techniques afin d'obtenir le résultat
escompté :

 - Utilisation de signaux django (``pre_save``, ``post_save`` …).
 - `Hooking des formulaires`_ (vu précédemment)


Dans le cas où vous souhaitez cacher des champs, rappelez vous que bon nombre de
champs sont marqués comme optionnel, et peuvent être cachés en allant dans la
configuration générale ("Configuration des champs").

En dernier recours, si vous souhaitez vraiment pouvoir modifiez un modèle
existant, il reste la possibilité de le *swapper*. Il faut cependant que le
modèle soit *swappable* ; c'est le cas de toutes les classes dérivant de
``CremeEntity`` ( ``Contact``, ``Organisation``, ``Activity`` …) ainsi que
``Address``.

Dans un premier temps, considérons que vous voulez effectuez ce *swapping* en
début de projet ; c'est-à-dire que vous n'avez pas une base de données en
production utilisant le modèle de base que vous voulez modifier. En gros, vous
êtres en début de développement et savez déjà que vous voulez modifiez ce modèle.

Nous allons prendre comme exemple que vous voulez *swapper* ``tickets.Ticket``.

Tout d'abord vous devez créez une app dont le rôle sera d'étendre ``tickets`` et
que nous appellerons ``my_tickets``. Vous devrez donc faire ce que nous avons
fait pour l'app ``Beavers`` : créez un répertoire ``creme/my_tickets/``, contenant
des fichiers ``__init__.py``, ``apps.py``, ``models.py``, ``urls.py`` …
Votre app devra également être ajoutée dans les INSTALLED_CREME_APPS ; pour faire
les choses correctement, elle devra être avant ``tickets``.

Notre ``AppConfig`` va déclarer que l'on étend ``tickets`` : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.apps import CremeAppConfig


    class MyTicketsConfig(CremeAppConfig):
        name = 'creme.my_tickets'
        verbose_name = _(u'Tickets')
        dependencies = ['creme.tickets']

        def register_creme_app(self, creme_registry):
            creme_registry.register_app('my_tickets',
                                        _(u'Tickets'),
                                        extended_app='tickets',  # <= ICI !!
                                       )


Dans le ``models.py``, il faut déclarer un modèle qui va se substituer à
``tickets.models.Ticket``. Le plus facile étant de dériver de
``tickets.models.AbstractTicket`` (sachant que toutes les entités utilisent un
schéma similaire). Il est important de garder ``Ticket`` comme nom de modèle,
afin d'éviter tout un tas de petits désagréments/bugs : ::

    # -*- coding: utf-8 -*-

    from django.db.models import DecimalField
    from django.utils.translation import ugettext_lazy as _

    from creme.creme_core.models import CremeModel

    from creme.tickets.models import AbstractTicket


    class Ticket(AbstractTicket):
        estimated_cost = DecimalField(_(u'Estimated cost (€)'),
                                      blank=True, null=True,
                                      max_digits=10, decimal_places=2,
                                     )  # <= CHAMP SUPPLÉMENTAIRE

        class Meta(AbstractTicket.Meta):
            app_label = 'my_tickets'


Dans ``settings.py``, il vous faut repérez une variable de la forme
``<APP>_<MODEL>_MODEL`` ; dans notre cas il s'agit de : ::

    TICKETS_TICKET_MODEL = 'tickets.Ticket'

Nous allons surcharger cette variable dans notre ``project_settings.py`` de la
manière suivante : ::

    TICKETS_TICKET_MODEL = 'my_tickets.Ticket'

Cela indique la classe à utiliser concrètement à la place de ``tickets.Ticket``.

Vous pouvez à présent générer le répertoire de migrations comme nous l'avons
déjà vu.

Si on jette un œil au fichier ``tickets/urls.py``, on voit qu'un certain nombre
d'URLs ne sont définies que lorsque le modèle n'est pas personnalisé : ::

    [...]

    if not ticket_model_is_custom():
        from .views import ticket

        urlpatterns += [
            url(r'^tickets$',                        ticket.listview,   name='tickets__list_tickets'),
            url(r'^ticket/add$',                     ticket.add,        name='tickets__create_ticket'),
            url(r'^ticket/edit/(?P<ticket_id>\d+)$', ticket.edit,       name='tickets__edit_ticket'),
            url(r'^ticket/(?P<ticket_id>\d+)$',      ticket.detailview, name='tickets__view_ticket'),
        ]

    [...]

Ces vues ne peuvent évidemment pas respecter vos règles métier ; par exemple la
vue de création peut planter si vous avez ajouté dans ``my_tickets.Ticket`` un champ à
la fois obligatoire et non éditable. Dans la mesure où vous avez choisi de
définir votre modèle personnalisé, il faut fournir nos propres URLs qui sont
sûres de fonctionner.

Dans notre cas, les vues de base devraient tout à fait suffire (les formulaires
seront assez intelligents pour utiliser votre nouveau champ), et donc nous
pouvons définir ``my_tickets/urls.py`` tel que : ::

    # -*- coding: utf-8 -*-

    from django.conf.urls import url

    from creme.tickets.views import ticket


    urlpatterns += [
        url(r'^my_tickets$',                        ticket.listview,   name='tickets__list_tickets'),
        url(r'^my_ticket/add$',                     ticket.add,        name='tickets__create_ticket'),
        url(r'^my_ticket/edit/(?P<ticket_id>\d+)$', ticket.edit,       name='tickets__edit_ticket'),
        url(r'^my_ticket/(?P<ticket_id>\d+)$',      ticket.detailview, name='tickets__view_ticket'),
    ]

**Note** : l'important est de définir des URLs avec le même *name* (utilisé par
``reverse()``), ainsi que les mêmes arguments ("ticket_id" ici).

Dans des cas plus complexes, vous voudrez sûrement utiliser vos propres formulaire
ou template. Il en vous reste plus qu'à définir vos propres vues quand c'est
nécessaire. Gardez à l'esprit qu'il vaut mieux copier/coller le moins de chose
possible ; les apps de base fournissent des vues abstraites qui vous permettront
en général de passer les arguments qui vous arrangent. Par exemple, si vous
voulez définir la vue de création de ``my_tickets.Ticket`` avec votre propre formulaire
(dont l'écriture n'est pas traité ici, vous savez déjà le faire), vous pourriez
écrire quelque chose comme ça : ::

    # -*- coding: utf-8 -*-

    from creme.creme_core.auth.decorators import login_required, permission_required

    from creme.tickets.views.ticket import abstract_add_ticket

    from creme.my_tickets.forms import MyTicketForm  # <= à écrire aussi !


    @login_required
    @permission_required(('my_tickets', 'my_tickets.add_ticket'))
    def add(request):
        return abstract_add_ticket(request, form=MyTicketForm)


**Un peu plus loin** : vous avez peut-être remarqué que dans ``settings.py`` se
trouvaient aussi aussi des variable de la forme ``<APP>_<MODEL>_FORCE_NOT_CUSTOM``
(par exemple ``TICKETS_TICKET_FORCE_NOT_CUSTOM``). Comme nous l'avons dit, il est
préférable de procéder au *swapping* avant la création de la base de données. Or
vous pourriez pressentir qu'à l'avenir un modèle doivent être *swappé*, mais vous
n'en êtes pas encore certain. Et même en le *swappant* par précaution, vous n'avez
pas forcément le temps de définir ses vues. C'est là qu'interviennent ces variables
``*_FORCE_NOT_CUSTOM`` ; elles servent justement à *swapper* des modèles en avance,
tout en forçant Creme à considérer que ces modèles ne sont pas personnalisés ;
ainsi les vues 'normales' (et les tests unitaires aussi) seront utilisées malgré
tout. Cependant, il faut faire attention à réellement utiliser des modèles qui
soient identiques à leur modèle de base, en se contentant par exemple de juste
dériver des modèles abstraits correspondants. Dans le cas contraire, les vues
de base n'ont aucune garantie de fonctionner correctement. Utilisez donc ces
variables avec précaution.

**Comment swapper un modèle à posteriori ?** Si vous êtes dans un des 2 cas
suivants :

- Vous avez une installation de Creme 1.5 dans laquelle vous modifiez un modèle
  de base grâce à la fonction ``contribute_to_model()``, et vous voulez passer
  sur Creme 1.6 (dans laquelle ``contribute_to_model()`` n'existe plus).
- Vous avez une installation de Creme 1.6 en production, et vous vous apercevez
  que pour faire ce que vous voulez, vous devez *swapper* un modèle (et donc
  c'est la version non *swappée* qui est utilisée dans votre code/base actuellement).

Attention ! Vous devriez évidemment tester les étapes suivantes sur un duplicat
de votre base de données de production, et toujours avoir une sauvegarde de votre
base de production avant d'appliquer les modifications dessus (c'est valable de
manière générale, mais 'est d'autant plus vrai que les manipulations suivantes
sont assez sensibles).


#. Vous devez écrire (dans votre propre app évidemment), un modèle *swappant*,
   qui **doit correspondre exactement** au modèle tel qu'il est actuellement en
   base ; c'est-à-dire :

   - si vous avez un code 1.6, c'est simple, il suffit que votre modèle se
     content de dériver du modèle abstrait correspondant (ex: ``AbstractTicket``)
     **sans ajouter** de nouveaux champs (pour le moment bien sûr).
   - si vous étiez un utilisateur de ``contribute_to_model()`` uniquement pour
     ajouter de nouveaux champs, alors dérivez de la classe abstraite, et
     ajoutez lesdits champs dans votre propre modèle.
   - si enleviez des champs grâce à ``contribute_to_model()``, alors le plus
     simple est de recopier le modèle abstrait, puis de commenter les champs
     enlevés ; vous devez aussi rajouter les champs que vous aviez ajoutés avec
     ``contribute_to_model()`` comme dans le cas précédent.

#. Modifier le *setting* ``<APP>_<MODEL>_MODEL`` pour pointer vers votre modèle
   comme vu précédemment.

#. Attention, c'est l'étape la plus subtile : renommez la table correspondant au
   modèle de base (dans PHPMyAdmin ou pdAdmin par exemple), en lui donnant le
   nom que donnerait Django à la table de votre modèle. Comprenez par là qu'il
   est important de suivre la convention Django. Dans l'exemple des tickets
   traité au dessus, ça voudrait dire renommer la table "tickets_ticket" en
   "my_tickets_ticket". Normalement, les SGBDR récents s'en sortent bien, et
   les contraintes associées (donc notamment les *ForeignKeys* vers cette table)
   sont correctement modifiées. Mais certaines vieilles version de MySQL ne font
   pas ce travail correctement, d'où l'importance de tester avec un environnement
   identique à votre environnement de production.

#. Modifiez, dans la table "django_content_type" la ligne correspondant au modèle ;
   par exemple la ligne app_label="tickets"/model="ticket" doit maintenant
   contenir app_label="my_tickets" (model="ticket" ne change pas si vous avez bien
   gardé ``Ticket`` comme nom).

#. Générez la migration de votre nouveau modèle. Cependant, comme la table existe
   déjà en base il faut *faker* cette migration : ::

        > python manage.py migrate my_tickets --fake-initial

#. Comme nous l'avons vu, il faut gérer les vues de notre nouveau modèle.


À ce moment, votre installation devrait être fonctionnelle ; si vous étiez parti
d'une installation 1.6, il vous reste encore à ajouter les nouveaux champs.


Liste des différents services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Vous pouvez personnaliser l'affichage des champs des modèles (vue détaillée,
  vue en liste) grâce à ``creme_core.gui.field_printers.field_printers_registry``.
- Vous pouvez enregistrer des algorithmes de rappel par e-mail via
  ``creme_core.core.reminder.reminder_registry``.
- Vous pouvez enregistrer de nouvelles périodicité dans
  ``creme_core.utils.date_period.date_period_registry``.
- Vous pouvez enregistrer de nouveaux intervalles de temps dans
  ``creme_core.utils.date_range.date_range_registry``.
- L'app *billing* permet d'enregistrer des algorithmes de génération de numéros
  de facture. Regardez le fichier ``billing/apps.py``, dans la méthode
  ``register_billing_algorithm()`` pour savoir comment faire.
- L'app *recurrents* permet de générer des objets de manière récurrente. Regardez
  les fichiers ``recurrents_register.py`` dans ``billing`` ou ``tickets``.
- L'app *crudity* permet de créer des objets depuis des données externes, comme
  les e-mails par exemple.


Tests unitaires et développement piloté par les tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Creme utilise autant que possible le
`Développement Piloté par les Tests <http://fr.wikipedia.org/wiki/Test_Driven_Development>`_
(TDD). Ainsi les tests des fonctionnalités sont écrits en même temps que les
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
        print('Error in <%s>: %s' % (__name__, e))


    class BeaverTestCase(CremeTestCase):
        @classmethod
        def setUpClass(cls):
            CremeTestCase.setUpClass()
            cls.populate('creme_core', 'beavers')

        def test_createview(self):
            user = self.login()

            self.assertEqual(0, Beaver.objects.count())
            url = '/beavers/beaver/add'
            self.assertGET200(url)

            name   = 'Hector'
            status = Status.objects.all()[0]
            response = self.client.post(url, follow=True,
                                        data={'user':     user.pk,
                                              'name':     name,
                                              'birthday': '2015-12-3',
                                              'status':   status.id,
                                             }
                                       )
            self.assertNoFormError(response)

            beavers = Beaver.objects.all()
            self.assertEqual(1, len(beavers))

            beaver = beavers[0]
            self.assertEqual(name,   beaver.name)
            self.assertEqual(status, beaver.status)
            self.assertEqual(datetime.date(year=2015, month=12, day=3),
                             beaver.birthday
                            )


Remarques:
 - Les imports initiaux sont mis dans un bloc try/except, car si une erreur se
   produit au moment de l'importation des modules, l'exception est capturée
   silencieusement par l'infrastructure de test, et vos tests ne seront pas
   exécutés (tout se passera comme s'il y avait 0 test).
 - La méthode ``setUpClass()`` est appelée une seule fois, avant que les tests soient
   exécutés. Y lancer les commandes *populate* utiles permet d'être bien plus
   rapide que si on les lance dans la méthode ``setUp()``, exécutée avant
   chaque test de la classe.

Vous pouvez alors lancer vos tests : ::

    > python manage.py test beavers

**Astuce** : travaillez avec SQLite lorsque vous écrivez le nouveau code.
Vous pouvez même, lorsque vous êtes dans une passe de TDD (c'est-à-dire que
vous ne cherchez pas à voir le résultat dans votre navigateur) vous passer de
l'écriture des migrations à chaque changement dans un modèle, avec les lignes
suivantes dans votre ``local_settings.py`` : ::

    import sys

    # ATTENTION ! Ne fonctionne qu'avec SQLite
    if 'test' in sys.argv:
        MIGRATION_MODULES = {
            'auth':           'auth.migrations_not_used_in_tests',
            'creme_core':     'creme_core.migrations_not_used_in_tests',
            'creme_config':   'creme_config.migrations_not_used_in_tests',
            'media_managers': 'media_managers.migrations_not_used_in_tests',
            'documents':      'documents.migrations_not_used_in_tests',
            'assistants':     'assistants.migrations_not_used_in_tests',
            'activities':     'activities.migrations_not_used_in_tests',
            'persons':        'persons.migrations_not_used_in_tests',
            'graphs':         'graphs.migrations_not_used_in_tests',
            'reports':        'reports.migrations_not_used_in_tests',
            'products':       'products.migrations_not_used_in_tests',
            'recurrents':     'recurrents.migrations_not_used_in_tests',
            'billing':        'billing.migrations_not_used_in_tests',
            'opportunities':  'opportunities.migrations_not_used_in_tests',
            'commercial':     'commercial.migrations_not_used_in_tests',
            'events':         'events.migrations_not_used_in_tests',
            'crudity':        'crudity.migrations_not_used_in_tests',
            'emails':         'emails.migrations_not_used_in_tests',
            'sms':            'sms.migrations_not_used_in_tests',
            'projects':       'projects.migrations_not_used_in_tests',
            'tickets':        'tickets.migrations_not_used_in_tests',
            'cti':            'cti.migrations_not_used_in_tests',
            'activesync':     'activesync.migrations_not_used_in_tests',
            'vcfs':           'vcfs.migrations_not_used_in_tests',
            'polls':          'polls.migrations_not_used_in_tests',
            'mobile':         'mobile.migrations_not_used_in_tests',
            'geolocation':    'geolocation.migrations_not_used_in_tests',

            'beavers':        'beavers.migrations_not_used_in_tests',
        }

Une fois votre code satisfaisant, prenez le temps de lancer les tests avec MySQL
et/ou PostgreSQL ; il vous faut pour ça commenter les lignes données au dessus
et avoir écrit les migrations.

**Astuce** : si vous êtes amené à lancer plusieurs fois les tests avec MySQL/PostgreSQL
pour corriger un test réfractaire par exemple, utilisez l'option ``--keepdb`` de
la commande ``test`` afin de grandement réduire le temps que prend la commande
(il ne faut en revanche pas modifier les modèles entre 2 exécutions des tests).
