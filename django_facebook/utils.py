import logging
import re

from django.conf import settings
from django.db import models
from django.http import QueryDict, HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.encoding import iri_to_uri

logger = logging.getLogger(__name__)


def test_permissions(request, scope_list, redirect_uri=None):
    """Calls Facebook ``me/permissions`` to see if the user granted us
    some specified permissions or not.
    
    :param request: The current request
    :param scope_list: List of permissions that will be checked
    :param redirect_uri: URI to which to redirect the user
        after authentication.
    """
    from django_facebook.api import get_persistent_graph
    from open_facebook import exceptions as facebook_exceptions
    fb = get_persistent_graph(request, redirect_uri=redirect_uri)
    permissions_dict = {}
    if fb:
        try:
            permissions_response = fb.get('me/permissions')
            permissions = permissions_response['data'][0]
        except facebook_exceptions.OAuthException:
            ## This happens when someone revokes their permissions
            ## while the session is still stored
            permissions = {}
        permissions_dict = dict([(k, bool(int(v)))
                                 for k, v in permissions.items()
                                 if v == '1' or v == 1])

    ## See if we have all permissions
    scope_allowed = True
    for permission in scope_list:
        if permission not in permissions_dict:
            scope_allowed = False

    ## Raise if this happens after a redirect though
    if not scope_allowed and request.GET.get('attempt'):
        raise ValueError(
              'Somehow Facebook is not giving us the permissions needed, ' \
              'lets break instead of endless redirects. FB was %r and ' \
              'permissions %r' % (fb, permissions_dict))

    return scope_allowed


def get_oauth_url(request, scope, redirect_uri=None, extra_params=None):
    """Returns the URL of the Facebook OAuth dialog for this application,
    asking for specified permissions and redirecting to given
    ``redirect_uri``.
    
    .. TODO:: Should we improve this by always redirecting to a specific
        location after OAuth, and from then redirect to final destination
        when the OAuth process is completed?
    
    :param request: The current request
    :param scope: List of permissions that will be required
    :param redirect_uri: The URI the user will be redirected to after OAuth.
        Defaults to the current location.
    :param extra_params: Extra query arguments to be added to redirect_uri
    :returns: A tuple: ``(oauth_url, redirect_uri)``
    """
    from django_facebook import settings as facebook_settings
    scope = parse_scope(scope)
    query_dict = QueryDict('', True)
    query_dict['scope'] = ','.join(scope)
    query_dict['client_id'] = facebook_settings.FACEBOOK_APP_ID
    
    ## Create absolute URI from ``redirect_uri``.
    ## If redirect_uri is None, the current URI will be used.
    redirect_uri = request.build_absolute_uri(location=redirect_uri)
    
    import urlparse
    _parsed_uri = urlparse.urlparse(redirect_uri)
    _uri_args = QueryDict(_parsed_uri.query, True)
    
    ## Set attempt=1 to prevent endless redirect loops
    if _uri_args.get('attempt') != '1':
        _uri_args['attempt'] = '1'
    
    ## Add extra_params to redirect_uri
    if extra_params:
        _uri_args.update(extra_params)
    
    ## Recreate redirect_uri
    redirect_uri = urlparse.urlunparse(_parsed_uri._replace(query=_uri_args.urlencode()))

    query_dict['redirect_uri'] = redirect_uri
    url = 'https://www.facebook.com/dialog/oauth?%s' % query_dict.urlencode()
    return url, redirect_uri


class CanvasRedirect(HttpResponse):
    """Redirect for Facebook Canvas pages.
    
    Instead of returning a 403, this response object returns a rendered
    HTML page containing some JavaScript that changes location of the
    ``top`` browser window.
    """
    def __init__(self, redirect_to):
        self.redirect_to = redirect_to
        self.location = iri_to_uri(redirect_to)
        context = dict(location=self.location)
        js_redirect = render_to_string('django_facebook/canvas_redirect.html', context)
        super(CanvasRedirect, self).__init__(js_redirect)
        
def response_redirect(redirect_url, canvas=False):
    """Abstract away canvas redirects.
    
    This method returns a :py:class:`CanvasRedirect` response, used
    to redirect the user to another page via JavaScript inside a Facebook
    canvas page.
    """
    if canvas:
        return CanvasRedirect(redirect_url)
    else:
        return HttpResponseRedirect(redirect_url)

def next_redirect(request, default='/', additional_params=None,
                  next_key='next', redirect_url=None, canvas=False):
    """Redirects to the value specified in the GET parameter(s) specified
    in the ``next_key`` parameter, or to ``redirect_url`` if no ``next``
    URL was found.
    
    :param request: The current request
    :param default: The default redirect URL
    :param additional_params: Additional parameters to be added to
        the final redirect url
    :param next_key: The key that will be looked for in the request,
        to find a redirect URL
    :param redirect_url: The URL to which to redirect the user, or ``None``
        to trigger autodiscover
    :param canvas: Whether we are running in canvas
    """
    from django_facebook import settings as facebook_settings
    
    if facebook_settings.FACEBOOK_DEBUG_REDIRECTS:
        return HttpResponse('<html><head></head><body><div>Debugging</div></body></html>')
    
    if not isinstance(next_key, (list, tuple)):
        next_key = [next_key]

    ## get the redirect url
    if not redirect_url:
        for key in next_key:
            redirect_url = request.REQUEST.get(key)
            if redirect_url:
                break
        if not redirect_url:
            redirect_url = default

    if additional_params:
        query_params = QueryDict('', True)
        query_params.update(additional_params)
        seperator = '&' if '?' in redirect_url else '?'
        redirect_url += seperator + query_params.urlencode()

    if canvas:
        return CanvasRedirect(redirect_url)
    else:
        return HttpResponseRedirect(redirect_url)


def get_profile_class():
    """Gets the class to be used for user profiles"""
    profile_string = getattr(settings, 'AUTH_PROFILE_MODULE', 'member.UserProfile')
    app_label, model = profile_string.split('.')
    return models.get_model(app_label, model)


def mass_get_or_create(model_class, base_queryset, id_field, default_dict,
                       global_defaults):
    """
    Updates the data by inserting all not found records
    Doesnt delete records if not in the new data

    Example usage::
    
        >>> model_class = ListItem #the class for which you are doing the insert
        >>> base_query_set = ListItem.objects.filter(user=request.user, list=1) #query for retrieving currently stored items
        >>> id_field = 'user_id' #the id field on which to check
        >>> default_dict = {'12': dict(comment='my_new_item'), '13': dict(comment='super')} #list of default values for inserts
        >>> global_defaults = dict(user=request.user, list_id=1) #global defaults
    """
    current_instances = list(base_queryset)
    current_ids = [unicode(getattr(c, id_field)) for c in current_instances]
    given_ids = map(unicode, default_dict.keys())
    new_ids = [g for g in given_ids if g not in current_ids]
    inserted_model_instances = []
    for new_id in new_ids:
        defaults = default_dict[new_id]
        defaults[id_field] = new_id
        defaults.update(global_defaults)
        model_instance = model_class.objects.create(
            **defaults
        )
        inserted_model_instances.append(model_instance)
    # returns a list of existing and new items
    return current_instances, inserted_model_instances


def get_form_class(backend, request):
    """Will use registration form in the following order:
    
    1. User configured RegistrationForm
    2. ``backend.get_form_class(request)`` from django-registration 0.8
    3. ``RegistrationFormUniqueEmail`` from django-registration < 0.8
    """
    from django_facebook import settings as facebook_settings
    form_class = None

    ## Try the setting
    form_class_string = facebook_settings.FACEBOOK_REGISTRATION_FORM
    if form_class_string:
        form_class = get_class_from_string(form_class_string, None)

    if not form_class:
        from registration.forms import RegistrationFormUniqueEmail
        form_class = RegistrationFormUniqueEmail
        if backend:
            form_class = backend.get_form_class(request)
    
    return form_class


def get_registration_backend():
    """Ensures compatibility with the new and old version
    of django registration.
    """
    backend = None
    try:
        # support for the newer implementation
        from registration.backends import get_backend
        try:
            backend = get_backend(settings.REGISTRATION_BACKEND)
        except:
            raise(ValueError,
                  'Cannot get django-registration backend from ' \
                  'settings.REGISTRATION_BACKEND')
    except ImportError:
        backend = None
    return backend


def parse_scope(scope):
    """Converts a comma-separated string or a ``tuple`` into a ``list``."""
    if not scope:
        raise ValueError, 'Scope is required'
    if isinstance(scope, basestring):
        scope_list = scope.split(',')
    elif isinstance(scope, (list, tuple)):
        scope_list = list(scope)
    return scope_list


def to_int(input, default=0, exception=(ValueError, TypeError), regexp=None):
    """Convert the given input to an integer or return default

    When trying to convert the exceptions given in the exception parameter
    are automatically caught and the default will be returned.

    :param input: The value to be converted to integer
    :param default: The value to return in case integer conversion fails
    :param regexp: An optional regular expression to be used to find
        the digits in a string.
    
        - if set to ``True``, it means "match any digit in the string"
        - if it is a ``regexp`` object, or any object with a `search()`
          method, it will be used as-is.
        - if it is a string, it will be compiled as a regular expression
          and then used.

    The last group of the regexp will be used as value
    """
    if regexp is True:
        regexp = re.compile('(\d+)')
    elif isinstance(regexp, basestring):
        regexp = re.compile(regexp)
    elif hasattr(regexp, 'search'):
        pass
    elif regexp is not None:
        raise(TypeError, 'Unknown argument passed for the regexp parameter')

    try:
        if regexp:
            match = regexp.search(input)
            if match:
                input = match.groups()[-1]
        return int(input)
    except exception:
        return default


def remove_query_param(url, key):
    p = re.compile('%s=[^=&]*&' % key, re.VERBOSE)
    url = p.sub('', url)
    p = re.compile('%s=[^=&]*' % key, re.VERBOSE)
    url = p.sub('', url)
    return url


def replace_query_param(url, key, value):
    p = re.compile('%s=[^=&]*' % key, re.VERBOSE)
    return p.sub('%s=%s' % (key, value), url)


DROP_QUERY_PARAMS = ['code', 'signed_request', 'state']


def cleanup_oauth_url(redirect_uri):
    """We have to maintain order with respect to the query parameters,
    which is a bit of a pain.
    
    .. TODO:: Very hacky will subclass ``QueryDict`` to ``SortedQueryDict``
       at some point And use a decent sort function
    
    .. TODO:: Why is all this needed??
    """
    if '?' in redirect_uri:
        redirect_base, redirect_query = redirect_uri.split('?', 1)
        query_dict_items = QueryDict(redirect_query).items()
    else:
        query_dict_items = QueryDict('', True)

    # filtered_query_items = [(k, v) for k, v in query_dict_items
    #                         if k.lower() not in DROP_QUERY_PARAMS]
    # new_query_dict = QueryDict('', True)
    # new_query_dict.update(dict(filtered_query_items))

    excluded_query_items = [(k, v) for k, v in query_dict_items
                            if k.lower() in DROP_QUERY_PARAMS]
    for k, v in excluded_query_items:
        redirect_uri = remove_query_param(redirect_uri, k)

    redirect_uri = redirect_uri.strip('?')
    redirect_uri = redirect_uri.strip('&')

    return redirect_uri


def get_class_from_string(path, default='raise'):
    """Returns the class specified by the string.

    IE: ``django.contrib.auth.models.User`` will return the user class

    If no default is provided and the class cannot be located
    (e.g., because no such module exists, or because the module does
    not contain a class of the appropriate name),
    ``django.core.exceptions.ImproperlyConfigured`` is raised.
    """
    from django.core.exceptions import ImproperlyConfigured
    try:
        from importlib import import_module
    except ImportError:
        from django.utils.importlib import import_module
    i = path.rfind('.')
    module, attr = path[:i], path[i + 1:]
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured('Error loading class %s: "%s"' % (module, e))
    try:
        backend_class = getattr(mod, attr)
    except AttributeError:
        if default == 'raise':
            raise ImproperlyConfigured(
                'Module "%s" does not define a class named "%s"' % (module, attr))
    return backend_class
