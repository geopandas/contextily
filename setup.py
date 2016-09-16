from setuptools import setup

setup(name='contextily',
        version='0.9.0',
      description='Context geo-tiles in Python',
      url='https://github.com/darribas/contextily',
      author='Dani Arribas-Bel',
      author_email='daniel.arribas.bel@gmail.com',
      license='3-Clause BSD',
      packages=['contextily'],
      install_requires=['cartopy', 'pandas', 'PIL', 
          'rasterio', 'six', 'mercantile'],
      package_data={'cenpy': ['stfipstable.csv']},
      zip_safe=False)
