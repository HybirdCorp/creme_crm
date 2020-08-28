SHELL := /bin/bash
.DEFAULT_GOAL := help
MAKE_NPROCS ?= $(shell nproc)
CREME_LANGUAGE ?= fr


## Upgrade the Python requirements
.PHONY: update-requirements
update-requirements:
	pip install --upgrade -r creme/requirements-dev.txt


## Upgrade the Python requirements, run the migrations, the creme_populate and generatemedia commands
.PHONY: update
update: update-requirements
	python manage.py migrate
	python manage.py creme_populate
	python manage.py generatemedia


## Generate the media files
.PHONY: media
media:
	python manage.py generatemedia


## Run the Django test suite
.PHONY: test
test:
	python manage.py test --noinput --parallel=${MAKE_NPROCS} $(filter-out $@,$(MAKECMDGOALS))


## Run the Django test suite and generate coverage reports
.PHONY: test-cov
test-cov:
	$(eval targets := $(filter-out $@,$(MAKECMDGOALS)))

	COVERAGE_PROCESS_START=setup.cfg coverage run --source creme/ manage.py test --noinput --keepdb --parallel=${MAKE_NPROCS} ${targets}

	@if [ "$(targets)" ]; then\
		coverage combine -a;\
	else \
		coverage combine;\
	fi

	coverage report
	coverage html
	@echo "file://$(shell pwd)/artifacts/coverage_html/index.html"

## Cleanup karma coverage html output
.PHONY: karma
karma-clean:
	rm -f artifacts/karma_coverage/html/static/*.html

## Run the Javascript test suite
.PHONY: karma
karma: media karma-clean
	node_modules/.bin/karma start .karma.conf.js --browsers=FirefoxHeadless --targets=$(filter-out $@,$(MAKECMDGOALS))
	@echo "file://$(shell pwd)/artifacts/karma_coverage/html/index.html"


## Run the Javascript test suite in CI (generatemedia is supposed to be already done)
.PHONY: karma-ci
karma-ci:
	node_modules/.bin/karma start .circleci/.karma.conf.js --targets=$(filter-out $@,$(MAKECMDGOALS))


## Run the application
.PHONY: serve
serve: media
	python manage.py runserver


## Run shell
.PHONY: shell
shell:
	python manage.py shell_plus


## Run the Javascript linters
.PHONY: eslint
eslint:
	git diff --name-only origin/master creme/ | { grep '.js$$' || true; } | xargs --no-run-if-empty \
		node_modules/.bin/eslint \
			--config .eslintrc \
			--ignore-path .eslintignore \
			--format stylish \
			--quiet


## Validates the Python imports with isort
.PHONY: isort-check
isort-check:
	isort -rc creme/ --check --diff --atomic



## Sort the Python imports with isort
.PHONY: isort-fix
isort-fix:
	isort -rc creme/ --atomic


## Validates the Python code with flake8
.PHONY: flake8
flake8:
	flake8 creme


## Run all the Python linters
.PHONY: lint
lint: isort-check flake8


## Print some Django settings
.PHONY: settings
settings:
	@python manage.py print_settings INSTALLED_APPS MIDDLEWARE DATABASES LOGGING --format pprint


## Collect the messages to translate for the entire projet or the given app directories
.PHONY: gettext-collect
gettext-collect:
	$(eval appdirs := $(filter-out $@,$(MAKECMDGOALS)))

	@# TODO : This is a hack before the deployment of better gettext collection tools like pybabel
	@if [ "$(appdirs)" ]; then\
		for appdir in ${appdirs}; do (\
			pushd $${appdir} > /dev/null && \
				echo "Building messages $$(pwd)..." && \
				django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" -i "tests.py" -e "html,txt,py,xml" && \
				django-admin.py makemessages -d djangojs -l ${CREME_LANGUAGE} -i "*/js/tests/*" -e js && \
			popd > /dev/null \
		); done; \
	else \
		pushd ./creme/products && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			popd; \
		pushd ./creme/opportunities && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			popd; \
		pushd ./creme/mobile && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i tests.py && \
			popd; \
		pushd ./creme/reports && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			django-admin.py makemessages -d djangojs -l ${CREME_LANGUAGE} -i "static/reports/js/tests/*" && \
			popd; \
		pushd ./creme/creme_core && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" -i "templates/creme_core/tests/*" && \
			django-admin.py makemessages -d djangojs -l ${CREME_LANGUAGE} -i "static/creme_core/js/tests/*" && \
			popd; \
		pushd ./creme/sms && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			popd; \
		pushd ./creme/events && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i tests.py && \
			popd; \
		pushd ./creme/projects && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i tests.py && \
			django-admin.py makemessages -d djangojs -l ${CREME_LANGUAGE} -i "static/projects/js/tests/*" && \
			popd; \
		pushd ./creme/crudity && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" -e py -e html -e xml && \
			popd; \
		pushd ./creme/emails && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			django-admin.py makemessages -d djangojs -l ${CREME_LANGUAGE} -i "static/emails/js/tests/*" && \
			popd; \
		pushd ./creme/tickets && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i tests.py && \
			popd; \
		pushd ./creme/commercial && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			popd; \
		pushd ./creme && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "activities/*" -i "assistants/*" -i "billing/*" -i "commercial/*" -i "creme_config/*" -i "creme_core/*" -i "crudity/*" -i "cti/*" -i "documents/*" -i "emails/*" -i "events/*" -i "geolocation/*" -i "graphs/*" -i "mobile/*" -i "opportunities/*" -i "persons/*" -i "polls/*" -i "products/*" -i "projects/*" -i "recurrents/*" -i "reports/*" -i "sms/*" -i "static/*" -i "tickets/*" -i "vcfs/*" && \
			popd; \
		pushd ./creme/graphs && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i tests.py && \
			popd; \
		pushd ./creme/polls && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			popd; \
		pushd ./creme/assistants && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			popd; \
		pushd ./creme/activities && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			django-admin.py makemessages -d djangojs -l ${CREME_LANGUAGE} && \
			popd; \
		pushd ./creme/creme_config && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			popd; \
		pushd ./creme/vcfs && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			popd; \
		pushd ./creme/recurrents && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			popd; \
		pushd ./creme/documents && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			popd; \
		pushd ./creme/cti && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} && \
			django-admin.py makemessages -d djangojs -l ${CREME_LANGUAGE} && \
			popd; \
		pushd ./creme/persons && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			django-admin.py makemessages -d djangojs -l ${CREME_LANGUAGE} && \
			popd; \
		pushd ./creme/geolocation && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			django-admin.py makemessages -d djangojs -l ${CREME_LANGUAGE} && \
			popd; \
		pushd ./creme/billing && \
			django-admin.py makemessages -l ${CREME_LANGUAGE} -i "tests/*" && \
			django-admin.py makemessages -d djangojs -l ${CREME_LANGUAGE} && \
			popd; \
	fi

## Compile the translation files
.PHONY: gettext-compile
gettext-compile:
	django-admin.py compilemessages -l ${CREME_LANGUAGE}


## Print this message
.PHONY: help
help:
	@printf "Usage\n";

	@awk '{ \
			if ($$0 ~ /^.PHONY: [a-zA-Z\-\\_0-9]+$$/) { \
				helpCommand = substr($$0, index($$0, ":") + 2); \
				if (helpMessage) { \
					printf "\033[36m%-20s\033[0m %s\n", \
						helpCommand, helpMessage; \
					helpMessage = ""; \
				} \
			} else if ($$0 ~ /^[a-zA-Z\-\\_0-9.]+:/) { \
				helpCommand = substr($$0, 0, index($$0, ":")); \
				if (helpMessage) { \
					printf "\033[36m%-20s\033[0m %s\n", \
						helpCommand, helpMessage; \
					helpMessage = ""; \
				} \
			} else if ($$0 ~ /^##/) { \
				if (helpMessage) { \
					helpMessage = helpMessage"\n                     "substr($$0, 3); \
				} else { \
					helpMessage = substr($$0, 3); \
				} \
			} else { \
				if (helpMessage) { \
					print "\n                     "helpMessage"\n" \
				} \
				helpMessage = ""; \
			} \
		}' \
		$(MAKEFILE_LIST)
