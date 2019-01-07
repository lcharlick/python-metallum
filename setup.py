from setuptools import setup

setup(
    name='python-metallum',
    version='1.0.4',
    author='Lachlan Charlick',
    author_email='lachlan.charlick@gmail.com',
    url='https://github.com/lcharlick/python-metallum',
    license='MIT',
    description='Python API for www.metal-archives.com',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    py_modules=['metallum'],
    python_requires='>=3',
    install_requires=['requests', 'requests-cache', 'pyquery', 'python-dateutil']
)
