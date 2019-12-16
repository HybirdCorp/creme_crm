import os
import re
from setuptools import setup, find_packages


with open(os.path.join(os.path.dirname(__file__), 'README')) as readme:
    README = readme.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


def find_version_from_file(*file_paths):
    path = os.path.join(*file_paths)

    with open(path, 'r', encoding='utf-8') as f:
        file_contains_version = f.read()

    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              file_contains_version, re.M)
    if version_match:
        return version_match.group(1)

    raise RuntimeError("Unable to find version string on '{}'.".format(path))


setup(
    name="creme-crm",
    version=find_version_from_file('creme', '__init__.py'),
    author="hybird.org",
    description="A CRM software using the django web framework",
    license="AGPL-3.0",
    keywords="CRM",
    url="www.cremecrm.com",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    long_description=README,
    install_requires=[
        "django>=2.2.8,<2.2.1024",
        "redis>=3.3.8,<3.3.1024",
        "Pillow>=6.2.0<6.2.1024",
        "python-dateutil>=2.8.0,<2.8.1024",
        "bleach>=3.1.0,<3.1.1024",
        "django-formtools==2.1",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Customer Service",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Natural Language :: French",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.5",
        "Topic :: Office/Business",
    ],
)
