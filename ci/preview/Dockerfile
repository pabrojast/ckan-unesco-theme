ARG BASE_IMAGE
FROM ${BASE_IMAGE}
USER root
ARG THEME_SHA
RUN test -n "$THEME_SHA" && rm -rf /app/src/ckanext-theme-ejemplo
COPY ckanext /app/src/ckanext-theme-ejemplo/ckanext
COPY setup.py setup.cfg README.md MANIFEST.in /app/src/ckanext-theme-ejemplo/
RUN pip install --no-deps --no-build-isolation -e /app/src/ckanext-theme-ejemplo \
    && cd /app/src/ckanext-theme-ejemplo && python setup.py compile_catalog \
    && python -m compileall -q ckanext/theme_ejemplo \
    && printf '%s\n' "$THEME_SHA" > /app/preview-theme-sha \
    && chown -R ckan:ckan /app/src/ckanext-theme-ejemplo /app/preview-theme-sha
COPY --chown=ckan:ckan ci/preview/wsgi.py /app/preview-wsgi.py
RUN sed -i 's@wsgi-file = /app/wsgi.py@wsgi-file = /app/preview-wsgi.py@' /app/preview-uwsgi.ini
RUN sed -i '/^beaker.session.cookie_domain[[:space:]]*=[[:space:]]*$/d' /app/production.ini /srv/app/production.ini
LABEL org.opencontainers.image.source="https://github.com/pabrojast/ckan-unesco-theme" \
      org.opencontainers.image.revision="${THEME_SHA}" \
      org.opencontainers.image.theme.revision="${THEME_SHA}"
USER ckan
