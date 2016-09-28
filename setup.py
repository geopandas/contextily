from setuptools import setup

# Dependencies.
with open('requirements.txt') as f:
    tests_require = f.readlines()
install_requires = [t.strip() for t in tests_require]

setup(name='contextily',
      version='0.9.0',
      description='Context geo-tiles in Python',
      url='https://github.com/darribas/contextily',
      author='Dani Arribas-Bel',
      author_email='daniel.arribas.bel@gmail.com',
      license='3-Clause BSD',
      packages=['contextily'],
      install_requires=install_requires,
      package_data={'cenpy': ['stfipstable.csv']},
      zip_safe=False)
