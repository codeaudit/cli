from setuptools import setup, find_packages

setup(name='riseml',
      version='0.0.1',
      description='RiseML client',
      author='RiseML',
      author_email='admin@riseml.com',
      packages=find_packages(),
      install_requires=[
          'pyyaml',
          'requests',
      ],
      zip_safe=False)
