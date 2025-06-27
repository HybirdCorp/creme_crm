Creme is a free/open-source Customer Relationship Management software developed by Hybird (www.hybird.org).

It is designed with an entities/relationships architecture, and is highly configurable, which allows
adapting Creme to many workflows.

![Detailed view of a contact](https://github.com/HybirdCorp/creme_crm/raw/main/screenshot.png)

It provides apps (i.e. modules) to manage:
 - Contacts & organisations.
 - Documents & folders.
 - Activities (meetings, phone calls, tasks...) with a calendar.
 - Products & services.
 - Invoices, quotes, sales orders & credit notes.
 - Opportunities.
 - Commercial actions.
 - Email campaigns.
 - Reports.
 - Tickets.
 - Alerts, todos & memos.
 - Geolocation.
 - ...

Lots of aspects can be configured through a graphical interface :
 - Detailed views for entities are built from blocks; you can configure which blocks are
   displayed, you can create your own the blocks (chose the fields which are used)...
 - You can configure the columns of the list views (columns can be related to fields, custom-fields,
   relationships...), and filter the lines with powerful rules.
 - You can create your custom-fields, or hide existing fields.
 - You can choose which fields of forms are used, and group them like you want.
 - You can create your own types of relationship, adapted to your business.
 - ...

Creme has powerful tools to filter, search or import data. it provides a credential system with
some cool features (teams, allow/forbid entities from a filter on fields/relationships, ...).

If you have very specific needs, Creme can also be used as a CRM framework to code your own CRM.

Creme is coded in Python, and uses the Django web framework (http://www.djangoproject.com/) and
the JQuery javascript library (http://jquery.com/).

You can find more information on Creme on its official website: http://cremecrm.com/
You can ask your questions in our forum: https://www.cremecrm.com/forum/index.php
(there is an english section)

### Current translations

 - English (could probably be improved)
 - French


### Recommendations:

It's recommended to use a database engine which supports transactions :
 - PostGreSQL is probably the best choice for databases with 100,000+ entities.
 - SQLite support is principally done for developers, but it remains a solution
   for small databases (e.g. a use as mono-user app with the server running of your computer).

You probably should use 'virtualenv' (for an upgrade from Creme 2.4, you should create a new
virtual env, in order to keep the old one working).


### Dependencies

 - Python 3.10+
 - MySQL 8.0.11+ (or MariaDB 10.5+ but we do not advise you to use MariaDB because it regularly causes strange issues)
   or PostGreSQL 14+
   or SQLite (which is included with Python)
 - A web server compatible with Python, like Apache 2.4
 - Redis 3+
 - These Python packages :
   (exact versions of Python packages are indicated in the 'setup.cfg' file)
   - Mandatory :
     - Django
     - redis
     - python-dateutil
     - cryptography
     - bleach
     - Pillow
     - django-formtools
     - xlrd (to import contacts, organisations, activities, tickets... from xls files)
     - xlwt (to export all types of entities -- like contacts or organisations -- as xls files)
     - openpyxl (to import & export as above but with xlsx files)
     - csscompressor
     - rJSmin
   - Optional :
     - creme.billing :
       If you want PDF export, you can use :
       - xhtml2pdf (default)
       - weasyprint (easy to install on Linux; harder on Windows)
       - you can also use the binary "latexmk" with "lualatex";
         For example on Ubuntu you'll need these packages:
         - minimum: latexmk texlive-latex-base
         - for french templates: texlive-latex-recommended texlive-latex-extra texlive-fonts-extra texlive-lang-french

Installation with 'pip':
 - You should probably use "virtualenv".
 - To install Creme itself :
   - You can just install from pyPI: 'pip install creme-crm==2.X'
   - If you retrieved the source, you can use the following command at the source's root: 'pip install -e .'
 - About DB server :
   - If you use MySQL/MariaDB, you must add the 'mysql' flag :
     'pip install creme-crm[mysql]==2.X' (or 'pip install -e .[mysql]' with the source).
   - For PostGreSQL,  you must add the 'pgsql' flag :
     'pip install creme-crm[pgsql]==2.X' (or 'pip install -e .[pgsql]' with the source).
   - SQLite doesn't require a specific flag (see RECOMMENDATIONS).
 - Notice some of these Python packages need system libraries to be installed.
   For example, here a list of Debian/Ubuntu packages you'll have to install before:
   - python-dev
   - mysql_config & libmysqlclient-dev (or libpq-dev if you want to use PostGreSQL)
   - redis-server
   - libjpeg-dev
   - libcairo-dev


### Install

Global remarks:
 - You should know how to install/deploy a Django application.
 - Upgrade note: if you already have a Creme installation, upgrade the version one by one
   (e.g. do not try to upgrade from 2.0 to 2.2, upgrade to 2.1 and then 2.2).

Database configuration:
For a new installation, you have to create a new database & a new DB user
(who is allowed to create/drop tables, indices...).
For an upgrade from the previous major version, back up your existing DB
(of course you should back up regularly, even when you do not upgrade Creme...).

Project creation:
For new installations AND for upgrades from a previous version, create a new project;
with the virtualenv activated, use the following command which creates a new folder:
```sh
>> creme creme_start_project my_project
```

Settings:
The newly created file "my_project/my_project/settings.py" gives all the information
for a basic installation with the minimal information you must fill.

For an upgrade from the previous version of Creme :
 - See the section "UPGRADE NOTE" corresponding to the new version in the file CHANGELOG.txt.
 - Do not remove apps in INSTALLED_APPS during the upgrade (because they are installed in your DB) ;
   complete your installation & then uninstall apps you do not want anymore (see below).


Filling the DB tables & creating the static asset:
You must be in the parent folder "my_project/" (i.e. not "my_project/my_project/").
Run the following commands (new installations AND upgrades from a previous version):
```sh
>> creme migrate --settings=my_project.settings
>> creme creme_populate --settings=my_project.settings
>> creme generatemedia --settings=my_project.settings
```

Note for MySQL users: you should load the time zone tables.
 - On Unix servers, it can be done with:
   ```sh
   >> mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root -p mysql
   ```
 - For Windows environment, see https://stackoverflow.com/questions/14454304/convert-tz-returns-null

Note for MariaDB users:
If you have an existing instance of Creme & you upgrade your MariaDB server to 10.7+,
you have to convert all the UUID fields (which were just CharFields before MariaDB 10.7)
to real UUID fields.
TO BE COMPLETED.

### Launch

To run the development server, you just have to run this command:
```sh
>> creme runserver --settings=my_project.settings
```
You can then go to http://localhost:8000 & log in with root/root.

For a production deployment (Apache, Nginx...), you should read https://docs.djangoproject.com/en/5.2/howto/deployment/

In order to get a completely functional instance, the job manager must be launched
(some features need it: sending emails campaign, CSV import...).
To run it, use this command (in a production environment a watch dog is advised):
```sh
>> creme creme_job_manager --settings=my_project.settings
```


### Uninstall apps

When you have a working installation, & want to remove an (optional) app, use the command 'creme_uninstall' which will
clean the DB. When it's done, you can comment the app in local_settings.py


### Contributing

The repository is using CircleCI and launch some linting tests. To check them locally before any commit or push you can
use the hooks in '.githooks'. There are two ways to configure them:

Simply change git configuration
```sh
>> git config core.hooksPath .githooks
```

Or create symlink in '.git/hooks/'. Make sure the old one are moved or removed.
```sh
>> ln -s ../../.githooks/pre-commit .git/hooks/pre-commit
>> ln -s ../../.githooks/pre-push .git/hooks/pre-push
```

In order to run the JavaScript linter locally, you can install a NodeJS environment within your virtualenv thanks to the
Python package nodeenv. In your virtualenv (named "mycremeenv"):
```sh
>> pip install nodeenv
>> nodeenv -n 14.20.0 -p    # to install nodejs 14.20.0 with "mycremeenv"
>> deactivate
>> workon mycremeenv
>> nodejs --version  # to check the installation is OK
>> make node-update  # Install nodejs requirements
```

Now you can run "make eslint" manually, and the pre-commit hook will check the new/modified files.

### References

Creme CRM source code is available on the [Creme CRM GitHub Repository](https://github.com/HybirdCorp/creme_crm).

Want to know more about Creme CRM ?
Check out the [Creme CRM Website](https://www.cremecrm.com).

Want to try Creme CRM ?
Visit the [Creme CRM Public Demo Website](https://demos.cremecrm.com/).

Want your own demo instance ?
Pull the latest Creme CRM Demo Docker image on the [Creme CRM DockerHub Repository](https://hub.docker.com/r/cremecrm/cremecrm-demo).

Want to know more about our company ?
Check out the [Hybird Website](https://hybird.org/).

Any other questions ?
Need help ?
Reach us on the [Creme CRM Forums](https://www.cremecrm.com/forum/).
Our (french) [Video tutorials](https://www.youtube.com/channel/UCqt-dsKnW7sNwlCWOODTDWQ).
