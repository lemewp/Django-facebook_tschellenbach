from django.utils.safestring import mark_safe

def facebook(request):
    """Context processor that includes some django_facebook-specific
    variables to templates context:
    
    - ``FACEBOOK_APP_ID`` - The ID of the Facebook application, as specified
      in the application settings. This is used by the JavaScript SDK.
    - ``FACEBOOK_DEFAULT_SCOPE`` - From the settings
    - ``FACEBOOK_DEFAULT_SCOPE_JS`` - JSON-encoded version
      of ``FACEBOOK_DEFAULT_SCOPE``
    """
    context = {}
    from django_facebook import settings as fb_settings
    from open_facebook.utils import json
    context['FACEBOOK_APP_ID'] = fb_settings.FACEBOOK_APP_ID
    context['FACEBOOK_DEFAULT_SCOPE'] = fb_settings.FACEBOOK_DEFAULT_SCOPE

    default_scope_js = unicode(json.dumps(fb_settings.FACEBOOK_DEFAULT_SCOPE))
    default_scope_js = mark_safe(default_scope_js)
    context['FACEBOOK_DEFAULT_SCOPE_JS'] = default_scope_js

    ## TODO: Send a configuration array for use with JavaScript
    ## TODO: Add some classes to page body, in order to let different CSS customizations for normal and canvas pages

    return context
