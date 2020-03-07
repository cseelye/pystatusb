from setuptools import setup
import os

# https://packaging.python.org/tutorials/packaging-projects/

NAME = "pystatusb"
setup(
    name = NAME,
    version = "__VERSION__",
    author = "Carl Seelye",
    author_email = "cseelye@gmail.com",
    description = "Control fit-statUSB devices",
    license = "MIT",
    keywords = "compulab statusb",
    packages = [NAME],
    url = "https://github.com/cseelye/{}".format(NAME),
    include_package_data=True,
    long_description = open(os.path.join(os.path.dirname(__file__), "README.md")).read(),
    long_description_content_type='text/markdown',
    install_requires = open(os.path.join(os.path.dirname(__file__), "requirements.txt")).readlines()
)
