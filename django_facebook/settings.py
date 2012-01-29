from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

## Default settings ------------------------------------------------------------

## Facebook application data.
## These settings are REQUIRED and MUST be configured by your app.
FACEBOOK_APP_ID = getattr(settings, 'FACEBOOK_APP_ID', None)
FACEBOOK_APP_SECRET = getattr(settings, 'FACEBOOK_APP_SECRET', None)

## Default permissions that will be asked to the user.
FACEBOOK_DEFAULT_SCOPE = getattr(settings, 'FACEBOOK_DEFAULT_SCOPE', ['email', 'user_about_me', 'user_birthday'])

## Absoluter URL of the Facebook canvas page.
## Usage of https URL is recommended.
FACEBOOK_CANVAS_PAGE = getattr(settings, 'FACEBOOK_CANVAS_PAGE', None)

## How to handle canvas.
## If set to None, no action is taken.
## If set to 'force', canvas is forced, by redirecting from stand-alone
## page to canvas page (requires FACEBOOK_CANVAS_PAGE to be set)
## If set to 'escape', the page will jump out of frames.
FACEBOOK_CANVAS_HANDLING = getattr(settings, 'FACEBOOK_CANVAS_HANDLING', None) or None

## These you don't need to change
FACEBOOK_HIDE_CONNECT_TEST = getattr(settings, 'FACEBOOK_HIDE_CONNECT_TEST', True)

## Track all raw data coming in from FB
FACEBOOK_TRACK_RAW_DATA = getattr(settings, 'FACEBOOK_TRACK_RAW_DATA', False)

## Whether to store all the user likes|friends
FACEBOOK_STORE_LIKES = getattr(settings, 'FACEBOOK_STORE_LIKES', False)
FACEBOOK_STORE_FRIENDS = getattr(settings, 'FACEBOOK_STORE_FRIENDS', False)

## Whether to use celery to do the above two.
## This is recommended if you want to store friends or likes
FACEBOOK_CELERY_STORE = getattr(settings, 'FACEBOOK_CELERY_STORE', False)

## Allow custom registration template
FACEBOOK_REGISTRATION_TEMPLATE = getattr(settings,
    'FACEBOOK_REGISTRATION_TEMPLATE', 'registration/registration_form.html')

## Allow custom signup form
FACEBOOK_REGISTRATION_FORM = getattr(settings, 'FACEBOOK_REGISTRATION_FORM', None)

## Debugging
FACEBOOK_DEBUG_REDIRECTS = getattr(settings, 'FACEBOOK_DEBUG_REDIRECTS', False)

## Check for required settings -------------------------------------------------
required_settings = ['FACEBOOK_APP_ID', 'FACEBOOK_APP_SECRET']
locals_dict = locals()
for setting_name in required_settings:
    assert(locals_dict.get(setting_name) is not None,
           'Please provide setting %s' % setting_name)

## Validate: FACEBOOK_CANVAS_HANDLING ------------------------------------------
_facebook_canvas_handling_options = ('force', 'escape')
if FACEBOOK_CANVAS_HANDLING is not None:
    if FACEBOOK_CANVAS_HANDLING not in _facebook_canvas_handling_options:
        raise ImproperlyConfigured("FACEBOOK_CANVAS_HANDLING must either be None or one of %r" % _facebook_canvas_handling_options)
