from distutils.core import setup

setup(
    name='metallum',
    version='1.0',
    author='Lachlan Charlick',
    author_email='lachlan.charlick@gmail.com',
    url='https://github.com/lcharlick/python-metallum',
    license='LICENSE.md',
    description='Python API for www.metal-archives.com',
    long_description=open('README.txt').read(),
    py_modules=['metallum'],
    python_requires='>=3',
    install_requires=['requests', 'requests-cache', 'pyquery', 'python-dateutil']
)
