#!/usr/bin/env bash

python manage.py collectstatic --noinput
python manage.py migrate --noinput

exec gunicorn dosiomics.wsgi:application --workers=3 --timeout 180 --bind 0.0.0.0:80
