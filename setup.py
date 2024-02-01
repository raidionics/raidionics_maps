from setuptools import find_packages, setup
import platform
import sys

with open("README.md", "r", errors='ignore') as f:
    long_description = f.read()

with open('requirements.txt', 'r', encoding='utf-16', errors='ignore') as ff:
    required = ff.read().splitlines()

if platform.system() == 'Darwin' and platform.processor() == 'arm':   # Specific for Apple M1 chips
    required.append('scikit-learn')
    required.append('statsmodels')
else:
    required.append('antspyx==0.3.8')

setup(
    name='raidionicsmaps',
    packages=find_packages(
        include=[
            'raidionicsmaps',
            'raidionicsmaps.Computation',
            'raidionicsmaps.Structures',
            'raidionicsmaps.Utils',
            'raidionicsmaps.Atlases',
            'tests',
        ]
    ),
    entry_points={
        'console_scripts': [
            'raidionicsmaps = raidionicsmaps.__main__:main'
        ]
    },
    install_requires=required,
    include_package_data=True,
    python_requires=">=3.8",
    version='1.0.0',
    author='David Bouget (david.bouget@sintef.no)',
    license='BSD 2-Clause',
    description='Raidionics backend for the generation of population-based location maps',
    long_description=long_description,
    long_description_content_type="text/markdown",
)
