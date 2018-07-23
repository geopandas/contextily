from setuptools import setup

# Dependencies.
with open('requirements.txt') as f:
    tests_require = f.readlines()
install_requires = [t.strip() for t in tests_require]

setup(name='contextily',
      version='0.99.0',
      description='Context geo-tiles in Python',
      url='https://github.com/darribas/contextily',
      author='Dani Arribas-Bel',
      author_email='daniel.arribas.bel@gmail.com',
      license='3-Clause BSD',
      packages=['contextily'],
      package_data={'': ['requirements.txt']},
      classifiers=[
            'License :: OSI Approved :: BSD License',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3 :: Only',
            'Programming Language :: Python :: Implementation :: CPython',
      ],
      python_requires='>=3.5',
      install_requires=install_requires,
      zip_safe=False)
