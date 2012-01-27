"""Django-facebook middleware"""

import logging

from django_facebook.api import _get_access_token_from_request, \
    get_facebook_graph
import django_facebook.settings as facebook_settings
from open_facebook.api import FacebookAuthorization

logger = logging.getLogger(__name__) 

class FacebookRequestMiddleware:
    def process_request(self, request):
        """Process requests for Facebook apps. This is expecially
        useful for canvas apps, since it handles signed_request logins,
        application requests, etc.
        
        Information about the current interaction status with Facebook
        is stored into ``request.fb_info`` as a dict with following
        keys:
        
        - ``is_canvas`` - Whether we are running inside canvas or not.
          This is determined by the presence of a signed request
          via POST.
        - ``is_signed_request`` - Whether we received a signed request,
          either via POST parameter (canvas) or cookie (js sdk method).
        - ``signed_request_type`` - ``"post"`` or ``"cookie"``
        - ``app_request_ids`` - If a ``request_ids`` GET was passed,
          the IDs of requests to be processed.
        - ``is_authenticated`` - Whether we have a valid access_token
          for this user, or not.
        
        - Validate signed requests from Facebook
          - Login when running in canvas
          - For the deauthorize_callback ping
        - Process the requests execution when a request_ids parameter
          is passed -> redirect to somewhere
        - We should also prevent CSRF code to be checked if the request
          is using ``signed_request``.
        
        .. NOTE::
            This middleware should go before CsrfMiddleware in order
            to skip CSRF validation for POSTs inside canvas apps,
            in case a valid signed_request was received.
        """
        
        logger.debug("Running FacebookRequest Middleware")
        
        request.fb_info = {
            "is_canvas": False,
            "is_signed_request": None,
            "signed_request_type": None,
            "app_request_ids": None,
            "is_authenticated": None,
        }
        
        ## Set ``request.csrf_processing_done = True`` to skip CSRF checking for signed_request
        
        ## Check signed request
        _sr_from = None
        _sr_data = None
        
        if request.POST.has_key('signed_request'):
            logger.debug("Got a signed_request via POST")
            _sr_from = 'post'
            _sr_data = request.POST['signed_request']
        elif request.GET.has_key('signed_request'):
            logger.debug("Got a signed_request via GET -- strange, but valid..")
            _sr_from = 'get'
            _sr_data = request.GET['signed_request']
        else:
            cookie_name = 'fbsr_%s' % facebook_settings.FACEBOOK_APP_ID
            cookie_data = request.COOKIES.get(cookie_name)
            if cookie_data:
                logger.debug("Got a signed_request via cookie")
                _sr_from = 'cookie'
                _sr_data = cookie_data
        
        if _sr_data:
            parsed_data = FacebookAuthorization.parse_signed_data(_sr_data)
            if parsed_data:
                if _sr_from in ('post', 'get'):
                    request.fb_info['is_canvas'] = True
                request.fb_info['is_signed_request'] = True
                request.fb_info['signed_request_type'] = _sr_from
                
                ## Skip CSRF validation in case of valid signed request
                request.csrf_processing_done = True
                
                ## TODO: Log in the user
        
        ## --- Application requests --------------------------------------------
        if request.REQUEST.has_key('request_ids'):
            request.fb_info['app_request_ids'] = request.REQUEST['request_ids'].split(',')


        return###===================================== STOP HERE ===============
        
        ## TODO: Check whether we are running inside canvas
        ##  - if we have a signed_request, we are inside canvas
        ## TODO: If we have a valid authentication from signed request, do that
        ## TODO: If we received arguments from a completed OAuth process, handle that
        ## TODO: We should skip CSRF checking for signed requests inside canvas
        ## TODO: If we received ``request_ids``, store them somewhere
        
        access_token = _get_access_token_from_request(request)
        if not access_token:
            request.fb_info['is_authenticated'] = False
        else:
            request.fb_info['is_authenticated'] = True
            fb = get_facebook_graph(request, access_token)
        
        pass
