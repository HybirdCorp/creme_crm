======================================
Carnet du développeur de modules Creme
======================================

:Author: Guillaume Englert
:Version: 26-04-2021 pour la version 2.3 de Creme
:Copyright: Hybird
:License: GNU FREE DOCUMENTATION LICENSE version 1.3
:Errata: Hugo Smett, Patix

.. contents:: Sommaire


Introduction
============

Ce document est destiné à des personnes voulant ajouter ou modifier des fonctionnalités
au logiciel de gestion de la relation client Creme_. Il ne s'agit pas d'une documentation
exhaustive de l'API de Creme, mais d'un didacticiel montrant la création d'un module, pas à pas.


Pré-requis
==========

- Avoir des bases en programmation de manière générale ; connaître le langage Python_ est un gros plus.
- Connaître un minimum le langage HTML.
- Connaître le logiciel git_.

Creme est développé en utilisant un cadriciel (framework) Python spécialisé dans
la création de sites et applications Web : Django_.
Si vous comptez réellement développer des modules pour Creme, la connaissance de
Django sera sûrement nécessaire. Heureusement la documentation de celui-ci est vraiment
complète et bien faite ; vous la trouverez ici : https://docs.djangoproject.com/fr/3.1/.
Dans un premier temps, avoir lu le `didacticiel <https://docs.djangoproject.com/fr/3.1/intro/overview/>`_
devrait suffire.

Creme utilise aussi la bibliothèque JavaScript (JS) jQuery_ ; il se peut que pour
programmer certaines fonctionnalités de vos modules vous deviez utiliser du
(JS) du côté du client (navigateur Web) ; connaître jQuery serait
alors un avantage. Cependant ce n'est pas obligatoire et nous utiliserons des
exemples principalement sans JS dans le présent document.

.. _Creme: https://cremecrm.com
.. _Python: https://www.python.org
.. _git: https://git-scm.com
.. _Django: https://www.djangoproject.com
.. _jQuery: https://jquery.com

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

 - Fork du dépôt *git* officiel pour avoir votre dépôt.
 - Clone de votre dépôt *git* (en se plaçant sur la branche "v2.2").
 - Configuration de votre SGBDR.
 - Configuration de votre serveur Web (le serveur de développement livré avec
   Django est un bon choix ici).


Configuration du fichier ``local_settings.py``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Il ne vaut mieux pas utiliser le système de cache des templates quand vous
développez, afin de ne pas avoir à relancer le serveur à chaque modification
de template : ::

    from .settings import TEMPLATES
    TEMPLATES[0]['OPTIONS']['loaders'] = (
        'django.template.loaders.app_directories.Loader',
        'django.template.loaders.filesystem.Loader',
    )

Activer les *warnings* vous permettra par exemple de voir que vous utilisez
du code obsolète (*deprecated*), ce qui vous sera utile lors vous mettrez à
jour la version sous-jacente de Creme (ledit code obsolète étant en général
supprimé dans la version suivante -- notez que le message va souvent
indiquer quelle fonction/classe utiliser à la place). La configuration
suivante permet d'afficher les *warnings*, mais chacun une seule fois
(ce qui évite de polluer votre terminal d'informations redondantes) : ::

    import warnings
    warnings.simplefilter('once')


Outils supplémentaires
~~~~~~~~~~~~~~~~~~~~~~

Nous vous conseillons d'utiliser l'app `django extensions <https://github.com/django-extensions/django-extensions>`_
qui apporte des commandes supplémentaires intéressantes (``runserver_plus``,
``shell_plus``, ``clean_pyc``, …).


Utilisation de git
~~~~~~~~~~~~~~~~~~

Bien que le code que vous écrirez résidera dans son propre répertoire, ce
répertoire sera parmi les autres modules de Creme. Dans une future version de
Creme, la séparation entre votre code et celui de Creme devrait être plus
facile et sera documentée.

Pour le moment on va se contenter de travailler dans une branche à part : ::

    > git checkout -b beavers

À chaque fois que vous aurez ajouté une nouvelle fonctionnalité, vous pourrez
créer un *commit* : ::

    > git commit -a

À n'importe quel moment nous pouvez visualiser les modifications faites depuis
le dernier *commit* : ::

    > git diff

À la fin de votre session de travail, vous pouvez sauvegarder votre travail
dans votre  dépôt : ::

    > git push origin beavers

Lorsque vous voudrez resynchroniser votre code avec celui de Creme (pour
avoir la dernière mise-à-jour mineure par exemple), il faudra passer par une
classique phase de **rebase**.


Création du répertoire parent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Plaçons nous dans notre projet, dans le répertoire ``creme/`` : ::

    > cd creme_crm/creme

Il existe une commande pour créer une app (``django-admin startapp``), cependant
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


Nous venons de créer notre première classe de modèle, ``Beaver``. Ce modèle correspondra
à une table dans notre Système de Gestion de Base de Données (SGBD) : *beavers_beaver*.
Pour le moment, on ne stocke pour chaque castor que son nom et sa date de naissance.
Notre modèle dérive de ``CremeEntity``, et non d'un simple ``DjangoModel`` : ceci
permettra aux castors de disposer de Propriétés, de Relations, de pouvoir être affichés
dans une vue en liste, ainsi que beaucoup d'autres services.

En plus des champs contenus en base (fields), nous déclarons :

- La classe ``Meta`` qui permet d'indiquer notamment l'app à laquelle appartient notre modèle.
- La méhode ``__str__`` qui permet d'afficher de manière agréable les objets ``Beavers``.


Là encore, pour que le répertoire ``models/`` soit un module, nous devons y mettre
un second fichier nommé ``__init__.py``, et qui contient : ::

    # -*- coding: utf-8 -*-

    from .beaver import Beaver


Ainsi, au démarrage de Creme, notre modèle sera importé automatiquement par Django, et
sera notamment relié à sa table dans le SGDB.


Installer notre module
~~~~~~~~~~~~~~~~~~~~~~

Éditez le fichier ``creme/project_settings.py`` en y copiant depuis le fichier de
configuration générale ``creme/settings.py`` le tuple INSTALLED_CREME_APPS. ::

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

Notez que par rapport à la configuration de base, nous avons ajouté à la fin du
tuple notre app.

**Remarque** : nous utilisons ``creme/project_settings.py`` plutôt que
``creme/local_settings.py`` dans la mesure où la liste des apps installées dans
le projet devrait sûrement être partagée avec les différents membres de l'équipe
(développeurs, administrateurs).


Créer la table dans la base de données
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Toujours depuis le répertoire ``creme/``, lancez les commandes suivantes : ::

    > python creme/manage.py makemigrations beavers

Cela devrait créer un répertoire ``creme/beavers/migrations/`` avec dedans un
fichier ``__init__.py`` et un fichier ``0001_initial.py``. Ce dernier donne
à Django la description de la table qui va contenir nos castors : ::

    > python creme/manage.py migrate beavers
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

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.apps import CremeAppConfig


    class BeaversConfig(CremeAppConfig):
        name = 'creme.beavers'
        verbose_name = _('Beavers management')
        dependencies = ['creme.creme_core']

        def register_entity_models(self, creme_registry):
            from .models import Beaver

            creme_registry.register_entity_models(Beaver)



Le singleton ``creme_registry`` permet d'enregistrer les modèles dérivants de
``CremeEntity`` (appel à ``creme_registry.register_entity_models()``) et que
l'on veut disposer sur eux des services tels que la recherche globale, la
configuration des boutons et des blocs par exemple. C'est le cas la plupart du
temps où l'on dérive de ``CremeEntity``.


Nous venons de définir la configuration de notre app pour Django ; mais afin qu'il
vienne chercher notre classe, il reste un petite chose à faire. Éditez le fichier
``beavers/__init__.py`` pour y mettre la ligne suivante : ::

    default_app_config = 'creme.beavers.apps.BeaversConfig'


Si nous lançons Creme avec le serveur de développement de Django, et que nous y
connectons avec notre navigateur Web (à l'adresse définie par SITE_DOMAIN dans
la configuration), que se passe-t-il ? ::

    > python creme/manage.py runserver


Il n'y a aucune trace de notre nouvelle app. Mais pas d'inquiétude, nous allons
y remédier.


Notre première vue : la vue de liste
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Nous allons à présent créer la vue permettant d'afficher la liste des castors,
à laquelle on accède par l'URL: '/beavers/beavers'.

Ajoutons d'abord un nouveau répertoire nommé ``views/`` dans ``beavers/``,
ainsi que le ``__init__.py`` habituel : ::

    > mkdir views
    > cd views
    > touch __init__.py


Dans ``views/``, nous créons le fichier ``beaver.py`` tel que : ::

    # -*- coding: utf-8 -*-

    from creme.creme_core.views import generic

    from creme.beavers.models import Beaver


    class BeaversList(generic.EntitiesList):
        model = Beaver


On doit maintenant lier cette vue à son URL. Jetons un coup d'œil au fichier
``creme/urls.py`` ; on y trouve la configuration des chemins de base pour chaque
app. Nous remarquons ici que pour chaque app présente dans le tuple
INSTALLED_CREME_APPS, on récupère le fichier ``urls.py`` se trouvant dans le
répertoire ``nom_de_votre_appli/``.

Nous n'avons donc pas à toucher à ``creme/urls.py`` et nous créons juste le
fichier ``urls.py`` dans ``beaver/`` : ::

    # -*- coding: utf-8 -*-

    from django.urls import re_path

    from .views import beaver

    urlpatterns = [
        re_path(r'^beavers[/]?$', beaver.BeaversList.as_view(), name='beavers__list_beavers'),
    ]

Notez :

 - le dernier paramètre de ``re_path()``, qui permet de nommer notre URL. La
   convention Creme est de la forme 'mon_app' + '__list_' + 'mes_modeles' pour la
   vue en liste.
 - le '/' final de notre URL qui est optionel (c'est la politique des URLs
   de Creme en général).

Rajoutons enfin la méthode ``get_lv_absolute_url()`` dans notre modèle. Cette
méthode permettra par exemple de revenir sur la liste des castors lorsqu'on
supprimera une fiche castor : ::

    # -*- coding: utf-8 -*-

    [...]

    from django.urls import reverse


    class Beaver(CremeEntity):
        [...]

        @staticmethod
        def get_lv_absolute_url():
            return reverse('beavers__list_beavers')


**Note** : la méthode ``reverse()``, qui permet de retrouver une URL par le nom
donné à la fonction ``re_path()`` utilisée dans notre ``urls.py``.

Nous pouvons maintenant accéder depuis notre navigateur à la liste des castors
en la tapant à la main dans la barre d'adresse… enfin presque. En effet on nous
demande de créer une vue pour cette liste. Ceci fait, on arrive bien sûr une
liste des castors… vide. Forcément, aucun castor n'a encore été créé.


La vue de création
~~~~~~~~~~~~~~~~~~

Créez un répertoire ``beavers/forms``, avec le coutumier ``__init__.py`` : ::

    > mkdir forms
    > cd forms
    > touch __init__.py


Dans ``forms/``, nous créons alors le fichier ``beaver.py`` : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.forms import CremeEntityForm

    from ..models import Beaver


    class BeaverForm(CremeEntityForm):
        class Meta(CremeEntityForm.Meta):
            model = Beaver


Il s'agit d'un formulaire lié à notre modèle tout simple.

**Note** : la plupart des vues de création d'entité que vous trouverez dans les
apps fournies de base par Creme n'utilisent pas de formulaire classique façon
Django. À la place elles utilisent le système de formulaire personnalisé
(CustomForm) de Creme qui permet aux utilisateurs finaux de configurer les
champs eux-mêmes. Les CustomForms sont abordés plus loin, et on utilisera dans
un premier temps les formulaires classiques, par simplicité.

Puis nous modifions ``views/beaver.py``, en ajoutant ceci à la fin (vous pouvez
ramener les ``import`` au début, avec les autres directives ``import`` bien sûr) : ::

    from ..forms.beaver import BeaverForm

    class BeaverCreation(generic.EntityCreation):
        model = Beaver
        form_class = BeaverForm


Rajoutons l'entrée qui référence ``beaver.BeaverCreation`` dans ``beavers/urls.py`` : ::

    urlpatterns = [
        re_path(r'^beavers[/]?$',    beaver.BeaversList.as_view(),    name='beavers__list_beavers'),
        re_path(r'^beaver/add[/]?$', beaver.BeaverCreation.as_view(), name='beavers__create_beaver'),
    ]


Il reste à mettre une méthode ``get_create_absolute_url()`` dans notre modèle,
ainsi que les attributs ``creation_label`` et ``save_label``, qui permettent de
nommer correctement les éléments d'interface (bouton, menu etc…) : ::

    # -*- coding: utf-8 -*-


    class Beaver(CremeEntity):
        [...]

        creation_label = _('Create a beaver')  # Intitulé du formulaire de création
        save_label	   = _('Save the beaver')  # Intitulé du bouton de sauvegarde

        [...]

        @staticmethod
        def get_create_absolute_url():
            return reverse('beavers__create_beaver')


Si nous rechargeons la vue des castors, un bouton 'Create a beaver' est apparu.
Quand nous cliquons dessus, nous obtenons bien le formulaire attendu. Mais quand
nous validons notre formulaire correctement rempli, nous obtenons une erreur 500.
Pas de panique : la classe de vue ``EntityCreation`` a juste demandé à afficher
la vue détaillée de notre castor. Celui-ci a bien été créé, mais cette vue
n'existe pas encore.


La vue détaillée
~~~~~~~~~~~~~~~~

Ajoutons cette classe de vue (dans ``views/beaver.py`` donc, si vous suivez) : ::

    class BeaverDetail(generic.EntityDetail):
        model = Beaver
        pk_url_kwarg = 'beaver_id'


Il faut aussi éditer ``beavers/urls.py`` pour ajouter cette URL : ::

    urlpatterns = [
        re_path(r'^beavers[/]?$',                   beaver.BeaversList.as_view(),    name='beavers__list_beavers'),
        re_path(r'^beaver/add[/]?$',                beaver.BeaverCreation.as_view(), name='beavers__create_beaver'),
        re_path(r'^beaver/(?P<beaver_id>\d+)[/]?$', beaver.BeaverDetail.as_view(),   name='beavers__view_beaver'),  # < -- NEW
    ]

En rafraîchissant notre page dans le navigateur, nous obtenons bien la vue
détaillée espérée.

**Note** : l'icone de notre fiche ne fonctionne pas pour le moment ; ne vous
inquiétez pas, ça sera réglé un peu plus tard.

Pour que les prochaines créations de castor n'aboutissent pas sur une erreur 404,
nous créons la méthode ``get_absolute_url()`` : ::

    # -*- coding: utf-8 -*-

    [...]


    class Beaver(CremeEntity):
        [...]

        def get_absolute_url(self):
            return reverse('beavers__view_beaver', args=(self.id,))


La vue d'édition
~~~~~~~~~~~~~~~~

Contrairement aux autres types de fiche, nos castors ne peuvent pas (encore) être
modifiés globalement (avec le gros stylo dans les vues détaillées).

Ajoutons cette vue dans ``views/beaver.py`` : ::

    class BeaverEdition(generic.EntityEdition):
        model = Beaver
        form_class = BeaverForm
        pk_url_kwarg = 'beaver_id'


Rajoutons l'URL associée : ::

    urlpatterns = [
        re_path(r'^beavers[/]?$',                        beaver.BeaversList.as_view(),    name='beavers__list_beavers'),
        re_path(r'^beaver/add[/]?$',                     beaver.BeaverCreation.as_view(), name='beavers__create_beaver'),
        re_path(r'^beaver/edit/(?P<beaver_id>\d+)[/]?$', beaver.BeaverEdition.as_view(),  name='beavers__edit_beaver'),  # < -- NEW
        re_path(r'^beaver/(?P<beaver_id>\d+)[/]?$',      beaver.BeaverDetail.as_view(),   name='beavers__view_beaver'),
    ]


Ainsi que la méthode ``get_edit_absolute_url`` : ::

    # -*- coding: utf-8 -*-

    [...]


    class Beaver(CremeEntity):
        [...]

        def get_edit_absolute_url(self):
            return reverse('beavers__edit_beaver', args=(self.id,))


Faire apparaître les entrées dans le menu
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Nous déclarons 2 entrées de menu (une pour la vue en liste, une pour la vue de
création), dans un nouveau fichier ``beavers/menu.py`` : ::

    # -*- coding: utf-8 -*-

    from creme.creme_core.gui import menu

    from .models import Beaver


    class BeaversEntry(menu.ListviewEntry):
        id = 'beavers-beavers'
        model = Beaver


    class BeaverCreationEntry(menu.CreationEntry):
        id = 'beavers-create_beaver'
        model = Beaver

**Note** : nous avons préfixé les attributs ``id`` avec le nom de notre app ;
c'est une technique qui sera employée régulièrement, afin d'éviter les collisions
d'identifiants entre les différentes apps.

Dans notre fichier ``apps.py``, nous ajoutons la méthode
``BeaversConfig.register_menu_entries()`` pour enregistrer nos 2 classes
nouvellement créées : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_menu_entries(self, menu_registry):
            from . import menu

            menu_registry.register(
                menu.BeaversEntry,
                menu.BeaverCreationEntry,
            )


Pour le moment notre menu n'affiche pas nos nouvelles entrées ; Creme sait juste
que ce sont des entrées valides. Il faut aller dans la l'interface de configuration
du menu (dans le menu "rouage" > Menu ), et utiliser nos nouvelles entrées.
Par exemple, on peut modifier le conteneur "Annuaire" ; l'entrée de la liste des
castors est maintenant proposée lorsque on appuie sur le bouton
«Ajouter des entrées normales». Dans le chapitre suivant, nous verrons comment
ajouter notre entrées de menu lors que l'installation, sans avoir à le faire à la main.

**Un peu plus loin** : nous ajoutons ensuite une entrée dans la fenêtre permettant
de créer tout type d'entité (dans le menu "+ Création" > Autre type de fiche).
Dans notre fichier ``apps.py``, nous ajoutons encore une méthode : ::

    [...]

    def register_creation_menu(self, creation_menu_registry):
        from .models import Beaver

        creation_menu_registry.get_or_create_group(
            'persons-directory', _('Directory'), priority=10,
        ).add_link(
            'beavers-create_beaver', Beaver, priority=20,
        )


Dans notre exemple, nous insérons notre entrée dans le groupe "Annuaire" (utilisé
aussi par l'app ``persons``) ; nous récupérons ce dernier grâce à ``get_or_create_group()``.
Pour afficher la structure des groupes de cette fenêtre, vous pouvez faire
``print(creation_menu_registry.verbose_str)``.


Initialisation du module
~~~~~~~~~~~~~~~~~~~~~~~~

La plupart des modules partent du principe que certaines données existent en base,
que ce soit pour leur bon fonctionnement ou pour rendre l'utilisation de ce module
plus agréable. Par exemple, quand nous avons voulu aller sur notre liste de castor
la première fois, nous avons du créer une vue (i.e. : les colonnes à afficher dans
la liste) ; nous avons aussi du configurer le menu. Nous allons écrire du code qui
sera exécuté au déploiement, et créera la vue de liste et les entrées de menu.

Créez le fichier ``beavers/constants.py``, qui contiendra comme son nom l'indique
des constantes : ::

    # -*- coding: utf-8 -*-

    # NB: ceci sera l'identifiant de notre vue de liste par défaut. Pour éviter
    #     les collisions entres apps, la convention est de construire une valeur
    #     de la forme 'mon_app' + 'hf_' + 'mon_model'.
    DEFAULT_HFILTER_BEAVER = 'beavers-hf_beaver'


Puis créons un fichier : ``beavers/populate.py``. ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import gettext as _

    from creme.creme_core.core.entity_cell import EntityCellRegularField
    from creme.creme_core.gui.menu import ContainerEntry
    from creme.creme_core.management.commands.creme_populate import BasePopulator
    from creme.creme_core.models import (
        HeaderFilter,
        MenuConfigItem,
        SearchConfigItem,
    )

    from .constants import DEFAULT_HFILTER_BEAVER
    from .menu import BeaversEntry
    from .models import Beaver


    class Populator(BasePopulator):
        dependencies = ['creme_core', 'persons']

        def populate(self):
            HeaderFilter.create(
                pk=DEFAULT_HFILTER_BEAVER, name=_('Beaver view'), model=Beaver,
                cells_desc=[
                    (EntityCellRegularField, {'name': 'name'}),
                    (EntityCellRegularField, {'name': 'birthday'}),
                ],
            )

            SearchConfigItem.create_if_needed(Beaver, ['name'])

            if not MenuConfigItem.objects.filter(entry_id__startswith='beavers-').exists():
                directory = MenuConfigItem.objects.filter(
                    entry_id=ContainerEntry.id,
                    entry_data={'label': _('Directory')},
                ).first()
                if directory is not None:
                    MenuConfigItem.objects.create(
                        entry_id=BeaversEntry.id, order=50, parent=directory,
                    )

Explications :

- Nous créons une vue de liste (``HeaderFilter``) avec 2 colonnes, correspondant
  tout simplement au nom et la date de naissance de nos castors. Pour les
  colonnes, la classe ``EntityCellRegularField`` correspond à des champs
  normaux de nos castors (il y a d'autres classes, comme ``EntityCellRelation``
  par exemple).
- La ligne avec ``SearchConfigItem`` sert à configurer la recherche globale :
  elle se fera sur le champ 'name' pour les castors.
- Nous ajoutons une entrée de menu dans la section "Annuaire", normalement créée
  par l'app ``persons`` (nous avons donc mis cette app en tant que dépendance,
  avec l'attribut ``dependencies``). Nous ne créons cette entrée que si aucune
  entrée correspondant à notre app existe en base de donnée (ce qui est une
  méthode perfectible pour essayer de ne pas modifier le menu après la première
  exécution de la commande…).

Le code est exécuté par la commande ``creme_populate``. La commande permet de ne
'peupler' que notre app. Dans ``creme/``, exécutez : ::

    > python creme/manage.py creme_populate beavers


En réaffichant votre liste de castors, la deuxième vue est bien là.

**Allons plus loin**: améliorons maintenant notre liste de castors afin de nous
assurer que lorsqu'un utilisateur se connecte avec une session neuve, la vue par
défaut est utilisée (sinon c'est la première par ordre alphabétique): ::

    [...]
    from ..constants import DEFAULT_HFILTER_BEAVER  # <- NEW

    [...]

    class BeaversList(generic.EntitiesList):
        model = Beaver
        default_headerfilter_id = DEFAULT_HFILTER_BEAVER  # <- NEW


Gestion des icônes
~~~~~~~~~~~~~~~~~~

Le système d'icône va chercher dans les images du thème actif, en fonction du
nom qu'on lui demande et en rajoutant la taille adaptée au contexte.

Creme est livré avec les icônes pour les apps incluses de base. Par exemple,
pour le thème "icecream", dans le répertoire ``creme/static/icecream/images``
vous trouverez un fichier "alert_22.png" ; son nom d'icône est "alert" (ce nom
est par exemple utilisé par certains *templatetags*), et le suffixe "_22" indique
sa taille de 22 x 22 pixels.

Vous pouvez ajouter vos propres icônes dans ``creme/beavers/static/THEME/images/`` ;
(THEME est à remplacer par le nom du thème, "icecream" ou "chantilly" pour les
thèmes fournis de base). N'oubliez pas de lancer la commande ``generatemedia``
quand vous ajoutez des images.

En plus des icônes nommées explicitement, Creme permet d'associer automatiquement
une icône à un type de fiche. Ajoutons une méthode dans notre fichier
``beavers/apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_icons(self, icon_registry):
            from .models import Beaver

            icon_registry.register(Beaver, 'images/contact_%(size)s.png')


Ici on utilise l'icône des Contacts qui est fournie par défaut ; libre à vous
d'utiliser une icône plus spécifique bien évidemment.


Localisation (l10n)
~~~~~~~~~~~~~~~~~~~

Jusqu'ici nous avons mis uniquement des labels en anglais. Donc même si votre
navigateur est configuré pour récupérer les pages en français quand c'est possible,
l'interface du module *beavers* reste en anglais. Mais nous avons toujours utilisé
les fonctions ``gettext`` et ``gettext_lazy`` (importées en tant que '_') pour
'wrapper' nos labels. Il va donc être facile de localiser notre module.
Dans ``beavers/``, créez un répertoire ``locale``, puis lancez la commande qui
construit le fichier de traduction (en français ici) : ::

    > mkdir locale
    > django-admin makemessages -l fr
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


Il suffit maintenant de compiler notre fichier de traduction avec la commande
suivante : ::

    > django-admin compilemessages
    processing file django.po in [...]/creme_crm/creme/beavers/locale/fr/LC_MESSAGES

Le fichier ``beavers/locale/fr/LC_MESSAGES/django.mo`` est bien généré. Si vous
relancez le serveur Web, les différents labels apparaissent en français, pour peu
que votre navigateur et votre utilisateur soient configurés pour, et que que le
*middleware* 'django.middleware.locale.LocaleMiddleware' soit bien dans votre
``settings.py`` (ce qui est le cas par défaut).


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


**Notes** : l'attribut ``is_custom`` sera utilisé par le module *creme_config*
comme nous allons le voir plus tard. Il est important qu'il se nomme ainsi, et
qu'il soit de type ``BooleanField``. Notez l'utilisation de ``set_tags()`` qui permet
de cacher ce champ à l'utilisateur (nous reviendrons plus tard sur les tags).
Donner un ordre par défaut (attribut ``ordering`` de la classe ``Meta``) agréable
pour l'utilisateur est important, puisque c'est cet ordre qui sera utilisé par
exemple dans les formulaires (à moins que vous n'en précisiez un autre
explicitement, évidemment).

**Notes** : nous avons utilisé la fonction de traduction ``pgettext_lazy()``
qui prend un paramètre de contexte. Cela va permettre d'éviter les éventuelles
collisions avec des chaînes de texte dans autres applications. Le terme "status"
étant vague, il se retrouve dans d'autres apps, et ont pourraient imaginer que
dans certaines langues (ou traductions personnalisées), la traduction soit
différente selon le cas. Dans Creme, nous préfixons les contextes avec le nom
de l'app plus '-'.


Modifiez *models/__init__.py* : ::

    # -*- coding: utf-8 -*-

    from .status import Status  # <-- NEW
    from .beaver import Beaver


Nous allons générer une première migration qui créé la table correspondante : ::

    > python creme/manage.py makemigrations beavers

Un fichier nommé ``0002_status.py`` est alors créé.

Dans la mesure où nous avons l'intention d'ajouter une *ForeignKey* non nullable
dans notre classe ``Beaver`` (cela rend l'exercice plus intéressant), nous
allons maintenant créer une migration de données (par opposition à migration de
schéma) qui rajoute en base une instance de ``Status`` qui servira de valeur par
défaut pour les instances de castor existantes. Ça sera tout à fait le genre
de chose qui vous arriveront en pratique : une version en production qu'il faut
faire évoluer sans casser les données existantes.

Générer donc cette migration (notez le paramètre ``empty``) : ::

    > python creme/manage.py makemigrations beavers --empty

Un fichier nommé en fonction de la date du jour vient d'être créé. Une fois
celui-ci rénommé en ``0003_populate_default_status.py``, ouvrez le.
Il devrait ressembler à ça : ::

    # -*- coding: utf-8 -*-

    from django.db import migrations, models


    class Migration(migrations.Migration):

        dependencies = [
            ('beavers', '0002_status'),
        ]

        operations = [
        ]


Éditez le pour obtenir : ::

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


Puis ajoutons un champ 'status' dans notre modèle ``Beaver`` : ::

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


**Remarque** : nous avons utilisé une valeur spécifique à Creme pour l'attribut
``on_delete`` : ``CREME_REPLACE``. Cette valeur est équivalente au classique
``PROTECT`` de Django, mais dans l'interface de configuration, si vous supprimez
une valeur de statut, Creme vous proposera de remplacer cette valeur dans les
instances ``Beaver`` qui l'utilisent.

- Il existe aussi ``CREME_REPLACE_NULL`` qui est équivalent à ``SET_NULL`` et
  proposera aussi de mettre à ``null`` les ``ForeignKey`` concernées.
- Les valeurs classiques (``PROTECT``, ``SET_NULL`` …) fonctionnent évidemment.

Il faut maintenant générer la migration correspondante (pas de ``empty``
puisque c'est une migration de schéma) : ::

    > python creme/manage.py makemigrations beavers
    You are trying to add a non-nullable field 'status' to beaver without a default; we can't do that (the database needs something to populate existing rows).
    Please select a fix:
    1) Provide a one-off default now (will be set on all existing rows)
    2) Quit, and let me add a default in models.py
    Select an option:

Nous avions anticipé cette question, et pouvons donc choisir l'option 1, puis
donner la valeur par défaut "1" (puisque c'est l'ID du ``Status`` créé dans la
migration précédente).

On peut maintenant exécuter nos migrations : ::

    > python creme/manage.py migrate

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
            Status.objects.create(id=STATUS_HEALTHY, name=_('Healthy'), is_custom=False)
            Status.objects.create(id=STATUS_SICK,    name=_('Sick'),    is_custom=False)


En mettant l'attribut ``is_custom`` à ``False``, on rend ces 2 ``Status`` non
supprimables. Les constantes créées juste avant sont les PK des 2 objets ``Status``
que l'ont créés ; on pourra ainsi y accéder facilement plus tard.

Avec la variable ``already_populated``, on s'assure que les statuts sont créés
au premier déploiement, mais que si les utilisateurs modifient le nom des statuts
dans l'interface de configuration, leurs modifications ne seront pas écrasées
lors d'une mise à jour (et donc d'un lancement de la commande ``creme_populate``).

Relancez la commande pour 'peupler' : ::

    > python creme/manage.py creme_populate beavers


Le formulaire de création de Beaver nous propose bien ces 2 statuts.

Il ne reste plus qu'à indiquer à Creme de gérer ce modèle dans sa configuration.
Il va encore une fois falloir ajouter une méthode dans notre fichier
``beavers/apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_creme_config(self, config_registry):
            from . import models

            config_registry.register_model(models.Status)


Si vous allez sur le portail de la 'Configuration générale', dans le
'Portails des applications', la section 'Portail configuration Gestion des castors'
est bien apparue : elle nous permet bien de créer des nouveaux ``Status``.

**Allons un peu loin** : vous pouvez préciser les formulaires à utiliser pour
créer ou modifier les statuts si ceux qui sont générés automatiquement ne vous
conviennent pas. Ça pourrait être le cas s'il y a une contrainte métier à
respecter, mais qui n'est pas exprimable via les contraintes habituelles des
modèles (comme ``nullable``) : ::

    [...]

    config_registry.register_model(
        models.Status,
    ).creation(
        form_class=MyStatusCreationForm,
    ).edition(
        form_class=MyStatusEditionForm,
    )


Vous pouvez aussi personnaliser les URLs de création/modification (argument
"url_name" des méthodes ``creation()/edition()``), ainsi que le bloc qui
gère ce modèle (méthode ``brick_class()``).

**Allons un peu loin** : si vous voulez que les **utilisateurs puissent choisir l'ordre**
des statuts (dans les formulaires, dans la recherche rapide des vues de liste etc…),
vous devez rajouter un champ ``order`` comme ceci : ::

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


Notez qu'un ``BasicAutoField`` est par défaut non éditable et non visible, et
qu'il gère l'auto-incrémentation tout seul, donc normalement vous n'aurez pas à
vous occuper de lui.


Faire apparaître notre modèle dans la recherche rapide comme meilleur résultat
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Nous avons précédemment configuré les champs sur lesquels chercher dans nos
instances de Beaver ; ainsi lorsqu'on fait une recherche globale (en haut à
droite dans la barre de menu), et que l'on va dans «Tous les résultats», les
castors trouvés (s'il y en a) sont bien dans un bloc de résultat.

Si vous voulez que les castors apparaissent plus souvent dans les résultats
rapides de recherche (la liste de résultats qui apparaît en temps réel quand
vous tapez dans le champ de recherche) en tant que meilleur résultat, il vous
faut mettre une valeur élevé à l'attribut ``search_score`` de votre modèle
``Beaver``. Dans Creme, de base, le modèle ``Contact`` a une valeur de 101.
Donc si vous mettez un score plus élevé, lorsqu'une chaîne recherchée va à
la fois être trouvée dans (au moins) un contact et un castor, c'est le castor
qui sera privilégié, et il apparaîtra donc en tant que meilleur résultat : ::

    [...]

    class Beaver(CremeEntity):
        [...]

        search_score = 200


Nouveaux types de relation
~~~~~~~~~~~~~~~~~~~~~~~~~~

Vous pouvez évidemment créer de nouveaux types de relation via l'interface de
configuration (Menu > Configuration > Types de relation), puis les utiliser pour
relier des fiches entre elles, filtrer dans les vues en liste, créer des blocs
associés à ce type de relation…

S'il est souhaitable que certains types soient disponibles immédiatement après
le déploiement, alors on va plutôt créer ces types dans notre script
``beavers/populate.py``. Nous allons créer un type de relation reliant un
vétérinaire (contact) et un castor ; en fait on va créer 2 types qui sont
symétriques : «le castor a pour vétérinaire» et
«le vétérinaire s'occupe du castor».

Premièrement, modifions ``beavers/constants.py``, pour rajouter les 2 clés
primaires : ::

    [...]

    REL_SUB_HAS_VET = 'beavers-subject_has_veterinary'
    REL_OBJ_HAS_VET = 'beavers-object_has_veterinary'


**Important** : vos clés primaires doivent satisfaire les 2 critères suivants :

 - Commencer par le nom de votre app, afin de garantir qu'il n'y aura pas de
   collision avec les types définis par les autres apps.
 - Puis une des clés doit se poursuivre par '-subject_', et l'autre '-object_',
   ce qui va permettre à la configuration de distinguer le sens principal du secondaire.
 - Enfin, une chaîne à votre convenance (mais qui devrait idéalement "décrire" le type),
   qui devrait être identique pour les 2 types symétriques, pour des raisons de propreté.

Puis ``beavers/populate.py`` : ::

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


**Notes** : nous avons mis des contraintes sur les types de fiche que l'ont peut relier
(Beaver et Contact en l'occurrence). Nous pourrions aussi, si on créait un type de propriété
«est un vétérinaire» (pour les Contacts), mettre une contrainte supplémentaire : ::

        RelationType.create(
            (constants.REL_SUB_HAS_VET, _('has veterinary'),       [Beaver]),
            (constants.REL_OBJ_HAS_VET, _('is the veterinary of'), [Contact], [VeterinaryPType]),
        )

Les types de relations créés ne sont pas supprimables via l'interface de
configuration (l'argument ``is_custom`` de ``RelationType.create()`` étant par
défaut à ``False``), ce qui est généralement ce qu'on veut.

**Allons un peu loin** : dans certain cas, on veut contrôler finement la
création et la suppression des relations ayant un certain type, à cause de
règles métiers particulières. Par exemple on veut qu'une des fiches à relier
ait telle valeur pour un champ, ou que seuls certains utilisateurs puissent
supprimer ces relations là. La solution consiste à déclarer ces types comme
internes ; les vues de création et de suppression génériques des relations
ignorent alors ces types : ::

        RelationType.create(
            (constants.REL_SUB_HAS_VET, _('has veterinary'),       [Beaver]),
            (constants.REL_OBJ_HAS_VET, _('is the veterinary of'), [Contact]),
            is_internal=True,
        )

C'est alors à vous d'écrire le code de création et de suppression de ces types.
Pour la création, classiquement, on créera la relation dans le formulaire de
création d'une fiche (ex: on assigne un vétérinaire à la création d'un castor),
ou bien dans une vue spécifique (ex: un bloc qui affiche les vétérinaires
associés, et qui permet d'en ajouter/enlever).


Utilisation des blocs
~~~~~~~~~~~~~~~~~~~~~

*Ceci est une simple introduction. Les blocs sont une grosse partie de Creme et pour en
comprendre tous les aspects il faudrait un document entier qui leur serait consacré.*

Quelques explications générales
*******************************

**Configurabilité** : si votre bloc est destiné à être placé sur une vue détaillée
ou sur l'accueil, alors le bloc devrait être configurable ; c'est-à-dire que dans
la configuration des blocs (Menu > Configuration > Blocs), les utilisateurs pourront
définir la présence et la position de votre bloc. Ce dernier doit donc fournir des
des informations utiles à l'interface de configuration, comme son nom ou bien sûr
sur quels types de fiche le bloc peut être affiché (pour les vues détaillés).
Dans le cas où votre bloc est situé sur une vue spécifique, c'est cette dernière
qui fournira la liste des blocs à afficher ; la liste sera donc définie par le code
(à moins que vous codiez un système de configuration "maison" de cette vue évidemment).

**Vue de rechargement** : lorsqu'il y a un changement dans un bloc (ex: l'utilisateur
a ouvert depuis ce bloc une *popup* et fait une modification), ce bloc va être
rechargé, sans qu'il soit besoin de recharger toute la page.
Si vous utilisez une vue générique (vue détaillée ou accueil), alors Creme
renseignera automatiquement l'URL de rechargement (elle est stockée dans le HTML),
qui correspond à une vue existante ; vous n'avez donc rien à faire de ce
côté là. A contrario, si vous créez une vue spécifique avec des blocs, vous devrez
potentiellement écrire votre propre vue de rechargement (si celles fournies par
creme_core ne suffisent pas), et vous devrez dans tous les cas injecter l'URL
dans le contexte du template de votre page.

**Les dépendances** : lorsqu'un bloc est rechargé, il est souvent nécessaire de
recharger d'autres blocs afin que l'affichage reste cohérent (ex: quand on ajoute
une ligne produit dans une facture, on recharge aussi le bloc des totaux).
Creme utilise un système de dépendances simple pour le codeur, et qui donne de
bons résultats en pratique.
Chaque bloc déclare une liste de dépendances. Lorsqu'un bloc doit être rechargé,
tous les blocs de la page sont inspectés, et tous ceux qui ont au moins une
dépendance en commun sont rechargés aussi. La plupart du temps, les dépendances
sont données sous la forme d'une liste de modèles (ex: Contact, Organisation) ;
ces modèles sont ceux qui sont "lus" par le bloc pour afficher ses données.
Mais dans les cas les plus pointus il est possible de générer des dépendances
plus fines.

Exemple : bloc simple de vue détaillée
**************************************

Nous allons faire un simple bloc qui affiche l'anniversaire et l'age d'un castor.
Notez que dans la section `Champs fonctions`_ on écrit un champ fonction
qui fait la même chose (pour l'age), mais de manière réutilisable, notamment
dans un bloc personnalisable ; c'est donc une meilleure approche dans l'absolu.

Créez le fichier ``creme/beavers/bricks.py`` : ::

    from datetime import date

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.gui.bricks import Brick

    from .models import Beaver


    class BeaverAgeBrick(Brick):
        # L'identifiant est utilisé :
        #  - par la configuration pour stocker la position du bloc.
        #  - par le système de rechargement, pour savoir quel bloc doit être recalculé & renvoyé.
        # Encore une fois, on utilise le nom de l'app pour garantir l'unicité.
        id_ = Brick.generate_id('beavers', 'beaver_age')

        # Comme ce bloc affiche des données venant d'un castor, si les données du castor
        # sont modifiées par un autre bloc (notamment si sa date d'anniversaire est modifiée)
        # alors on veut recharger ce bloc pour qu'il reste à jour dans l'affichage.
        dependencies = (Beaver,)

        # Nous allons créer ce template juste après.
        template_name = 'beavers/bricks/age.html'

        # Nom utilisé par l'interface de configuration pour désigner ce bloc.
        verbose_name = _('Age of the beaver')

        # L'interface de configuration ne proposera de mettre ce bloc que sur la vue détaillée
        # des castors (NB: ne pas renseigner cet attribut pour que le bloc puisse être sur
        # tous les types de fiche).
        target_ctypes = (Beaver,)

        # Si on définit cette méthode, on indique que ce bloc est capable de s'afficher
        # sur les vue détaillée (c'est une autre méthode pour l'accueil:  home_display()).
        def detailview_display(self, context):
            # L'entité courante est injectée dans le contexte par la vue generic.EntityDetail
            # et par la vue de rechargement bricks.reload_detailview().
            beaver = context['object']

            birthday = beaver.birthday

            return self._render(self.get_template_context(
                context,
                age=(date.today().year - birthday.year) if birthday else None,
            ))

On crée ensuite le template correspondant, ``creme/beavers/templates/beavers/bricks/age.html`` : ::

    {% extends 'creme_core/bricks/base/table.html' %}
    {% load i18n creme_bricks %}

    {% comment %}
        La classe CSS "beavers-age-brick" n'est pas indispensable, elle permet juste
        de plus facilement modifier l'apparence du bloc via le CSS.
    {% endcomment %}
    {% block brick_extra_class %}{{block.super}} beavers-age-brick{% endblock %}

    {% block brick_header_title %}
        {% brick_header_title title=_('Age') %}
    {% endblock %}

    {# On ne met pas de titre à nos colonnes #}
    {% block brick_table_head %}{% endblock %}

    {# Contenu: nous sommes dans un bloc de type 'table', d'ou les <tr>/<td> #}
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

Pour que le bloc soit pris en compte par Creme, il faut l'enregistrer gràce à ``beavers/apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_bricks(self, brick_registry):
            from . import bricks

            brick_registry.register(bricks.BeaverAgeBrick)

Maintenant le bloc est disponible dans l'interface de configuration des blocs, lorsqu'on
crée/modifie une configuration de vue détaillée pour les castors.

Si on veut que le bloc soit présent dans la configuration de base pour les castors dès
l'installation, il faut s'en occuper dans notre fichier ``beavers/populate.py`` : ::

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

            # Ca c'est le bloc qui affichera les différents champs des castors
            BrickDetailviewLocation.objects.create_for_model_brick(order=5, zone=LEFT, model=Beaver)

            # Les blocs de creme_core qui sont en général présents sur toutes les vues détaillées
            create_bdl(brick=core_bricks.CustomFieldsBrick, order=40,  zone=LEFT,  model=Beaver)
            create_bdl(brick=core_bricks.PropertiesBrick,   order=450, zone=LEFT,  model=Beaver)
            create_bdl(brick=core_bricks.RelationsBrick,    order=500, zone=LEFT,  model=Beaver)
            create_bdl(brick=core_bricks.HistoryBrick,      order=30,  zone=RIGHT, model=Beaver)

            # Là c'est notre nouveau bloc
            create_bdl(brick=BeaverAgeBrick, order=40, zone=RIGHT, model=Beaver)

            # Classiquement on ajoute aussi les blocs de l'app "assistants" (en vérifiant qu'elle est installée)
            # Le lecteur intéressé ira regarder dans le code source d'une app Creme pour voir comment...


Utilisation des boutons
~~~~~~~~~~~~~~~~~~~~~~~

Des boutons peuvent être disposés dans les vues détaillées, juste en dessous du
la bloc de titre, où se trouve le nom de la fiche visionnée. Ces boutons peuvent
généralement être affichés ou non selon la configuration.

Utilisons donc cette fonctionnalité pour créer un ``Ticket`` (venant de l'app
*tickets*) à destination des vétérinaires, que l'on pourra créer lorsqu'un
castor est malade.

Nous commençons par faire la vue de création de ``Ticket``. Puisque le bouton sera
présent sur la vue détaillée des castors, et que lorsque l'on créera un ticket
depuis la fiche d'un castor malade, ce ticket fera référence automatiquement à ce
castor, nous passons l'identifiant du castor dans l'URL, pour que la vue puisse le retrouver.

Dans un nouveau fichier de vue ``beavers/views/ticket.py`` : ::

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
            self.request.user.has_perm_to_view_or_die(beaver)  # On utilise le nom du castor juste après
            initial['description'] = _('{} is sick.').format(beaver)

            return initial


Dans ``beavers/urls.py`` : ::

    [...]

    from .views import beaver, ticket  # <- UPDATE

    [...]

        re_path(r'^ticket/add/(?P<beaver_id>\d+)[/]?$',
                ticket.VeterinaryTicketCreation.as_view(),
                name='beavers__create_ticket',
                ),  # <- NEW

    [...]


Créons le ficher ``beavers/buttons.py`` (ce nom n'est pas une obligation, mais
une convention) : ::

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

Maintenant au tour du fichier template associé, ``beavers/templates/beavers/buttons/ticket.html``: ::

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
            from . import buttons

            button_registry.register(buttons.CreateTicketButton)


Si nous allons dans le menu de configuration (le petit rouage), puis 'Menu bouton',
et que nous éditons la configuration d'un type autre que Castor, notre bouton
n'est pas proposé (c'est ce que nous voulions). En revanche, il est bien proposé
s'il l'on créé une configuration pour le type Castor. Ajoutons le sur cette
configuration nouvellement créée.

En nous rendant sur la fiche d'un castor malade (avec le statut "Sick"), le
bouton est bien apparu. Lorsque l'on clique dessus nous avons bien un
formulaire partiellement pré-rempli.


Utilisation de la création rapide
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dans l'éntrée de menu '+ Création', se trouve la section 'Création rapide'
qui permet de créer des nouvelles fiche via une petite popup (et pas en
allant sur une nouvelle page avec un gros formulaire).

Les formulaires de création rapide sont en général, et pour des raisons évidentes,
des versions simplifiées des formulaires desdites entités. Par exemple, le formulaire
de création rapide des Sociétés n'a que 2 champs ("nom" et "propriétaire").

Ces formulaires sont aussi utilisés dans certains *widgets* de sélection de fiche,
qui permettent de créer des fiches à la volée.

Dans ``forms/beaver.py``, ajoutons une classe de formulaire ; elle doit dériver
de la classe ``CremeEntityQuickForm`` : ::

    [...]

    from creme.creme_core.forms import (
        CremeEntityForm,
        CremeEntityQuickForm,  # <== NEW
    )

    [...]

    class BeaverQuickForm(CremeEntityQuickForm):  # <== NEW
        class Meta(CremeEntityQuickForm.Meta):
            model = Beaver


Puis dans votre ``apps.py``, ajoutez la méthode ``register_quickforms()``
telle que : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_quickforms(self, quickforms_registry):  # <- NEW
            from .forms.beaver import BeaverQuickForm
            from .models import Beaver

            quickforms_registry.register(Beaver, BeaverQuickForm)


**Attention** : n'enregistrez que des modèles dérivant de ``CremeEntity``. Si
vous enregistrez d'autres types de classes, les droits de création ne seront
accordés qu'aux super-utilisateurs (car leurs tests de droit sont évités), en
clair les utilisateurs lambda ne verront pas la classe dans la liste des créations
rapides possibles. C'est à la fois un choix d'interface et une limitation de
l'implémentation, cela pourrait donc changer à l'avenir, mais en l'état il en
est ainsi.


Formulaires personnalisés (CustomForms)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comme évoqué lors de la création de nos premières vues avec formulaire, Creme
utilise généralement pour ses propres entités des formulaires que les
utilisateurs finaux peuvent configurer graphiquement : les formulaires
personnalisés.

Nous allons ici faire un CustomForm simple pour créer nos castors. Tout
d'abord, à la racine de notre app (``beavers/`` donc), nous créons le fichier
``custom_forms.py`` : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.gui.custom_form import CustomFormDescriptor

    from .models import Beaver

    BEAVER_CREATION_CFORM = CustomFormDescriptor(
        id='beavers-beaver_creation',
        model=Beaver,
        verbose_name=_('Creation form for beaver'),
    )

Attention a bien lui donner un identifiant unique ; en préfixant par le nom de
notre app on est tranquille. Dans notre fichier ``populate.py``, nous allons
indiquer les champs utilisés de base dans notre formulaire personnalisé : ::

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
                            # NB: adaptez en fonction des champs de votre modèle évidemment
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

Déclarons ensuite notre descripteur de formulaire ; dans notre fichier
``beavers/apps.py``, ajoutons une nouvelle méthode : ::


    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_custom_forms(self, cform_registry):
            from . import custom_forms

            cform_registry.register(custom_forms.BEAVER_CREATION_CFORM)


Si vous avez lancé la commande ``creme_populate``, vous devriez retouver
votre formulaire dans la liste des formulaires configurables
(Menu > Configuration > Formulaires personnalisés), associé à votre modèle.

Il reste à faire que notre vue de création utilise effectivement notre
formulaire personnalisées ; modifions ``views/beaver.py`` : ::

    [...]

    from .. import custom_forms

    class BeaverCreation(generic.EntityCreation):
        model = Beaver
        form_class = custom_forms.BEAVER_CREATION_CFORM  # <== NEW


Maintenant votre vue de création devrait réfléter la configuration que vous
donnez à votre formulaire.

**Un peu plus loin** : il y a plusieurs moyens de faire des traitements un peu
plus spécifiques dans un formulaire personnalisé, gràce à certains attributs
de ``CustomFormDescriptor`` :

- vous pouvez exclure des champs via l'attribut ``excluded_fields``.
- vous pouvez spécifier la classe de base que le formulaire généré utilisera
  avec l'attribut ``base_form_class``. Attention la classe que vous passez
  doit hériter de la classe ``creme_core.forms.base.CremeEntityForm``, et vous
  devriez éviter de définir des champs dedans (l'intérêt est plutôt de mettre
  du code dans les méthodes ``clean()`` ou ``save()``).
- il est possible d'ajouter des champs spéciaux, ne correspondant pas
  forcément à des champs de modèle, avec l'attribut ``extra_sub_cells``.
  L'app ``products``, par exemple, s'en sert pour générer un champ qui gère les
  catégories/sous-catégories.
- il est même possible de déclarer des blocs entier de champs spéciaux (qui
  ne seront pas configurables, et seront juste présents ou absents selon la
  configuration) avec l'attribut ``extra_group_classes``. Il vaut mieux se
  servir de cette solution en dernier recours (et préférér les solutions
  précédentes). Mais si vous en avez vraiment besoin, vous pouvez regarder
  l'app ``persons`` qui s'en sert pour le bloc "Adresses".


Champs fonctions
~~~~~~~~~~~~~~~~

Ce sont des champs qui n'existent pas en base de données, et qui permettent
d'effectuer des calculs ou des requêtes afin de présenter des informations
utiles aux utilisateurs. Ils sont disponibles dans les vues en liste et les
blocs personnalisés.

Dans notre exemple, le champ fonction affichera l'âge d'un castor. Créez un
fichier ``function_fields.py`` : ::

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


L'attribut ``name`` sera utilisé comme identifiant. L'attribut ``verbose_name``
sera utilisé par exemple dans la vue de liste comme titre de colonne (comme
l'attribut homonyme des champs classiques des modèles par exemple).

**Note** : le resultat doit être du type ``FunctionFieldResult`` (ou d'une de ses
classes filles, comme ``FunctionFieldDecimal`` ou ``FunctionFieldResultsList``),
qui est la valeur par défaut de ``FunctionField.result_type`` ; ce type va
permettre de formatter correctement la valeur, selon qu'on affiche du HTML
ou qu'on exporte du CSV.

Puis dans votre ``apps.py``, ajoutez la méthode ``register_function_fields()``
telle que : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_function_fields(self, function_field_registry):  # <- NEW
            from . import function_fields

            function_field_registry.register(Beaver, function_fields.BeaverAgeField)


**Notes** : comme vous précisez le modèle associé à votre champ fonction, il est
aisé d'enrichir un modèle venu d'une autre app. Et comme les champs fonctions
sont hérités, si vous en ajoutez un à ``CremeEntity``, il sera disponible dans
tous les types d'entités.

**Un peu plus loin** : il est possible de mettre un champ de recherche dans la
colonne des vues en liste correspondant à votre ``FunctionField``. Pour cela,
il faut renseigner l'attribut de classe ``search_field_builder`` avec une classe
dérivant de ``creme.creme_core.forms.listview.ListViewSearchField``. Il s'agit
globalement d'un champ de formulaire (qui possède notamment un widget associé)
mais dont la méthode ``to_python()`` va renvoyer une instance de
``django.db.models.query_utils.Q``. Vous trouverez des exemples d'utilisation
dans les fichiers suivants :

- ``creme/creme_core/function_fields.py`` : on peut chercher les entités ayant
  une Propriété parmi une liste de Propriétés disponibles.
- ``creme/assistants/function_fields.py`` : on peut chercher les entités ayant
  une Alerte via son titre.


Recherche dans la vue de liste
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dans le paragraphe précédant, on a expliqué comment coder dans une vue en liste
une recherche relative à un champ fonction. Il est en fait possible de faire la
même chose pour tout type de colonne. Des champs de recherche sont définis par
défaut (voir ``creme/creme_core/gui/listview/search.py``), mais vous pouvez
par exemple :

- écraser les comportements existants.
- définir les comportements pour vos propres types de champs de modèles.

Vous devrez créer une classe dérivant de
``creme.creme_core.forms.listview.ListViewSearchField`` (rappel: il s'agit
d'un champ de formulaire mais qui génère une instance de
``django.db.models.query_utils.Q``). Il faut aller l'enregistrer auprès de
Creme, via la méthode ``register_search_fields()`` dans votre ``apps.py``.

**Exemple** : dans l'app ``persons``, le comportement de la recherche pour les
``ForeignKeys`` pointant vers le modèle ``Address`` a été personnalisé, afin de
chercher dans les sous-champs des instances de ``Address``.

Dans le fichier ``creme/persons/forms/listview.py`` est défini le champ de
recherche : ::

    from django.db.models.query_utils import Q

    from creme.creme_core.forms import listview

    # On dérive de la classe de base des champs de recherche de liste.
    class AddressFKField(listview.ListViewSearchField):

        # On veut un widget qui est un simple <input> de texte.
        widget = listview.TextLVSWidget

        def to_python(self, value):
            # On traite le cas d'une recherche vide.
            if not value:
                return Q()

            [...]

            # Notez l'attribut "cell" de type 'creme_core.core.entity_cell.EntityCell' ;
            # ici on s'en sert pour récupérér le nom de la 'ForeignKey'.
            fk_name = self.cell.value

            # On fabrique notre instance de Q(), que l'on renvoie enfin
            q = Q()
            for fname in address_field_names:
                q |= Q(**{f'{fk_name}__{fname}__icontains': value})

            return q


Dans le fichier ``creme/persons/apps.py``, on enregistre le champ de recherche : ::

    class PersonsConfig(CremeAppConfig):
        [...]

        def register_search_fields(self, search_field_registry):
            from django.db.models import ForeignKey

            from creme.creme_core.core.entity_cell import EntityCellRegularField

            from .forms.listview import AddressFKField

            # 'search_field_registry' est une registry aborescente ; on récupère
            # dans l'ordre :
            #  - la sous-registry des champs normaux.
            #  - la sous-registry des 'ForeignKey'.
            # Puis on déclare que notre champ de recherche est associé au
            # modèle 'Address'.
            search_field_registry[EntityCellRegularField.type_id]\
                                 .builder_4_model_field_type(ForeignKey)\
                                 .register_related_model(model=self.Address,
                                                         sfield_builder=AddressFKField,
                                                        )


Actions dans la vue de liste
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dans les vues de liste des fiches, il y a une colonne permettant de déclencher
des actions (ex: cloner une fiche). Sur chaque ligne, on trouve un menu pour
effectuer des actions relatifs à la fiche correspond à cette ligne ; et dans
l'entête de la liste se trouve un menu avec les actions opérant sur plusieurs
fiches en même temps.

Il est possible de créer ses propres actions ; elles pourront être disponibles
pour toutes les fiches (en les associant au modèle ``CremeEntity``) ou bien
à un type de fiche spécifique comme les castors.

Dans cet exemple, nous imaginons avoir une vue qui génère un code barre (sous
la forme d'une image qu'on télécharge) correspondant à un castor ; on va alors
pouvoir faire une action permettant de télécharger ce code barre depuis le menu
action d'un castor dans la vue de liste.

Créons un fichier ``actions.py`` dans notre app : ::

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


Quelques explications :

- ``id`` : doit être unique (parmi les actions), et comme d'habitude va servir
  lors de l'enregistrement de l'action pour la retrouver plus tard par le système.
- ``model`` : modèle pour lequel l'action est disponible. Ici nous avons mis notre
  modèle specifique, car cela n'a pas de sens pour les autres types de fiches.
- ``type`` : va déterminer le comportement de l'action dans l'interface ; créer
  de nouveaux type nécessite d'écrire du JavaScript (ce qui sort du périmètre de
  cet exemple simple). Ici, le type "download" est fourni de base et permet de rediriger
  vers une URL (il est donc souvent utilisé).
- ``icon`` :  nom de l'icône à utiliser à coté du ``label`` dans l'interface ;
  attention c'est bien Creme qui génère le nom du fichier final du genre
  "download_22.png".
- ``is_enabled()`` : dans le cas ou on retourne ``False``, l'entrée est désactivée.

**Notes** : la vue avec le nom "beavers__barcode" resterait à écrire évidemment,
mais ce n'est pas l'objet de cet exemple.

Reste à déclarer notre action dans notre ``apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_actions(self, actions_registry):  # <- NEW
            from . import actions

            actions_registry.register_instance_actions(
                actions.GenerateBarCodeAction,
            )


**Un peu plus loin** : pour faire une action qui s'exécute sur plusieurs fiches,
une classe d'action doit dériver de ``creme.creme_core.gui.actions.UIAction``
et s'enregistre avec ``actions_registry.register_bulk_actions``.


Modifier les apps existantes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

C'est un besoin courant de vouloir modifier le comportement des apps existantes.
Si tant d'entreprises écrivent leur propre CRM c'est bien car il est difficile
pour ce genre d'application de prendre en compte tous les besoins spécifiques
possibles.

Le fait que vous puissiez modifier directement le code de Creme est bien évidemment
un atout ; en effet, quelle que soit la modification que vous voudrez faire, elle
sera toujours possible de cette manière (alors que les mécanismes qui vont être
présentés ici auront toujours des limites).

Pourtant, si c'est possible, il vaut mieux passer par les mécanismes proposés
par Creme/Django/Python (dans cet ordre de priorité) afin de modifier le code
des apps existantes depuis votre propre code. Cela permettra de garder une
conception modulaire et de faciliter les montées de version de Creme.

Dans tous les cas, vous êtes évidemment vivement encouragé à écrire des tests
unitaires (`Tests unitaires et développement piloté par les tests`_) pour
vérifier vos nouveaux comportements (notamment lorsque vos mettez à jour la
version de Creme) ; en pratique vous pourrez copier les tests unitaires
correspondants dans vos propres fichiers de tests, et simplement modifier ces
copies selon vos besoins (plutôt que de partir de 0).


Techniques générales
********************

**Monkey patching** : cette méthode est plutôt brutale et doit être utilisée
avec prudence, voire évitée.
Gràce au dynamisme de Python, il est possible d'écraser des éléments d'un
autre module.
Par exemple, dans ``creme/creme_core/apps.py``, on trouve ce code qui modifie
la méthode ``ForeignKey.formfield()`` (définie dans Django) : ::

    [...]

    class CremeCoreConfig(CremeAppConfig):
        [...]

        @staticmethod
        def hook_fk_formfield():
            from django.db.models import ForeignKey

            from .models import CremeEntity

            from creme.creme_config.forms.fields import CreatorModelChoiceField

            # Ici on stocke la méthode originelle....
            original_fk_formfield = ForeignKey.formfield

            def new_fk_formfield(self, **kwargs):
                [...]

                defaults = {'form_class': CreatorModelChoiceField}
                defaults.update(kwargs)

                # ... qu'on appelle là.
                return original_fk_formfield(self, **defaults)

            ForeignKey.formfield = new_fk_formfield  # On écrase avec notre propre méthode.


**Variables globales & attributs de classes** : souvent le code de Creme/Django
est conçu pour être modifié facilement de l'extérieur, sans qu'une API complexe
ne soit nécessaire. Il faut juste se balader dans le code source et le comprendre.
Par exemple, dans les classes des champs de formulaire, le *widget* associé
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

            # On met les widgets de Creme en tant que widgets par défaut.
            # Ainsi, lorsqu'un formulaire est généré automatiquement
            # depuis un modèle, les widgets sont les "bons", sans aucun effort.
            forms.DateField.widget     = widgets.CalendarWidget
            forms.DateTimeField.widget = widgets.DateTimeWidget
            forms.TimeField.widget     = widgets.TimeWidget

On pourra faire pareil avec les attributs de classe des vues (celles basées sur
des classes, pas celles sous forme de fonctions évidemment).

De manière général, les comportements dans Creme sont souvent stockés
dans des dictionnaires globaux, plutôt qu'en dur dans des blocs
``if ... elif ... elif ...``. Il est alors aisé d'ajouter, supprimer
ou modifier lesdits comportements.

**AppConfig** : Django permet, dans la variable ``settings.INSTALLED_APPS``,
de spécifier la classe d'AppConfig utilisée par une app.
Imaginons que vous vouliez supprimer toutes les statistiques des activités
du bloc de statistique (voir `Bloc de statistiques`_).
Dans ``project_settings.py``, faites la modification suivante : ::

    INSTALLED_CREME_APPS = (
        [...]

        # 'creme.activities',  # est remplacé par:
        'creme.beavers.apps.BeaversActivitiesConfig',
        [...]
    )

Puis dans ``creme/beavers/apps.py``, on créé ladite classe de configuration : ::

    [...]

    from creme.activities.apps import ActivitiesConfig

    # On dérive de la classe originelle, afin de garder toutes les autres méthodes à l'identique.
    class BeaversActivitiesConfig(ActivitiesConfig):
        def register_statistics(self, statistics_registry):
            pass  # la méthode ne fait plus rien


Modifier les entrées de menu d'une autre app
********************************************

L'API du menu principal a été conçu pour pouvoir facilement modifier les
entrées depuis votre code. Tous les exemples suivant sont à faire de
préférence dans la méthode ``register_menu()`` de votre ``AppConfig``.

Avant toute chose, si vous voulez afficher dans la console la structure
du menu, afin de connaître les différents identifiants et priorités des
``Item``, faites ceci : ::

    print(str(creme_menu))


**Modifier un label** : ::

    creme_menu.get('features', 'persons-directory', 'persons-contacts').label = _('List of contacts')


**Modifier l'ordre** d'un ``Item`` (cela marche aussi si cet ``Item`` est un
``ContainerItem``) : ::

    creme_menu.get('features', 'persons-directory').change_priority(1, 'persons-contacts')


**Supprimer des entrées** : ::

    creme_menu.get('features', 'persons-directory').remove('persons-contacts', 'commercial-salesmen')


**Transférer une entrée** d'un *container* vers un autre. En fait, on combine
juste un ajout et une suppression : ::

    features = creme_menu.get('features')
    features.get('activities-main').add(features.get('persons-directory').pop('persons-contacts'))


Si vous voulez réécrire tout le code de menu d'une app, le mieux devrait être
d'écrire votre propre ``AppConfig`` (comme vu juste avant) et de ré-écrire sa
méthode ``register_menu()``.


Hooking des formulaires
***********************

Les formulaires Creme possèdent 3 méthodes qui permettent de changer leur
comportement sans avoir à modifier leur code directement, ce qui est utile pour
adapter les apps existantes de manière propre :

 - ``add_post_init_callback()``
 - ``add_post_clean_callback()``
 - ``add_post_save_callback()``

Elles prennent chacune une fonction comme seul paramètre ; comme leur nom
le suggère, ces fonctions (*callbacks*) sont respectivement appelées après les
appels à __init__(), clean() et save(). Ces *callbacks* doivent avoir un et un
seul paramètre, l'instance du formulaire.

**Notes** : avec les formulaires personnalisés et les classes de formulaire
déclarées comme des attributs de classe des vues, le *hooking* de classes de
formulaires classique est devenu beaucoup moins utile.

Le plus simple est de *hooker* les formulaires voulus depuis le ``apps.py``,
d'une de vos apps personnelles (comme *beavers*), dans la méthode
``all_apps_ready()``. Ici un exemple qui rajoute un champ dans le formulaire
de creation des utilisateurs (notez qu'il faudrait aussi *hooker* la méthode
``save()`` pour utiliser ce champ ; cet exercice est laissé au lecteur) : ::

    # -*- coding: utf-8 -*-

    [...]


    class BeaversConfig(CremeAppConfig):
        name = 'creme.beavers'
        verbose_name = _('Beavers management')
        dependencies = ['creme.creme_core']

        def all_apps_ready(self):
            super(BeaversConfig, self).all_apps_ready()

            from django.forms.fields import BooleanField

            # NB: on fait les import des autres apps ici pour éviter les
            #     problème d'ordre de chargement.
            from creme.creme_config.forms.user import UserAddForm

            def add_my_field(form):
                form.fields['loves_beavers'] = BooleanField(required=False, label=_('Loves beavers?'))

            UserAddForm.add_post_init_callback(add_my_field)

        [...]


**Note technique** : ``all_apps_ready()`` est un ajout de Creme à Django qui ne
définit que la méthode ``ready()``. Si vous avez besoin de faire des imports
qui directement ou indirectement provoque l'import de code présent dans d'autres
apps, alors utilisez plutôt ``all_apps_ready()`` ; sinon préférez ``ready()``
qui est plus classique.

**Note technique** : en raison du moment où les *callbacks* sont appelées, il
est tout à fait possible, selon le formulaire qui vous préoccupe, que vous ne
puissiez pas faire ce que vous voulez (par exemple avoir accès à un champ créé
après l'appel à la *callbacks*).


Surcharge des templates
***********************

Nous en avons déjà parlé, il est possible, depuis votre AppConfig, de modifier
l'attribut ``template_name`` des classes-vues, afin de faire utiliser à une vue
venant d'une autre app un template situé dans la vôtre. L'avantage est que votre
template pourra étendre le template remplacé ; ce qui est utile dans le cas où
le nouveau template ressemble beaucoup à celui remplacé (à condition bien sûr
que ce dernier utilise intelligemment des ``{% block %}``).

Mais si ce n'est pas possible (ou souhaité), il y a une autre façon de faire utiliser
à une autre app vos propres templates : la surcharge de template. Pour cela, il suffit
de s'appuyer sur le système de chargement des templates de Django.

Si vous regardez votre fichier ``settings.py``, vous pouvez y trouver la
variable suivante : ::

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


L'ordre des *loaders* est important ; cet ordre va faire que les templates présent
dans le répertoire ``creme/templates/`` seront chargés en priorité par rapport
aux templates présent dans les répertoires ``templates/`` que l'on trouve dans
les répertoires des apps.

Exemple : plutôt que de modifier directement le template ``creme/persons/templates/persons/view_contact.html``,
vous pouvez mettre votre version modifiée dans le fichier ``creme/templates/persons/view_contact.html``.


Surcharge de label
******************

Il est assez courant de vouloir personnaliser certains labels ; par exemple,
vouloir remplacer les occurrences de 'Société' par 'Collectivité'.

Il faut lancer la commande suivante (notez que 'organisation' est le terme
utilisé en anglais pour 'société') : ::

    > python creme/manage.py i18n_overload -l fr organisation Organisation


Il faut ensuite éditer le fichier de traduction nouvellement créé dans
``locale_overload/`` (indiqué par la commande), en modifiant les phrases en
français. Dans notre exemple, on remplacera donc 'société' par 'collectivité'.
N'oubliez pas de supprimer les lignes "#, fuzzy".
Il ne restera alors plus qu'à compiler ces nouvelles traductions comme déjà
vu auparavant. En se plaçant dans le répertoire ``locale_overload/`` : ::

    > django-admin compilemessages


Modification d'un modèle existant
*********************************

Il arrive aussi régulièrement de vouloir modifier un modèle existant, fourni de
base par Creme, par exemple ajouter des champs à Contact, ou bien en supprimer.

Dans le cas où vous voulez **ajouter des champs**, la méthode la plus simple est
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

 - Utilisation de signaux Django (``pre_save``, ``post_save`` …).
 - `Hooking des formulaires`_ (vu précédemment)


Dans le cas où vous souhaitez **cacher des champs**, rappelez vous que bon
nombre de champs sont marqués comme optionnel, et peuvent être cachés en allant
dans la configuration.

**En dernier recours**, si vous souhaitez vraiment pouvoir modifiez un modèle
existant, il reste la possibilité de le *swapper*. Il faut cependant que le
modèle soit *swappable* ; c'est le cas de toutes les classes dérivant de
``CremeEntity`` ( ``Contact``, ``Organisation``, ``Activity`` …) ainsi que
``Address``.

Dans un premier temps, considérons que vous voulez effectuez ce *swapping* en
début de projet ; c'est-à-dire que vous n'avez pas une base de données en
production utilisant le modèle de base que vous voulez modifier. En gros, vous
êtes en début de développement et savez déjà que vous voulez modifiez ce modèle.

Nous allons prendre comme exemple que vous voulez *swapper* ``tickets.Ticket``.

Tout d'abord vous devez créez une app dont le rôle sera d'étendre ``tickets`` et
que nous appellerons ``my_tickets``. Vous devrez donc faire ce que nous avons
fait pour l'app ``Beavers`` : créez un répertoire ``creme/my_tickets/``, contenant
des fichiers ``__init__.py``, ``apps.py``, ``models.py``, ``urls.py`` …
Votre app devra également être ajoutée dans les INSTALLED_CREME_APPS ; pour faire
les choses correctement, elle devra être avant ``tickets``.

Notre ``AppConfig`` va déclarer que l'on étend ``tickets`` : ::

    # -*- coding: utf-8 -*-

    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.apps import CremeAppConfig


    class MyTicketsConfig(CremeAppConfig):
        name = 'creme.my_tickets'
        verbose_name = _('Tickets')
        dependencies = ['creme.tickets']
        extended_app = 'creme.tickets'  # <= ICI !!
        credentials  = CremeAppConfig.CRED_NONE  # <= et ICI !!


Dans ``models.py``, il faut déclarer un modèle qui va se substituer à
``tickets.models.Ticket``. Le plus facile étant de dériver de
``tickets.models.AbstractTicket`` (sachant que toutes les entités utilisent un
schéma similaire). Il est important de garder ``Ticket`` comme nom de modèle,
afin d'éviter tout un tas de petits désagréments/bugs : ::

    # -*- coding: utf-8 -*-

    from django.db.models import DecimalField
    from django.utils.translation import gettext_lazy as _

    from creme.creme_core.models import CremeModel

    from creme.tickets.models import AbstractTicket


    class Ticket(AbstractTicket):
        estimated_cost = DecimalField(
            _('Estimated cost (€)'), blank=True, null=True, max_digits=10, decimal_places=2,
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

Si on jette un œil au fichier ``tickets/urls.py``, on voit que la façon de
définir les URLs est par endroit un peu différente de ce dont on a l'habitude.
Par exemple : ::

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

Ces URLs (en effet, on voit que ``re_path()`` est appelé, même si le code est
enveloppé dans d'autres appels) ne sont définies que lorsque le modèle ``Ticket``
n'est pas personnalisé.

Ces vues ne peuvent évidemment pas respecter vos règles métier ; par exemple la
vue de création peut planter si vous avez ajouté dans ``my_tickets.Ticket`` un champ à
la fois obligatoire et non éditable. Dans la mesure où vous avez choisi de
définir votre modèle personnalisé, il faut fournir nos propres URLs qui sont
sûres de fonctionner.

Dans notre cas, les vues de base devraient tout à fait suffire (les formulaires
seront assez intelligents pour utiliser les nouveaux champs éditables par
exemple), et donc nous pouvons définir ``my_tickets/urls.py`` tel que : ::

    # -*- coding: utf-8 -*-

    from django.urls import re_path

    from creme.tickets.views import ticket


    urlpatterns += [
        re_path(r'^my_tickets[/]?$',                        ticket.TicketsList.as_view(),    name='tickets__list_tickets'),
        re_path(r'^my_ticket/add[/]?$',                     ticket.TicketCreation.as_view(), name='tickets__create_ticket'),
        re_path(r'^my_ticket/edit/(?P<ticket_id>\d+)[/]?$', ticket.TicketEdition.as_view(),  name='tickets__edit_ticket'),
        re_path(r'^my_ticket/(?P<ticket_id>\d+)[/]?$',      ticket.TicketDetail.as_view(),   name='tickets__view_ticket'),
    ]

**Note** : l'important est de définir des URLs avec le même *name* (utilisé par
``reverse()``), ainsi que les mêmes arguments ("ticket_id" ici). Pour vous
éviter de faire des erreurs, Creme vérifie au lancement que toutes les URLs
*swappées* ont bien été définies ailleurs.

Dans des cas plus complexes, vous voudrez sûrement utiliser vos propres
formulaires ou templates. Il en vous reste plus qu'à définir vos propres vues
quand c'est nécessaire. Gardez à l'esprit qu'il vaut mieux copier/coller le
moins de chose possible ; les apps de base fournissent des vues sous la forme
de classes qui peuvent être facilment étendues. Par exemple, si vous voulez
définir la vue de création de ``my_tickets.Ticket`` avec votre propre
formulaire (dont l'écriture n'est pas traité ici, vous savez déjà le faire),
vous pourriez écrire quelque chose comme ça : ::

    # -*- coding: utf-8 -*-

    from creme.tickets.views.ticket import TicketCreation

    from creme.my_tickets.forms import MyTicketForm  # <= à écrire aussi !


    class TicketCreation(TicketCreation):
        form_class = MyTicketForm


**Un peu plus loin** : vous avez peut-être remarqué que dans ``settings.py`` se
trouvaient aussi des variable de la forme ``<APP>_<MODEL>_FORCE_NOT_CUSTOM``
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

**Comment swapper un modèle à posteriori ?** c'est-à-dire que vous avez une
installation en production, et vous vous apercevez que pour faire ce que vous
voulez, vous devez *swapper* un modèle (et donc c'est la version non *swappée*
qui est utilisée dans votre code/base actuellement).

Attention ! Vous devriez évidemment tester les étapes suivantes sur un duplicata
de votre base de données de production, et toujours avoir une sauvegarde de votre
base de production avant d'appliquer les modifications dessus (c'est valable de
manière générale, mais c'est d'autant plus vrai que les manipulations suivantes
sont assez sensibles).


#. Vous devez écrire (dans votre propre app évidemment), un modèle *swappant*,
   qui **doit correspondre exactement** au modèle tel qu'il est actuellement en
   base. Il suffit que votre modèle se content de dériver du modèle abstrait
   correspondant (ex: ``AbstractTicket``) **sans ajouter** de nouveaux champs
   (pour le moment bien sûr).

#. Modifier le *setting* ``<APP>_<MODEL>_MODEL`` pour pointer vers votre modèle
   comme vu précédemment.

#. Attention, c'est l'étape la plus subtile : renommez la table correspondant au
   modèle de base (dans PHPMyAdmin ou pgAdmin par exemple), en lui donnant le
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

        > python creme/manage.py migrate my_tickets --fake-initial

#. Comme nous l'avons vu, il faut gérer les vues de notre nouveau modèle.


Masquage des URLs existantes
****************************

Il se peut que vous vouliez qu'une URL existante mène vers une vue que vous
auriez vous même écrite entièrement. Comme nous l'avons vu, lorsque vous
*swappez* un modèle, vous devez préciser un certain nombre des vues qui lui
sont associées (création, vue de liste, etc…) ; mais vous pouvez être dans
un cas différent :

- vous n'avez pas *swappé* le modèle concerné, et ne voulez pas le faire
  juste pour modifier une vue.
- la vue en question n'est pas à re-définir en *swappant* un quelconque modèle.

**Remarque**: avec les vues sous forme de classes, il y a, comme vu précédemment,
divers moyens de modifier une vue existante depuis votre app, sans avoir besoin
de la réécrire totalement.

Dans la mesure où les URLs sont nommées dans les différents ``urls.py``, si votre
app est avant (comprendre: dans ``settings.INSTALLED_CREME_APPS``) l'app qui
contient l'URL que vous voulez re-router vers votre propre vue, il suffit de
déclarer une URL avec le même nom (elle devra aussi prendre les mêmes arguments).
Dans la mesure où le code de Creme récupère partout les URLs par leur nom,
votre URL sera donc donc utilisée.

Par exemple, vous voulez modifier la vue de création d'un mémo. Dans
``creme/assistants/urls.py``, on trouve le code suivant : ::

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


Dans votre app (qui doit être avant ``creme.assistants.py`` dans
``settings.INSTALLED_CREME_APPS``), vous déclarez donc l'URL suivante : ::

    urlpatterns = [
        re_path(
            r'^my_memo/add/(?P<entity_id>\d+)[/]?$',
            views.MyMemoCreation.as_view(),
            name='assistants__create_memo',
        ),

        [...]
    ]

Cela fonctionnera très bien, mais il existe un problème potentiel : l'URL
d'origine existe toujours (c'est juste que l'interface de Creme se servira de
la vôtre). Ce qui veut dire qu'on peut toujours accéder à la vue qu'on veut
masquer. On peut penser à une application externe dont le code n'aurait pas été
modifié, ou bien un utilisateur malveillant. Donc si par exemple la vue masquée
permet des actions qui devraient être interdites (votre vue fait des
vérifications supplémentaires), et ne se contente pas de proposer une ergonomie
améliorée, alors il faut aller un peu plus loin, en utilisant exactement la
même URL (et pas seulement son nom dans Creme).

Par défaut, les URLs de votre app commencent par le nom de celle-ci. Mais nous
pouvons préciser explicitement ce préfixe, pour utiliser le même que l'app
``assistants``. Comme cela va concerner l'ensemble des URLs de votre app, il va
être plus propre de faire une app minimale qui ne fera que ça. Créez donc une
app ``my_assistants`` ; dans son fichier ``my_assistants/apps.py``, nous allons
préciser le préfixe des URLs de cette manière : ::

    [...]

    class MyAssistantsConfig(CremeAppConfig):
        name = 'creme.my_assistants'

        @property
        def url_root(self):
            return 'assistants/'

        [...]


Puis dans ``my_assistants/urls.py`` : ::

    from django.urls import re_path

    from . import views

    urlpatterns = [
        # Notez que l'URL doit être la même que l'original.
        # Dans notre cas, plus de 'my_memo/', remplacé par un 'memo/' comme dans "assistants"
        re_path(r'^memo/add/(?P<entity_id>\d+)[/]?$', views.MyMemoCreation.as_view(), name='assistants__create_memo'),
    ]


Cette méthode reste fragile, puisque si l'URL masquée vient à changer lors
d'une version (majeure) ultérieure de Creme, votre vue ne la masquera plus
sans que cela ne déclenche d'erreur (les 2 URLs cohabiteront). Il faudra donc
l'utiliser avec parcimonie et faire attention lors des mises à jour.

**Cas spécifique: suppression d'une fonctionnalité** : dans certains cas vous
voudrez qu'une vue définie de base par Creme soit désactivée.
Par exemple, vous voulez que les Mémos soient uniquement créées par un Job
qui les importent depuis un ERP. Pour faire ça correctement il faut que les
vues de création de Mémos ne puissent plus être accédées.

Vous devriez en plus du masquage d'URL enlever les éventuels entrées de menu
et autres boutons qui envoient vers ces vues de création, afin de ne pas
polluer l'interface utilisateur avec des choses inutiles ; mais c'est étudié
dans d'autres parties de ce document.

Creme vous fournit une vue générique qui va renvoyer à l'utilisateur une page
d'erreur : ::

    from django.urls import re_path

    from creme.creme_core.views.generic.placeholder import ErrorView

    urlpatterns = [
        re_path(
            r'^memo/add/(?P<entity_id>\d+)[/]?$',
            ErrorView.as_view(message='Memo are only created by ERP.'),
            name='assistants__create_memo',
        ),
    ]



Plus loin avec les modèles: les Tags
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Creme permet de *tagger* les champs de modèles afin de leur rajouter de la
sémantique, et d'affiner le comportement de certains services. Pour le moment
en tout cas, il n'est pas possible de créer ses propres *tags*.

Exemple d'utilisation (avec 2 tags configurés en même temps) : ::

    [...]

    class Beaver(CremeEntity):
        [...]
        internal_data = CharField('Data', max_length=100).set_tags(viewable=False, clonable=False)


Liste des *tags* et leur utilité :

 - ``viewable``: les champs d'informations classiques (``IntegerField``,
   ``TextField``, …) sont visibles par l'utilisateur. Or, parfois on souhaite
   stocker des informations internes que les utilisateurs ne devraient pas voir.
   Il suffit de mettre ce *tag* à ``False``, et il sera caché dans toute
   l'application.
 - ``clonable``: en mettant ce *tag* à ``False``, la valeur du champ n'est pas
   copiée lorsque l'entité est clonée.
 - ``optional``: en mettant ce *tag* à ``True``, le champ peut être caché par
   l'utilisateur dans la configuration des champs. Le champ est alors enlevé
   des formulaires ; il est donc évident que le champ doit supporter de ne pas
   être rempli par les formulaires sans provoquer d'erreur ; par exemple en
   étant ``nullable`` ou avoir une valeur pour ``default``.
 - ``enumerable``: lorsqu'une ``ForeignKey`` a ce *tag* positionné à ``False``
   (la valeur par défaut étant ``True``), Creme considère que cette FK peut
   prendre une infinité de valeurs, et ces valeurs ne devraient donc jamais
   être présentées en tant que choix, dans les filtres par exemple.


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
            bulk_update_registry.register(
                Beaver,
                exclude=['my_field1','my_field2'],
            )

Vous pouvez aussi vouloir personnaliser le formulaire d'édition pour un champ
en particulier, parce qu'il est associé à des règles métiers par exemple : ::


    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_bulk_update(self, bulk_update_registry):
            from .forms.my_field import MyBulkEditForm

            bulk_update_registry.register(
                Beaver,
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
        [...]

        @staticmethod
        def get_clone_absolute_url():
            return ''


Si vous souhaitez gérer finement ce qui se passe lors d'un clonage, en plus du
*tag* ``clonable`` vu précédemment, vous pouvez surcharger les méthodes
suivantes :

 - ``_pre_save_clone(self, source)`` (à préférer)
 - ``_post_save_clone(self, source)`` (à préférer)
 - ``_post_clone(self, source)`` (à préférer)
 - ``_clone_m2m(self, source)``
 - ``_clone_object(self)``
 - ``_copy_properties(self, source)``
 - ``_copy_relations(self, source, allowed_internal=())``
 - ``clone(self)``


Import de fichiers CSV
~~~~~~~~~~~~~~~~~~~~~~

Si vous souhaitez que votre modèle d'entité puisse être importé via des
fichiers CSV/XLS, vous devez rajouter dans votre ``apps.py`` : ::

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
``register_merge_forms()`` de ``apps.py`` (cela sort du cadre de ce tutoriel).

**Notes** : si vous avez créé un modèle relié à un type d'entité fusionnable,
vous pouvez gérer plus finement ce qui ce passe lors d'une fusion grâce aux
signaux ``creme.creme_core.signals.pre_merge_related`` et
``creme.creme_core.signals.pre_replace_related``. Et si votre modèle est relié
par un OneToOneField, vous **devez** gérer la fusion, car Creme ne peut
évidemment pas gérer le cas où chacune des entités est reliée (il faut donc au
moins supprimer une des instances reliées, en récupérant ou non des
informations au passage etc…).


Valeurs de réglages
~~~~~~~~~~~~~~~~~~~

Il s'agit de proposer aux utilisateurs de rentrer des valeurs typées via une
interface de configuration (contrairement à une valeur dans ``settings.py``
que seul l'administrateur peut changer), afin que le code puisse adopter des
comportements spécifiques différents.


Réglages globaux
****************

Le modèle ``SettingValue`` permet de récupérer des valeurs globales à
l'application, c'est-à-dire valables pour tous les utilisateurs.

Dans votre fichier ``constants.py`` définissez l'identifiant de la clé de
configuration : ::

    BEAVER_KEY_ID = 'beavers-my_key'


Notez qu'il est conseillé de préfixer par le nom de l'app, afin d'éviter les
collisions avec les clés d'autres apps ; donc de garantir l'unicité. Si la clé
n'est pas unique une exception sera soulevée au lancement de l'application ;
il n'y a donc pas de risque d'avoir un comportement buggé (une clé utilisée
à la place d'une autre), mais cela obligerait à modifier le code.

Dans un fichier ``setting_keys.py`` à la racine de votre app mettez : ::

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


Réglages par utilisateur
************************

Il est question ici que chaque utilisateur puisse régler lui-même une valeur
qui lui sera propre.

Cela va beaucoup ressembler à la section précédente (les 2 APIs sont
volontairement proches par souci d'homogénéité/simplicité, et partagent
du code quand c'est possible).

Dans votre fichier ``beavers/constants.py`` définissez l'identifiant de la clé de
configuration (même remarque sur le préfixe/unicité) : ::

    BEAVER_USER_KEY_ID = 'beavers-my_user_key'


Dans le fichier ``setting_keys.py`` à la racine de l'app mettez : ::

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


On ne crée pas de valeur initiale dans notre ``populate.py``, puisque
les utilisateurs sont typiquement créés après l'installation de l'app.

Exposez la clé à Creme dans ``apps.py`` : ::

    [...]

    class BeaversConfig(CremeAppConfig):
        [...]

        def register_user_setting_keys(self, user_setting_key_registry):
            from .setting_keys import beaver_user_key

            user_setting_key_registry.register(beaver_user_key)


La valeur peut alors être configurée par chaque utilisateur dans sa
configuration personnelle (Menu > Creme > Ma configuration).

Il faut maintenant utiliser la valeur dans votre code. Notez qu'on doit
utiliser une instance de ``auth.get_user_model()`` ; dans cet exemple on
écrit une vue, et on a donc accès à ``request.user`` : ::

    [...]

    from .setting_keys import beaver_user_key

    [...]

    @login_required
    def a_view(request):
        [...]

        if request.user.settings.get(beaver_user_key, False):
            [...]


**Un peu plus loin** : lorsque vous instanciez un SettingKey/UserSettingKey,
il y a un paramètre ``hidden``, qui est par défaut à ``False``. Lorsque
ce paramètre est à ``True``, Creme ne gérera pas automatiquement l'interface
de configuration pour cette instance de clé ; ce qui permettra de faire une
interface plus adaptée, par exemple :

  - pour valider plus finement les valeurs entrées.
  - pour grouper plusieurs clés dans un même formulaire.


Bloc de statistiques
~~~~~~~~~~~~~~~~~~~~

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

Quelques explications sur les paramètres :

 - ``id`` : une chaîne de caractères unique identifiant une statistique, qui
   permet par exemple de supprimer une statistique d'une autre app depuis l'extérieur.
   Comme d'habitude, il est conseillé de préfixer par le nom de votre app pour
   garantir l'unicité.
 - ``label`` : le nom qui sera utilisé dans le bloc pour cette statistique.
 - ``func`` : une fonction sans argument qui renvoie une liste d'objets à afficher ;
   cette fonction sera appelée à chaque affichage du bloc.
   Ici c'est une liste avec un simple entier, mais elle pourrait contenir par exemple
   des ``string`` pour des valeurs plus élaborées (ex: «50 castors par km²»).
 - ``perm`` : une ``string`` de permission, pour savoir si l'utilisateur courant
   peut voir la statistique. En général la permission correspondant à l'app des
   modèles concernés fera l'affaire.
 - ``priority`` : nombre entier. Plus sa valeur est grande, plus la statistique
   est affichée en haut du bloc.


Jobs
~~~~

Le système de job permet de s'occuper de tâches :

 - qui mettent longtemps à s'exécuter, en fournissant à l'utilisateur une barre
   de progression, la possibilité de changer de page (ou de fermer le navigateur)
   sans que la tâche ne soit interrompue, ainsi que la garantie que la tâche
   soit terminée correctement même en cas de crash du serveur (panne de courant etc…).
   Ex: Creme se sert de cet aspect pour les imports CSV/XLS.
 - qui doivent être exécutées périodiquement (ou au moins à une date précise) sans
   qu'il n'y ait besoin d'un utilisateur pour les déclencher. Cela remplace
   avantageusement une commande associée à une configuration CRON, car cela ne
   nécessite pas de travail particulier pour l'administrateur (quand il
   installe/désinstalle une app par exemple).
   Ex: Creme se sert de cet aspect pour les envois de campagnes d'e-mails.

Nous allons faire le squelette d'un job qui fait une tâche quotidienne qui irait
chercher l'état de santé d'un castor, par exemple en lisant un fichier créé par
un autre logiciel ou en se connectant à un service Web (cette partie du code sera
laissée en exercice pour le lecteur de toutes les façons).

Tout d'abord nous allons créer le type de job, qui va contenir le code de notre tâche.
Pour cela notre app doit contenir un *package* ``creme_jobs`` ; si votre app doit contenir
plusieurs jobs, vous pouvez opter pour un répertoire ``beavers/creme_jobs/``.
Ici on va juste créer un simple fichier ``beavers/creme_jobs.py`` : ::


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
            # C'est ici que vous allez mettre votre code qui va récupérer les données

        def get_description(self, job):
            # Vous devez renvoyer une liste de chaînes (traduites de préférence) ;
            # elle sera utilisée dans la vue détaillée du job.
            # La liste permet de mettre des informations supplémentaires comme
            # l'URL du service utilisée dans notre cas.
            return [
                gettext('Check the health of the beavers by connecting to our health service'),
                gettext('URL is {}').format(settings.BEAVERS_HEALTH_URL),
            ]


    beavers_health_type = _BeaversHealthType()

    # Il est important que votre *package* contienne une variable "jobs" qui
    # est une liste d'instances de vos types.
    # Creme va venir chercher cette variable pour connaître les types de jobs.
    jobs = (beavers_health_type,)

**Explications** : on définit ici un type de job, qui sera utilisé par des
instances de ``creme_core.models.Job``.
Comme d'habitude, on crée un identifiant (attribut ``id``) pour notre classe
qui va servir à la retrouver depuis une *string* en base de données. Le champ
``verbose_name`` sera utilisé dans l'interface pour désigner notre job, comme
dans la liste des jobs par exemple. L'attribut ``periodic`` désigne le type de
périodicité utilisée par ce type de job ; la valeur peut être :

 - ``JobType.NOT_PERIODIC`` : les instances de ``Job`` avec cette valeur sont
   créées à la volée, puis exécutées une seule fois dès que possible par le
   gestionnaire de jobs. Par exemple, l'import de fichier CSV de Creme
   fonctionne comme ça ; chaque import génère un ``Job`` qui contient toutes
   les données nécessaires (qui ont été rentrées via le formulaire d'import).
 - ``JobType.PERIODIC`` : une seul instance de ``Job`` possédera ce type et sera
   créée dans le fichier ``populate.py`` (voir après) et ne sera supprimée
   qu'à la désinstallation de l'app correspondante. Le job est exécuté
   de manière périodique. Ex: aller consulter une boîte mail, la présence d'un
   fichier via FTP…
 - ``JobType.PSEUDO_PERIODIC`` : comme dans le cas précédent il n'y aura qu'une
   seule instance de ``Job`` ; le job est exécuté selon les données en base qui
   définissent la prochaine exécution. Par exemple si un job d'envoi d'e-mails
   doit faire un envoi dans 17 heures puis un dans 3 jours.

Comme nous avons créé un job périodique, il nous faut créer l'instance de ``Job``
dans notre ``populate.py`` : ::

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
                    # ATTENTION: nous devons définir une periode
                    'periodicity': date_period_registry.get_period('days', 1),
                    'status':      Job.STATUS_OK,
               },
            )

**Gestion des erreurs** : il est très probable que vos jobs puissent rencontrer
des soucis ; dans notre exemple le service Web distant pourrait être indisponible.
Cela peut être une bonne idée de pouvoir indiquer dans l'interface ce qui s'est passé
lors de la dernière exécution. La plupart des méthodes de ``JobType`` prennent un
paramètre ``job`` qui est l'instance de ``Job`` associée. Et vous avez de base des
modèles qui permettent de créer des résultats associés à ce job (ils sont affichés
dans le bloc d'erreurs de la vue détaillée du job). Voici un exemple : ::

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


Vous pouvez créer votre propre type d'exception et votre propre bloc d'erreur
(voir ``JobType.results_bricks``).

**Configuration du job** : un job périodique peut être configuré via un formulaire
accessible depuis la liste des jobs ; cela permet de changer la période de ce job.
Mais il est possible qu'un job propose un formulaire configuration plus poussé, via
la méthode ``JobType.get_config_form_class()`` ; les données supplémentaires
peuvent être stockées dans l'instance de ``Job``, qui possède une propriété
``data`` (attention les données doivent pouvoir être sérialisée en JSON).


Personnaliser les énumérations dans les filtres et vues de liste
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Il est possible de changer le comportement des énumérations d'instances pointées
par une ``ForeignKey`` (ou un ``ManyToManyField``), que l'on trouve dans le
formulaire de filtre (que l'on trouverait pour le champ ``Beaver.status``) et
la recherche rapide des vues en liste. Comme vu précédemment, lesdites
``ForeignKey`` devront avoir le *tag* ``enumerable`` à ``True`` pour pouvoir
renvoyer une liste de choix.

Si on souhaite juste limiter les choix possibles pour une ``ForeignKey`` précise,
on préfèrera utiliser l'attribut "limit_choices_to" sur ladite ``ForeignKey``
(puisque cela affectera automatiquement tous les formulaires du modèle en question).

Le système d'énumération de Creme va au delà ; il permet d'avoir des labels
plus adaptés ou de regrouper certains choix entre eux. Par exemple
Creme utilise ça pour personnaliser les énumération des ``ForeignKey`` pointant
le modèle ``EntityFilter`` (ce qui n'arrive actuellement que dans le modèle
``reports.Report``) ; les filtres sont regroupés selon le type de fiche auxquel
ils sont attachés.

Voici par exemple ce qu'on peut trouver dans le fichier ``creme_core/apps.py`` : ::

    def register_enumerable(self, enumerable_registry):
        from . import enumerators, models

        enumerable_registry.register_related_model(
            models.EntityFilter,
            enumerators.EntityFilterEnumerator,
        )


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
envisager de tester et déboguer votre code sans rafraîchir constamment votre
navigateur Web.

Pour notre module *beavers*, voici un exemple qui teste la vue de création.
Créez un fichier ``beavers/tests.py`` : ::

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
                    'birthday': '2015-12-3',
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
                datetime.date(year=2015, month=12, day=3),
                beaver.birthday
            )


Vous pouvez alors lancer vos tests : ::

    > python creme/manage.py test beavers

**Astuce** : travaillez avec SQLite lorsque vous écrivez le nouveau code.
Vous pouvez même, lorsque vous êtes dans une passe de TDD (c'est-à-dire que
vous ne cherchez pas à voir le résultat dans votre navigateur), vous passer de
l'écriture des migrations à chaque changement dans un modèle, avec les lignes
suivantes dans votre ``local_settings.py`` : ::

    import sys

    # ATTENTION ! Ne fonctionne qu'avec SQLite
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

Une fois votre code satisfaisant, prenez le temps de lancer les tests avec MySQL
et/ou PostgreSQL ; il vous faut pour ça commenter les lignes données au dessus
et avoir écrit les migrations.

**Astuce** : si vous êtes amené à lancer plusieurs fois les tests avec
MySQL/PostgreSQL pour corriger un test réfractaire par exemple, utilisez
l'option ``--keepdb`` de la commande ``test`` afin de grandement réduire le
temps que prend la commande (il ne faut en revanche pas modifier les modèles
entre 2 exécutions des tests).
