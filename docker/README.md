# Creme CRM Demo


## What is Creme CRM?

[Creme CRM](https://www.cremecrm.com/) is a free Customer Relationship Management (CRM) software developed by [Hybird](https://hybird.org/).

It is developed in [Python](https://www.python.org/) with the web framework [Django](https://www.djangoproject.com/).

This [Docker](https://www.docker.com/) image contains everything you need to run a local demo instance of Creme CRM, for testing purpose.


## How to use this image

### Start a Creme CRM demo instance

Starting an instance is simple:

```commandline
docker run --detach --rm --name creme_demo --publish 8001:80 --volume creme_data:/srv/creme/data --env CREME_LANGUAGE_CODE=en cremecrm/cremecrm-demo:latest
```
This command will run a docker container daemon mode, named `creme_demo`.  
It will bind the container network port 80 to the local port 8001.  
It will create a docker named volume `creme_data`, that will allow us to persist data from on run to the next.
We configure the setup in english by providing an environment variable `CREME_LANGUAGE_CODE=en` to the command.
The exhaustive list of the available configuration is in the Environment Variables section.

The Creme installation process takes a bit of time the first time (1-2 minutes).
Creme will soon be available at [http://localhost:8001](http://localhost:8001).  
You can log in using the first admin user:  
username: `root`  
password: `root`


### Environment Variables

#### `CREME_DEBUG`
Run Creme in debug mode.  
Available values: `0`, `1`  
Default value: 0.

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
Default value: `'Europe/Paris'`. 


#### `CREME_LANGUAGE_CODE`
The language to use for this setup.  
Available values: `'en'`, `'fr'`  
- `'django.db.backends.sqlite3'`

Default value: `'fr'`.

#### `CREME_MEDIA_ROOT`
Path to the root directory where user media will be stored.
Default value: `'/srv/creme/data/media/upload'`.  
It has been placed in the volume defined in the run command, for persistence.

#### `CREME_JOBMANAGER_BROKER`
DSN used to connect to a message broker, required for the jobs to work correctly.
Default value: `'unix_socket:///srv/creme/jobs/'`.  


## License

Creme source code is released under the GNU AFFERO GENERAL PUBLIC LICENSE version 3.  
[See the details here.](https://github.com/HybirdCorp/creme_crm/blob/adca145bc382cdf8b274dce154c8f86424fa9224/LICENSE.txt)

As with all Docker images, these likely also contain other software which may be under other licenses.


## References

Creme CRM source code is available on GitHub: [https://github.com/HybirdCorp/creme_crm](https://github.com/HybirdCorp/creme_crm)

Want to know more about Creme CRM ? Check out [Creme CRM website](https://www.cremecrm.com)

Want to know more about our company? Check out [Hybird website](https://hybird.org/)

Any other question? Need help? Reach us on the [Creme CRM Forums](https://www.cremecrm.com/forum/)
