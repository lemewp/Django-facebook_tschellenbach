from django.utils.safestring import mark_safe

def facebook(request):
    """Context processor that includes some django_facebook-specific
    variables to templates context:
    
    - ``FACEBOOK_APP_ID`` - The ID of the Facebook application, as specified
      in the application settings. This is used by the JavaScript SDK.
    - ``FACEBOOK_SETTINGS`` - JSON-encoded object containing misc
      configuration settings for Facebook-related stuff.
    """
    context = {}
    from django_facebook import settings as fb_settings
    from open_facebook.utils import json
    context['FACEBOOK_APP_ID'] = fb_settings.FACEBOOK_APP_ID
    context['FACEBOOK_DEFAULT_SCOPE'] = fb_settings.FACEBOOK_DEFAULT_SCOPE

    default_scope_js = unicode(json.dumps(fb_settings.FACEBOOK_DEFAULT_SCOPE))
    default_scope_js = mark_safe(default_scope_js)
    context['FACEBOOK_DEFAULT_SCOPE_JS'] = default_scope_js
    
    context['FACEBOOK_CANVAS_HANDLING'] = fb_settings.FACEBOOK_CANVAS_HANDLING
    context['FACEBOOK_CANVAS_PAGE'] = fb_settings.FACEBOOK_CANVAS_PAGE
    
    _js_settings = {
        "app_id" : fb_settings.FACEBOOK_APP_ID,
        "app_secret": "CHUPAAA!!", ## We don't want to reveal app_secret!!
        "canvas_handling" : fb_settings.FACEBOOK_CANVAS_HANDLING,
        "canvas_page" : fb_settings.FACEBOOK_CANVAS_PAGE,
        "default_scope" : fb_settings.FACEBOOK_DEFAULT_SCOPE,
    }
    
    context['FACEBOOK_SETTINGS'] = json.dumps(_js_settings)
    
    _body_classes = []
    
    if getattr(request, 'fb_info', {}).get('is_canvas', False):
        _body_classes.append('canvas-page')
    else:
        _body_classes.append('stand-alone-page')
    
    context['FACEBOOK_BODY_CLASSES'] = " ".join(_body_classes)

    return context
