#!/bin/bash

cd "$( dirname "$0" )"
python manage.py runserver django-fbcanvas.local:8000
