##------------------------------------------------------------------------------
## Database settings
##------------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE'    : 'django.db.backends.postgresql_psycopg2',
        'NAME'      : 'samu_20120125_fbcanvas',
        'USER'      : 'samu_devel',
        'PASSWORD'  : 'pass',
        'HOST'      : 'localhost',
        'PORT'      : '5432',
    }
}


##------------------------------------------------------------------------------
## Settings for django_facebook
##------------------------------------------------------------------------------
FACEBOOK_APP_ID = "216551815105670"
FACEBOOK_APP_SECRET = "8ec14f75d395663d6da9fcf147e90a9f"
FACEBOOK_CANVAS_URL = "https://apps.facebook.com/django-fbcanvas/"
FACEBOOK_FORCE_CANVAS = True
ACCOUNT_ACTIVATION_DAYS = 10
