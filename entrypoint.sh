#!/usr/bin/env bash

python manage.py collectstatic --noinput
python manage.py migrate --noinput

gunicorn dosiomics.wsgi --workers=3 --timeout 180 -b 0.0.0.0:80
