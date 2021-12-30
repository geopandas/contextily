FROM darribas/gds_py:4.1

# Install contextily main
RUN pip install -U earthengine-api git+https://github.com/geopandas/contextily.git@main
# Add notebooks
RUN rm -R work/
COPY ./README.md ${HOME}/README.md
COPY ./notebooks ${HOME}/notebooks
# Fix permissions
USER root
RUN chown -R ${NB_UID} ${HOME}
USER ${NB_USER}
