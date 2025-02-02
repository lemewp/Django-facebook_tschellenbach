import datetime
import logging

from open_facebook import OpenFacebook, FacebookAuthorization
from open_facebook import exceptions as open_facebook_exceptions
from open_facebook.exceptions import OpenFacebookException
from open_facebook.utils import send_warning

from django.forms.util import ValidationError
from django.utils import simplejson as json
from django_facebook import settings as facebook_settings
from django_facebook import signals
from django_facebook.utils import mass_get_or_create, cleanup_oauth_url, get_profile_class

logger = logging.getLogger(__name__)

def require_persistent_graph(request, *args, **kwargs):
    """Just like ``get_persistent graph``, but instead of returning
    ``None``, raises an OpenFacebookException if we can't access Facebook.
    """
    graph = get_persistent_graph(request, *args, **kwargs)
    if not graph:
        raise OpenFacebookException('please authenticate')
    return graph


def get_persistent_graph(request, *args, **kwargs):
    """Uses :py:func:`get_facebook_graph` to get an
    :py:class:`open_facebook.api.OpenFacebook` object.
    the graph in the session, allowing usage across multiple page views.
    Note that Facebook sessions expire at some point, you can't store this
    for permanent usage, unless we require the ``offline_access`` permission.
    """
    if not request:
        raise(ValidationError, 'You must pass a valid ``request`` to use persistent tokens')

    if hasattr(request, 'facebook'):
        graph = request.facebook
        _add_current_user_id(graph, request.user)
        return graph

    ## get the new graph
    graph = get_facebook_graph(request, *args, **kwargs)

    #if it's valid replace the old cache
    if graph is not None and graph.access_token:
        request.session['graph'] = graph
    else:
        facebook_open_graph_cached = request.session.get('graph')
        if facebook_open_graph_cached:
            facebook_open_graph_cached._me = None
        graph = facebook_open_graph_cached

    _add_current_user_id(graph, request.user)
    request.facebook = graph

    return graph

def _get_access_token_from_request(request, redirect_uri=None):
    """Do whatever needed to retrieve an access_token from the request.
    :returns: a ``dict`` containing at least the access_token key.
    """
    
    ## Check for OAuth process `code` argument
    at = _exchange_oauth_code_for_access_token(request.REQUEST.get('code'), redirect_uri)
    if at and at['access_token']:
        at['at_source'] = 'oauth_code'
        return at
    
    ## Check for signed_request argument, or signed cookie
    at = _get_access_token_from_signed_request(request, redirect_uri)
    if at and at['access_token']:
        at['at_source'] = 'signed_request'
        return at
    
    ## Check whether there is an access_token stored in the user profile
    if request.user.is_authenticated():
        profile = request.user.get_profile()
        access_token = getattr(profile, 'access_token', None)
        if access_token:
            return dict(
                access_token=access_token,
                at_source = 'request.user',
                )
    
    ## No access_token found. Sorry.
    return None

def _exchange_oauth_code_for_access_token(code, redirect_uri=None):
    """Try to exchange an OAuth `code` for a proper access_token.
    
    Following code is based on the PHP API:
    https://github.com/facebook/php-sdk/blob/master/src/base_facebook.php
    """
    if not code:
        return None

    ## Create a default for the redirect_uri:
    ## - when using the JavaScript SDK the default should be ''
    ## - for other pages it should be the URL of the current page.
    if not redirect_uri:
        redirect_uri = ''

    ## We need to remove ``signed_request``, ``code`` and ``state``
    ## GET parameters from the current URL.
    redirect_uri = cleanup_oauth_url(redirect_uri)

    try:
        logger.info('Trying to exchange the code for an access_token. redirect_uri=%r', redirect_uri)
        token_response = FacebookAuthorization.convert_code(code, redirect_uri=redirect_uri)
        expires = token_response.get('expires')
        access_token = token_response['access_token']
    except open_facebook_exceptions.OAuthException, e:
        ## This sometimes fails, but it shouldn't raise exceptions
        ## because this happens when an user deauthorizes your
        ## application and then tries to re-authenticate.
        logger.warn('Exchange of code %r failed.', unicode(e))
    else:
        return dict(access_token=access_token, expires=expires)

def _get_access_token_from_signed_request(request, redirect_uri=None):
    """Try to retrieve an access_token from a signed request"""
    ## Check whether we got any signed request
    _signed_data = None
    signed_data = request.REQUEST.get('signed_request')
    if signed_data:
        logger.info('Got signed data from Facebook')
        _signed_data = signed_data
    else:
        cookie_name = 'fbsr_%s' % facebook_settings.FACEBOOK_APP_ID
        cookie_data = request.COOKIES.get(cookie_name)
        if cookie_data:
            logger.info('Got signed cookie from Facebook')
            _signed_data = cookie_data
    
    if _signed_data:
        parsed_data = FacebookAuthorization.parse_signed_data(signed_data)
        if parsed_data:
            logger.debug('Parsing of signed data was successful')
            ## Parsed data can fail because of signing issues
            if 'oauth_token' in parsed_data:
                logger.info('The signed data contains a valid oauth_token')
                ## We already have an active access token in the data
                access_token = parsed_data['oauth_token']
                return dict(access_token=access_token)
            else:
                logger.info('Got code from parsed data')
                ## no access token, need to use this code to get one
                code = parsed_data.get('code', None)
                return _exchange_oauth_code_for_access_token(code, redirect_uri)

def get_facebook_graph(request=None, access_token=None, redirect_uri=None):
    """Returns an OpenFacebook object, instantiated with an ``access_token``.
    
    The access_token can be either specified directly, as argument to
    the function, or it will be determined by one of:
    
    - js authentication flow (signed cookie)
    - facebook app authentication flow (signed cookie)
    - facebook oauth redirect (code param in url)
    - mobile authentication flow (direct access_token)
    - offline access token stored in user profile

    :param request: Standard Django request object.
    :param access_token: (optional) A Facebook access token.
    :param redirect_uri: the path from which you requested the token.
        For some reason Facebook needs exactly this URI when converting
        the code to a token.
        Falls back to the current page without code in the request params.
        You need to specify a ``redirect_uri`` if you are not posting
        and receiving the code on the same page.
    """
    ## Should drop query params be included in the open Facebook API,
    ## maybe, weird this...
    
    parsed_data = None
    expires = None

    ## Try retrieving the cached version of the graph object.
    if hasattr(request, 'facebook'):
        graph = request.facebook
        _add_current_user_id(graph, request.user)
        return graph

    ## Try to retrieve an access_token
    if not access_token:
        at_data = _get_access_token_from_request(request, redirect_uri)
        if at_data:
            access_token = at_data['access_token']
            expires = at_data.get('expires', None)
    
    if not access_token:
        return None

    ## Instantiate the OpenFacebook object with the access_token
    graph = OpenFacebook(access_token, parsed_data, expires=expires)
    if request:
        _add_current_user_id(graph, request.user)

    return graph


def _add_current_user_id(graph, user):
    """Set the current user id, convenient if you want to make sure your
    FB session and user belong together
    """
    if graph:
        graph.current_user_id = None

    if user.is_authenticated() and graph:
        profile = user.get_profile()
        facebook_id = getattr(profile, 'facebook_id', None)
        if facebook_id:
            graph.current_user_id = facebook_id


class FacebookUserConverter(object):
    """
    This conversion class helps you to convert Facebook users to Django users

    Helps with:
    
    - extracting and prepopulating full profile data
    - invite flows
    - importing and storing likes
    """
    def __init__(self, open_facebook):
        
        self.open_facebook = open_facebook
        assert isinstance(open_facebook, OpenFacebook)
        self._profile = None

    def is_authenticated(self):
        return self.open_facebook.is_authenticated()

    def facebook_registration_data(self, username=True):
        """Gets all registration data and ensures its correct
        input for a django registration.
        """
        facebook_profile_data = self.facebook_profile_data()
        user_data = {}
        try:
            user_data = self._convert_facebook_data(
                facebook_profile_data, username=username)
        except OpenFacebookException, e:
            self._report_broken_facebook_data(
                user_data, facebook_profile_data, e)
            raise

        return user_data

    def facebook_profile_data(self):
        """Returns the facebook profile data, together with the image locations
        """
        if self._profile is None:
            profile = self.open_facebook.me()
            profile['image'] = self.open_facebook.my_image_url('large')
            profile['image_thumb'] = self.open_facebook.my_image_url()
            self._profile = profile
        return self._profile

    @classmethod
    def _convert_facebook_data(cls, facebook_profile_data, username=True):
        """Takes facebook user data and converts it to a format for
        usage with Django.
        """
        user_data = facebook_profile_data.copy()
        profile = facebook_profile_data.copy()
        website = profile.get('website')
        if website:
            user_data['website_url'] = cls._extract_url(website)

        user_data['facebook_profile_url'] = profile.get('link')
        user_data['facebook_name'] = profile.get('name')
        if len(user_data.get('email', '')) > 75:
            #no more fake email accounts for facebook
            del user_data['email']

        gender = profile.get('gender', None)

        if gender == 'male':
            user_data['gender'] = 'm'
        elif gender == 'female':
            user_data['gender'] = 'f'

        user_data['username'] = cls._retrieve_facebook_username(user_data)
        user_data['password2'], user_data['password1'] = (
            cls._generate_fake_password(), ) * 2  # same as double equal

        facebook_map = dict(birthday='date_of_birth',
                            about='about_me', id='facebook_id')
        for k, v in facebook_map.items():
            user_data[v] = user_data.get(k)
        user_data['facebook_id'] = int(user_data['facebook_id'])

        if not user_data['about_me'] and user_data.get('quotes'):
            user_data['about_me'] = user_data.get('quotes')

        user_data['date_of_birth'] = cls._parse_data_of_birth(
            user_data['date_of_birth'])

        if username:
            user_data['username'] = cls._create_unique_username(
                user_data['username'])

        return user_data

    @classmethod
    def _extract_url(cls, text_url_field):
        """
        >>> url_text = 'http://www.google.com blabla'
        >>> FacebookAPI._extract_url(url_text)
        u'http://www.google.com/'

        >>> url_text = 'http://www.google.com/'
        >>> FacebookAPI._extract_url(url_text)
        u'http://www.google.com/'

        >>> url_text = 'google.com/'
        >>> FacebookAPI._extract_url(url_text)
        u'http://google.com/'

        >>> url_text = 'http://www.fahiolista.com/www.myspace.com/www.google.com'
        >>> FacebookAPI._extract_url(url_text)
        u'http://www.fahiolista.com/www.myspace.com/www.google.com'

        >>> url_text = u'''http://fernandaferrervazquez.blogspot.com/\r\nhttp://twitter.com/fferrervazquez\r\nhttp://comunidad.redfashion.es/profile/fernandaferrervazquez\r\nhttp://www.facebook.com/group.php?gid3D40257259997&ref3Dts\r\nhttp://fernandaferrervazquez.spaces.live.com/blog/cns!EDCBAC31EE9D9A0C!326.trak\r\nhttp://www.linkedin.com/myprofile?trk3Dhb_pro\r\nhttp://www.youtube.com/account#profile\r\nhttp://www.flickr.com/\r\n Mi galer\xeda\r\nhttp://www.flickr.com/photos/wwwfernandaferrervazquez-showroomrecoletacom/ \r\n\r\nhttp://www.facebook.com/pages/Buenos-Aires-Argentina/Fernanda-F-Showroom-Recoleta/200218353804?ref3Dts\r\nhttp://fernandaferrervazquez.wordpress.com/wp-admin/'''
        >>> FacebookAPI._extract_url(url_text)
        u'http://fernandaferrervazquez.blogspot.com/a'
        """
        import re
        text_url_field = text_url_field.encode('utf8')
        seperation = re.compile('[ ,;\n\r]+')
        parts = seperation.split(text_url_field)
        for part in parts:
            from django.forms import URLField
            url_check = URLField(verify_exists=False)
            try:
                clean_url = url_check.clean(part)
                return clean_url
            except ValidationError:
                continue

    @classmethod
    def _generate_fake_password(cls):
        """Returns a random fake password"""
        import string
        from random import choice
        size = 9
        password = ''.join([choice(string.letters + string.digits)
                            for i in range(size)])
        return password.lower()

    @classmethod
    def _parse_data_of_birth(cls, data_of_birth_string):
        if data_of_birth_string:
            format = '%m/%d/%Y'
            try:
                parsed_date = datetime.datetime.strptime(
                    data_of_birth_string, format)
                return parsed_date
            except ValueError:
                # Facebook sometimes provides a partial date format
                # ie 04/07 (ignore those)
                if data_of_birth_string.count('/') != 1:
                    raise

    @classmethod
    def _report_broken_facebook_data(cls, facebook_data,
                                     original_facebook_data, e):
        """Sends a nice error email with the
        
        - facebook data
        - exception
        - stacktrace
        """
        from pprint import pformat
        data_dump = json.dumps(original_facebook_data)
        data_dump_python = pformat(original_facebook_data)
        message_format = 'The following facebook data failed with error %s' \
                         '\n\n json %s \n\n python %s \n'
        data_tuple = (unicode(e), data_dump, data_dump_python)
        message = message_format % data_tuple
        extra_data = {
            'data_dump': data_dump,
            'data_dump_python': data_dump_python,
            'facebook_data': facebook_data,
        }
        send_warning(message, **extra_data)

    @classmethod
    def _create_unique_username(cls, base_username):
        """Check the database and add numbers to the username
        to ensure its unique all over our db."""
        from django.contrib.auth.models import User
        usernames = list(User.objects.filter(
            username__istartswith=base_username).values_list(
                'username', flat=True))
        usernames_lower = [str(u).lower() for u in usernames]
        username = str(base_username)
        i = 1
        while base_username.lower() in usernames_lower:
            base_username = username + str(i)
            i += 1
        return base_username

    @classmethod
    def _retrieve_facebook_username(cls, facebook_data):
        """Search for the username in 3 places:
        
        - public profile
        - email
        - name
        """
        link = facebook_data.get('link')
        if link:
            username = link.split('/')[-1]
            username = cls._username_slugify(username)
        if 'profilephp' in username:
            username = None

        if not username and 'email' in facebook_data:
            username = cls._username_slugify(facebook_data.get(
                'email').split('@')[0])

        if not username or len(username) < 4:
            username = cls._username_slugify(facebook_data.get('name'))

        return username

    @classmethod
    def _username_slugify(cls, username):
        """Slugify the username and replace `-` with `_`
        to meet username requirements.
        """
        from django.template.defaultfilters import slugify
        return slugify(username).replace('-', '_')

    def get_and_store_likes(self, user):
        """Gets and stores your Facebook likes to DB.
        
        Both the get and the store run in a async task when
        ``FACEBOOK_CELERY_STORE = True``.
        """
        if facebook_settings.FACEBOOK_CELERY_STORE:
            from django_facebook.tasks import get_and_store_likes
            get_and_store_likes.delay(user, self)
        else:
            self._get_and_store_likes(user)

    def _get_and_store_likes(self, user):
        likes = self.get_likes()
        stored_likes = self._store_likes(user, likes)
        return stored_likes

    def get_likes(self, limit=5000):
        """Parses the Facebook response and returns the likes"""
        likes_response = self.open_facebook.get('me/likes', limit=limit)
        likes = likes_response and likes_response.get('data')
        logger.info('found %s likes', len(likes))
        return likes

    def store_likes(self, user, likes):
        """Given a user and likes store these in the db.
        Note this can be a heavy operation, best to do it
        in the background using celery
        """
        if facebook_settings.FACEBOOK_CELERY_STORE:
            from django_facebook.tasks import store_likes
            store_likes.delay(user, likes)
        else:
            self._store_likes(user, likes)

    @classmethod
    def _store_likes(self, user, likes):
        current_likes = inserted_likes = None
        
        if likes:
            from django_facebook.models import FacebookLike
            base_queryset = FacebookLike.objects.filter(user_id=user.id)
            global_defaults = dict(user_id=user.id)
            id_field = 'facebook_id'
            default_dict = {}
            for like in likes:
                name = like.get('name')
                created_time_string = like.get('created_time')
                created_time = None
                if created_time_string:
                    created_time = datetime.datetime.strptime(
                        like['created_time'], "%Y-%m-%dT%H:%M:%S+0000")
                default_dict[like['id']] = dict(
                    created_time=created_time,
                    category=like.get('category'),
                    name=name
                )
            current_likes, inserted_likes = mass_get_or_create(
                FacebookLike, base_queryset, id_field, default_dict,
                global_defaults)
            logger.debug('found %s likes and inserted %s new likes',
                         len(current_likes), len(inserted_likes))

        #fire an event, so u can do things like personalizing the users' account
        #based on the likes
        signals.facebook_post_store_likes.send(sender=get_profile_class(),
            user=user, likes=likes, current_likes=current_likes,
            inserted_likes=inserted_likes,
        )
        
        return likes

    def get_and_store_friends(self, user):
        """Gets and stores your Facebook friends to DB
        Both the get and the store run in a async task when
        ``FACEBOOK_CELERY_STORE = True``
        """
        if facebook_settings.FACEBOOK_CELERY_STORE:
            from django_facebook.tasks import get_and_store_friends
            get_and_store_friends.delay(user, self)
        else:
            self._get_and_store_friends(user)

    def _get_and_store_friends(self, user):
        """Getting the friends via fb and store in database."""
        friends = self.get_friends()
        stored_friends = self._store_friends(user, friends)
        return stored_friends

    def get_friends(self, limit=5000):
        """Connects to the Facebook API and gets the user's friends"""
        friends = getattr(self, '_friends', None)
        if friends is None:
            friends_response = self.open_facebook.fql(
                "SELECT uid, name, sex FROM user WHERE uid IN (SELECT uid2 " \
                "FROM friend WHERE uid1 = me()) LIMIT %s" % limit)
            # friends_response = self.open_facebook.get('me/friends',
            #                                           limit=limit)
            # friends = friends_response and friends_response.get('data')
            friends = []
            for response_dict in friends_response:
                response_dict['id'] = response_dict['uid']
                friends.append(response_dict)

        logger.info('found %s friends', len(friends))

        return friends

    def store_friends(self, user, friends):
        """Stores the given friends locally for this user.
        Quite slow, better do this using celery on a secondary db.
        """
        if facebook_settings.FACEBOOK_CELERY_STORE:
            from django_facebook.tasks import store_friends
            store_friends.delay(user, friends)
        else:
            self._store_friends(user, friends)

    @classmethod
    def _store_friends(self, user, friends):
        from django_facebook.models import FacebookUser
        current_friends = inserted_friends = None
        
        #store the users for later retrieval
        if friends:
            #see which ids this user already stored
            base_queryset = FacebookUser.objects.filter(user_id=user.id)
            global_defaults = dict(user_id=user.id)
            default_dict = {}
            for f in friends:
                name = f.get('name')
                default_dict[str(f['id'])] = dict(name=name)
            id_field = 'facebook_id'

            current_friends, inserted_friends = mass_get_or_create(
                FacebookUser, base_queryset, id_field, default_dict,
                global_defaults)
            logger.debug('found %s friends and inserted %s new ones',
                         len(current_friends), len(inserted_friends))
            
        #fire an event, so u can do things like personalizing suggested users
        #to follow
        signals.facebook_post_store_friends.send(sender=get_profile_class(),
            user=user, friends=friends, current_friends=current_friends,
            inserted_friends=inserted_friends,
        )

        return friends

    def registered_friends(self, user):
        """Returns all profile models which are already registered
        on your site and a list of friends which are not on your site.
        """
        from django_facebook.utils import get_profile_class
        profile_class = get_profile_class()
        friends = self.get_friends(limit=1000)

        if friends:
            friend_ids = [f['id'] for f in friends]
            friend_objects = profile_class.objects.filter(
                facebook_id__in=friend_ids).select_related('user')
            registered_ids = [f.facebook_id for f in friend_objects]
            new_friends = [f for f in friends if f['id'] not in registered_ids]
        else:
            new_friends = []
            friend_objects = profile_class.objects.none()

        return friend_objects, new_friends
