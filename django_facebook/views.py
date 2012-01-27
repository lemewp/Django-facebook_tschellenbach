import logging

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse, QueryDict, HttpResponseNotAllowed,\
    HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt

## NOTE: from inside the application, you can directly import the file
from django_facebook import exceptions as facebook_exceptions, settings as facebook_settings
from django_facebook.api import get_persistent_graph, FacebookUserConverter, require_persistent_graph
from django_facebook.connect import CONNECT_ACTIONS, connect_user
from django_facebook.decorators import facebook_required, facebook_required_lazy
from django_facebook.utils import next_redirect, CanvasRedirect
from open_facebook.exceptions import OpenFacebookException
from open_facebook.utils import send_warning
from open_facebook.api import FacebookAuthorization

logger = logging.getLogger(__name__)


### --- FUNCTIONAL VIEWS -------------------------------------------------------

def fb_oauth(request):
    """View to process the OAuth login via Facebook.
    
    This view accepts a GET argument "next" to specify the page where
    to go upon successful OAuth authentication.
    This defaults to '/' in order to prevent infinite redirects.
    """
    
    if request.GET.get('next'):
        request.session['facebook_oauth_next'] = request.GET['next']
    if not request.session['facebook_oauth_next']:
        request.session['facebook_oauth_next'] = '/'
    next_url = request.session['facebook_oauth_next']
    
    oauth_code = request.GET.get('code') or None
    redirect_uri = reversed("django_facebook.views.fb_oauth")
    
    error_info = {
        'error': request.GET.get('error') or None,
        'error_reason': request.GET.get('error_reason') or None,
        'error_description': request.GET.get('error_description') or None,
    }
    
    if error_info['error']:
        if error_info['error_reason'] == 'user_denied':
            messages.warning(request,
                             "You must click on the 'Authorize' button in order to log in with Facebook!")
        else:
            messages.error(request,
                           "An error occurred while trying to authenticate on Facebook: %s (%s)" \
                           % (error_info['error_reason'], error_info['error_description']))
        return HttpResponseRedirect(next_url)
    
    if not oauth_code:
        ## Start redirecting to the OAuth dialog..
        import uuid, hashlib
        ## CSRF prevention
        _state = str(hashlib.md5(uuid.uuid1()).hexdigest())
        request.session['facebook_oauth_state'] = _state
        
        qd = QueryDict('', True)
        qd['client_id'] = settings.FACEBOOK_APP_ID
        qd['redirect_uri'] = redirect_uri
        qd['state'] = _state
        
        dialog_url = "https://www.facebook.com/dialog/oauth?%s" % qd.urlencode()
        
        return CanvasRedirect(dialog_url) # Is this needed?? - what about HttpResponseRedirect .. ?
    
    else:
        ## We got an OAuth code
        if request.REQUEST.get('state') == request.session['facebook_oauth_state']:
            result = FacebookAuthorization.convert_code(code=oauth_code, redirect_uri=redirect_uri)
            access_token = result['access_token']
            request.session['facebook_access_token'] = access_token
            ## TODO : Trigger a signal here to allow user registration etc.
            ## TODO: Redirect somewhere else..
            return HttpResponseRedirect(next_url)
        else:
            raise HttpResponseNotAllowed("State doesn't match - you might be victim of CSRF")
    
    
    
    #https://www.facebook.com/dialog/oauth?
    #client_id=YOUR_APP_ID&redirect_uri=YOUR_URL
    #&scope=...
    
    #http://YOUR_URL?error_reason=user_denied&
    #error=access_denied&error_description=The+user+denied+your+request.

    #https://graph.facebook.com/oauth/access_token?
    # client_id=YOUR_APP_ID&redirect_uri=YOUR_URL&
    # client_secret=YOUR_APP_SECRET&code=THE_CODE_FROM_ABOVE
    
    pass


def fb_deauthorize(request):
    """Deauthorize callback, pinged when an user deauthorizes this app."""
    pass



### --- TESTING VIEWS - SHOULD BE MOVED AWAY! ----------------------------------

@facebook_required(scope='publish_actions')
def open_graph_beta(request):
    """Simple example on how to do open graph postings"""
    fb = get_persistent_graph(request)
    entity_url = 'http://www.fashiolista.com/item/2081202/'
    fb.set('me/fashiolista:love', item=entity_url)
    messages.info(request,
                  'Frictionless sharing to open graph beta action ' \
                  'fashiolista:love with item_url %s, this url contains ' \
                  'open graph data which Facebook scrapes' % entity_url)


@facebook_required(scope='publish_stream')
def wall_post(request):
    fb = get_persistent_graph(request)
    message = request.REQUEST.get('message')
    fb.set('me/feed', message=message)
    messages.info(request, 'Posted the message to your wall')
    return next_redirect(request)


@facebook_required(scope='publish_stream,user_photos')
def image_upload(request):
    fb = get_persistent_graph(request)
    pictures = request.REQUEST.getlist('pictures')

    for picture in pictures:
        fb.set('me/photos', url=picture, message='the writing is one The '
            'wall image %s' % picture)

    messages.info(request, 'The images have been added to your profile!')

    return next_redirect(request)


@csrf_exempt
@facebook_required_lazy(extra_params=dict(facebook_login='1'))
def connect(request):
    """
    Handles the view logic around connect user
    - (if authenticated) connect the user
    - login
    - register
    """
    context = RequestContext(request)

    assert context.get('FACEBOOK_APP_ID'), 'Please specify a facebook app id '\
        'and ensure the context processor is enabled'
    facebook_login = bool(int(request.REQUEST.get('facebook_login', 0)))

    if facebook_login:
        logger.info('trying to connect using facebook')
        graph = get_persistent_graph(request)
        if graph:
            logger.info('found a graph object')
            facebook = FacebookUserConverter(graph)
            if facebook.is_authenticated():
                logger.info('facebook is authenticated')
                facebook_data = facebook.facebook_profile_data()
                #either, login register or connect the user
                try:
                    action, user = connect_user(request)
                    logger.info('Django facebook performed action: %s', action)
                except facebook_exceptions.IncompleteProfileError, e:
                    warn_message = u'Incomplete profile data encountered '\
                        u'with error %s' % e
                    send_warning(warn_message, e=e,
                                 facebook_data=facebook_data)

                    context['facebook_mode'] = True
                    context['form'] = e.form
                    return render_to_response(
                        facebook_settings.FACEBOOK_REGISTRATION_TEMPLATE,
                        context_instance=context,
                    )

                if action is CONNECT_ACTIONS.CONNECT:
                    messages.info(request, _("You have connected your account "
                        "to %s's facebook profile") % facebook_data['name'])
                elif action is CONNECT_ACTIONS.REGISTER:
                    return user.get_profile().post_facebook_registration(
                        request)
        else:
            if 'attempt' in request.GET:
                return next_redirect(request, next_key=['error_next', 'next'],
                    additional_params=dict(fb_error_or_cancel=1))
            else:
                logger.info('Facebook authentication needed for connect, ' \
                            'raising an error')
                raise OpenFacebookException('please authenticate')

        return next_redirect(request)

    if not settings.DEBUG and facebook_settings.FACEBOOK_HIDE_CONNECT_TEST:
        raise Http404

    return render_to_response('django_facebook/connect.html', context)


def connect_async_ajax(request):
    """
    Not yet implemented:
    The idea is to run the entire connect flow on the background using celery
    Freeing up webserver resources, when facebook has issues
    """
    from django_facebook import tasks as facebook_tasks
    graph = get_persistent_graph(request)
    output = {}
    if graph:
        FacebookUserConverter(graph)
        task = facebook_tasks.async_connect_user(request, graph)
        output['task_id'] = task.id
    from open_facebook.utils import json
    json_dump = json.dumps(output)
    return HttpResponse(json_dump)


def poll_connect_task(request, task_id):
    """
    Not yet implemented
    """
    pass


@facebook_required_lazy(canvas=True)
def canvas(request):
    """
    Example of a canvas page.
    Canvas pages require redirects to work using javascript instead of http headers
    The facebook required and facebook required lazy decorator abstract this away
    """
    context = RequestContext(request)
    fb = require_persistent_graph(request)
    likes = fb.get('me/likes')['data']
    context['likes'] = likes

    return render_to_response('django_facebook/canvas.html', context)




