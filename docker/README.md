# Creme CRM Demo


## What is Creme CRM?

[Creme CRM](https://www.cremecrm.com/) is a free/open-source Customer Relationship Management (CRM) software developed by [Hybird](https://hybird.org/).

It is designed with an entities/relationships architecture, and is highly configurable, which allows adapting Creme to many workflows.

It is developed in [Python](https://www.python.org/) with the web framework [Django](https://www.djangoproject.com/).

This [Docker](https://www.docker.com/) image contains everything you need to run a local demo instance of Creme CRM, for testing purposes.

We do not provide a `latest` docker image tag. The full list of tags is available [here](https://hub.docker.com/repository/docker/cremecrm/cremecrm-demo/tags).

Please note that this is **not a production ready image**, as it would require a finer configuration.


## How to use this image

### Start a Creme CRM demo instance

Starting an instance is simple:

```commandline
docker run --detach --rm --name creme_demo --publish 8001:80 --volume creme_data:/srv/creme/data cremecrm/cremecrm-demo:2.7.0
```

This command will run a docker container in daemon mode, named `creme_demo`:
- it will bind the container's network port 80 to the local port 8001
- and create a docker volume named `creme_data`, to persist data from one run to the next.

Environment variables can be used to provide some additional configuration values.
The exhaustive list of available configuration options can be found in the Environment Variables section below.

Here is an example command setting up an instance using the French locale:

```commandline
docker run --detach --rm --name creme_demo --publish 8001:80 --volume creme_data:/srv/creme/data --env CREME_LANGUAGE_CODE=fr --env CREME_TIME_ZONE=Europe/Paris cremecrm/cremecrm-demo:2.6.0
```

The installation process can take a minute or two the first time the command runs.
Creme will soon be available at [http://localhost:8001](http://localhost:8001).  

You can then log in using the default admin user:  
username: `root`  
password: `root`


### Environment Variables

#### `CREME_DEBUG`
Run Creme in debug mode.  
Available values: `0`, `1`  
Default value: `0`.


#### `CREME_SECRET_KEY`
The Django secret key. Keep it secret!  
Default value: `'Creme-Demo-Secret-Key'`.


#### `CREME_DATABASE_ENGINE`
The database engine to use.  
Available values:
- `'django.db.backends.postgresql'`
- `'django.db.backends.mysql'`
- `'django.db.backends.sqlite3'`

Default value: `'django.db.backends.sqlite3'`.


#### `CREME_DATABASE_NAME`
Name of the database, or path to the database file if using 'sqlite3'.  
Default value: `'/srv/creme/data/cremecrm.db'`.  

It has been placed in the volume defined in the run command, for persistence.


#### `CREME_DATABASE_USER`
The database user. Not used with sqlite3.  
Default value: `''`. 


#### `CREME_DATABASE_PASSWORD`
The database user password. Not used with sqlite3.  
Default value: `''`. 


#### `CREME_DATABASE_HOST`
The database host. Not used with sqlite3.  
Default value: `''`. 


#### `CREME_DATABASE_PORT`
The database port. Not used with sqlite3.  
Default value: `''`. 


#### `CREME_TIME_ZONE`
The default timezone for this setup.  
Available values: Any timezone name from the tz database.  
Default value: `'Europe/London'`. 


#### `CREME_LANGUAGE_CODE`
The language to use for this setup.  
Available values: `'en'`, `'fr'`  
Default value: `'en'`.


#### `CREME_MEDIA_ROOT`
Path to the root directory where user media will be stored.  
Default value: `'/srv/creme/data/media/upload'`.  

It has been placed in the volume defined in the run command, for persistence.


#### `CREME_JOBMANAGER_BROKER`
DSN used to connect to a message broker, required for the jobs to work correctly.  
Default value: `'unix_socket:///srv/creme/jobs/'`.  


## License

Creme's source code is released under the GNU AFFERO GENERAL PUBLIC LICENSE version 3.  
[See details here.](https://github.com/HybirdCorp/creme_crm/blob/adca145bc382cdf8b274dce154c8f86424fa9224/LICENSE.txt)

As with all Docker images, these likely also contain other software which may be under other licenses.


## References

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
