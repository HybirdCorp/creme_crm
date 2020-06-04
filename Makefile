MAKE_NPROCS ?= $(shell nproc)

update-requirements:
	pip install --upgrade -r creme/requirements-dev.txt

update: update-requirements
	python manage.py migrate
	python manage.py creme_populate
	python manage.py generatemedia

media:
	python manage.py generatemedia

test:
	manage.py test --noinput --parallel=${MAKE_NPROCS} $(filter-out $@,$(MAKECMDGOALS))
%:
	@:

test-cov:
	COVERAGE_PROCESS_START=.coveragerc coverage run --source creme/ manage.py test --noinput --parallel=${MAKE_NPROCS} $(filter-out $@,$(MAKECMDGOALS))
	coverage combine
	coverage report
	coverage html
%:
	@:

karma: media
	node_modules/.bin/karma start .karma.conf.js --browsers=FirefoxHeadless --targets=$(filter-out $@,$(MAKECMDGOALS))
%:
	@:

serve: media
	python manage.py runserver

eslint:
	git diff --name-only origin/master creme/ | { grep '.js$$' || true; } | xargs --no-run-if-empty \
		node_modules/.bin/eslint \
			--config .eslintrc \
			--ignore-path .eslintignore \
			--format stylish \
			--quiet

isort:
	git diff --name-only origin/master creme/ | { grep '.py$$' || true; } | xargs --no-run-if-empty \
		isort --check --diff --atomic

gettext-collect:
	@for appdir in $(shell find creme/ -maxdepth 1 -type d|grep -E 'creme/[^_]+'); do (\
		cd $${appdir} && \
		pwd && \
		django-admin.py makemessages -l fr -i "tests/*" \
	); done

gettext-compile:
	@for appdir in $(shell find creme/ -maxdepth 1 -type d|grep -E 'creme/[^_]+'); do (\
		cd $${appdir} && \
		pwd && \
		django-admin.py compilemessages -l fr
	); done
