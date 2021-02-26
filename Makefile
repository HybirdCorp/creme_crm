SHELL := /bin/bash
.DEFAULT_GOAL := help
MAKE_NPROCS ?= $(shell nproc)
CREME_LANGUAGE ?= fr


## clean - Basic cleanup, mostly temporary files.
.PHONY: clean
clean:
	find . -name '*.pyc' -delete
	find . -name '*.pyo' -delete
	find . -name '__pycache__' -delete
	rm -rf *.egg
	rm -rf ./build
	rm -rf ./package
	rm -rf ./dist
	rm -rf ./package
	rm -rf ./.coverage
	rm -rf ./htmlcov
	rm -rf ./.pytest_cache
	rm -rf ./.hypothesis
	rm -rf ./artifacts
	find . -type d -empty -print -delete


## Upgrade the Python requirements
.PHONY: update-requirements
update-requirements:
	pip install --upgrade -e .[dev]


## Upgrade the Python requirements, run the migrations, the creme_populate and generatemedia commands
.PHONY: update
update: update-requirements
	python creme/manage.py migrate
	python creme/manage.py creme_populate
	python creme/manage.py generatemedia


## Install or upgrade nodejs requirements
.PHONY: node-update
node-update:
	npm install --no-save


## Generate the media files
.PHONY: media
media:
	python creme/manage.py generatemedia


## Run the Django test suite
.PHONY: test
test:
	python creme/manage.py test --keepdb --noinput --parallel=${MAKE_NPROCS} $(filter-out $@,$(MAKECMDGOALS))


## Run the Django test suite and generate coverage reports
.PHONY: test-cov
test-cov:
	$(eval targets := $(filter-out $@,$(MAKECMDGOALS)))

	COVERAGE_PROCESS_START=setup.cfg coverage run --source creme/ creme/manage.py test --noinput --keepdb --parallel=${MAKE_NPROCS} ${targets}

	@if [ "$(targets)" ]; then\
		coverage combine -a;\
	else \
		coverage combine;\
	fi

	coverage report
	coverage html
	@echo "file://$(shell pwd)/artifacts/coverage_html/index.html"

## Cleanup karma coverage html output
.PHONY: karma-clean
karma-clean:
	rm -f artifacts/karma_coverage/html/static/*.html
	rm -f artifacts/karma_coverage/html/*.html

## Run the Javascript test suite
.PHONY: karma
karma: media karma-clean
	node_modules/.bin/karma start .karma.conf.js --browsers=FirefoxHeadless --targets=$(filter-out $@,$(MAKECMDGOALS))
	@echo "file://$(shell pwd)/artifacts/karma_coverage/html/index.html"

karma-browsers: media karma-clean
	CHROME_BIN=/usr/bin/google-chrome \
		node_modules/.bin/karma start .karma.conf.js \
			--browsers=FirefoxHeadless,ChromiumHeadless,ChromeHeadless \
			--concurrency 3\
			--targets=$(filter-out $@,$(MAKECMDGOALS))

	@echo "file://$(shell pwd)/artifacts/karma_coverage/html/index.html"

## Run the Javascript test suite in CI (generatemedia is supposed to be already done)
.PHONY: karma-ci
karma-ci:
	node_modules/.bin/karma start .circleci/.karma.conf.js --targets=$(filter-out $@,$(MAKECMDGOALS))


## Run the application
.PHONY: serve
serve: media
	python creme/manage.py runserver


## Run shell
.PHONY: shell
shell:
	python creme/manage.py shell_plus


## Run the Javascript linters
.PHONY: eslint-diff
eslint-diff:
	git diff --name-only --diff-filter=MARC origin/main creme/ | { grep -E '.js$$' || true; } | xargs --no-run-if-empty \
		node_modules/.bin/eslint \
			--config .eslintrc \
			--ignore-path .eslintignore \
			--format stylish \
			--quiet

	git diff --name-only --diff-filter=MARC origin/main creme/ | { grep -E '.html$$' || true; } | xargs --no-run-if-empty \
		node_modules/.bin/eslint \
			--config .eslintrc \
			--ignore-path .eslintignore \
			--plugin template \
			--rule 'template/no-template-branch: 2' \
			--global '____' \
			--format stylish \
			--quiet


.PHONY: eslint
eslint:
	$(eval targets := $(or $(filter-out $@,$(MAKECMDGOALS)),creme/))

	find ${targets} -iname *.js | xargs --no-run-if-empty \
		node_modules/.bin/eslint \
			--config .eslintrc \
			--ignore-path .eslintignore \
			--format stylish \
			--quiet

	find ${targets} -iname *.html | xargs --no-run-if-empty \
		node_modules/.bin/eslint \
			--config .eslintrc \
			--ignore-path .eslintignore \
			--plugin template \
			--rule 'template/no-template-branch: 2' \
			--global '____' \
			--format stylish \
			--quiet


## Validates the Python imports with isort
.PHONY: isort-check
isort-check:
	isort creme/ --check --diff --atomic


## Sort the Python imports with isort
.PHONY: isort-fix
isort-fix:
	isort creme/ --atomic


## Validates the Python code with flake8
.PHONY: flake8
flake8:
	flake8 creme


## Run all the Python linter checks
.PHONY: lint
lint: isort-check flake8


## Run all the Python linter fixes
.PHONY: format
format: isort-fix


## Print some Django settings
.PHONY: settings
settings:
	@python creme/manage.py print_settings INSTALLED_APPS MIDDLEWARE DATABASES LOGGING --format pprint


## Collect the messages to translate for the entire project or the given app directories
.PHONY: gettext-collect
gettext-collect:
	$(eval appdirs := $(filter-out $@,$(MAKECMDGOALS)))

	@# TODO : This is a hack before the deployment of better gettext collection tools like pybabel
	@if [ "$(appdirs)" ]; then\
		for appdir in ${appdirs}; do (\
			pushd $${appdir} > /dev/null && \
				echo "Building messages $$(pwd)..." && \
				django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" -i "tests.py" -e "html,txt,py,xml" --no-location && \
				django-admin makemessages -d djangojs -l ${CREME_LANGUAGE} -i "*/js/tests/*" -e js --no-location && \
			popd > /dev/null \
		); done; \
	else \
		pushd ./creme/products && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			popd; \
		pushd ./creme/opportunities && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			popd; \
		pushd ./creme/mobile && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			popd; \
		pushd ./creme/reports && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*"  --no-location && \
			django-admin makemessages -d djangojs -l ${CREME_LANGUAGE} -i "static/reports/js/tests/*" --no-location && \
			popd; \
		pushd ./creme/creme_core && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" -i "templates/creme_core/tests/*" --no-location && \
			django-admin makemessages -d djangojs -l ${CREME_LANGUAGE} -i "static/creme_core/js/tests/*" --no-location && \
			popd; \
		pushd ./creme/sms && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			popd; \
		pushd ./creme/events && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i tests.py --no-location && \
			popd; \
		pushd ./creme/projects && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i tests.py --no-location && \
			django-admin makemessages -d djangojs -l ${CREME_LANGUAGE} -i "static/projects/js/tests/*" --no-location && \
			popd; \
		pushd ./creme/crudity && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" -e py -e html -e xml --no-location && \
			popd; \
		pushd ./creme/emails && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			django-admin makemessages -d djangojs -l ${CREME_LANGUAGE} -i "static/emails/js/tests/*" --no-location && \
			popd; \
		pushd ./creme/tickets && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i tests.py --no-location && \
			popd; \
		pushd ./creme/commercial && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			popd; \
		pushd ./creme && \
			django-admin makemessages -l ${CREME_LANGUAGE} --no-location -i "activities/*" -i "assistants/*" -i "billing/*" -i "commercial/*" -i "creme_config/*" -i "creme_core/*" -i "crudity/*" -i "cti/*" -i "documents/*" -i "emails/*" -i "events/*" -i "geolocation/*" -i "graphs/*" -i "mobile/*" -i "opportunities/*" -i "persons/*" -i "polls/*" -i "products/*" -i "projects/*" -i "recurrents/*" -i "reports/*" -i "sms/*" -i "static/*" -i "tickets/*" -i "vcfs/*" && \
			popd; \
		pushd ./creme/graphs && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i tests.py --no-location && \
			popd; \
		pushd ./creme/polls && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			popd; \
		pushd ./creme/assistants && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			popd; \
		pushd ./creme/activities && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			django-admin makemessages -d djangojs -l ${CREME_LANGUAGE} -i "static/activities/js/tests/*" --no-location && \
			popd; \
		pushd ./creme/creme_config && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			popd; \
		pushd ./creme/vcfs && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			popd; \
		pushd ./creme/recurrents && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			popd; \
		pushd ./creme/documents && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			popd; \
		pushd ./creme/cti && \
			django-admin makemessages -l ${CREME_LANGUAGE}  -i "tests.py" --no-location && \
			django-admin makemessages -d djangojs -l ${CREME_LANGUAGE} -i "static/cti/js/tests/*" --no-location && \
			popd; \
		pushd ./creme/persons && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			django-admin makemessages -d djangojs -l ${CREME_LANGUAGE}  -i "static/persons/js/tests/*" --no-location && \
			popd; \
		pushd ./creme/geolocation && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			django-admin makemessages -d djangojs -l ${CREME_LANGUAGE}  -i "static/geolocation/js/tests/*" --no-location && \
			popd; \
		pushd ./creme/billing && \
			django-admin makemessages -l ${CREME_LANGUAGE} -i "tests/*" --no-location && \
			django-admin makemessages -d djangojs -l ${CREME_LANGUAGE} --no-location && \
			popd; \
	fi

## Compile the translation files
.PHONY: gettext-compile
gettext-compile:
	django-admin compilemessages -l ${CREME_LANGUAGE}


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
