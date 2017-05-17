try:
    from setuptools import setup
    setuptools_available = True
except ImportError:
    from distutils.core import setup
    setuptools_available = False
import sys
import os


current_dir = os.getcwd()
sys.path.insert(0, current_dir)


requires = ['numpy>=1.5']

package_name = 'tdm_loader'
with open(os.path.join(current_dir, package_name, 'VERSION'), 'r') as fobj:
    version = fobj.read().strip()

try:
    long_description = open(os.path.join(current_dir, 'README.md'),
                            'r').read()
except:
    long_description = ''

# these files will be installed with the package
# they must also appear in MANIFEST.in
data_files = ['VERSION']

kwargs = dict(
    name = package_name,
    version = version,
    author = 'Florian Dobener and Josh Ayers (until 2016)',
    author_email = 'florian.dobener (at) schroedingerscat.org',
    maintainer = 'Florian Dobener',
    maintainer_email = 'florian.dobener@schroedingerscat.org',
    url = 'https://github.com/domna/tdm_loader',
    license = 'MIT',
    description = ('Open National Instruments TDM/TDX files as '
                   'NumPy structured arrays.'),
    long_description = long_description,
    packages = [package_name],
    package_data = {package_name:data_files},
    classifiers = ['Development Status :: 4 - Beta',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3.5',
                   'License :: OSI Approved :: MIT License',
                   'Operating System :: OS Independent',
                   'Intended Audience :: End Users/Desktop',
                   'Intended Audience :: Science/Research'])

if setuptools_available:
    kwargs.update(dict(
        install_requires = requires))

setup(**kwargs)

