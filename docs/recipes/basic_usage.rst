################################################################################
Basic usage
################################################################################

Installation
------------

Download the source code or use ``pip install django_facebook``.


**Create a Facebook App**

In case you don't yet have a facebook app. You need an app to use the open graph api and make the login process work.
You can create a facebook app at this url: http://www.facebook.com/developers/createapp.php

**Settings**

Define the following settings in your settings.py file:

::

    FACEBOOK_APP_ID
    FACEBOOK_APP_SECRET

**Url config, context processor, auth backend**

add django facebook to your installed apps::

    'django_facebook',

add this line to your context processors (``TEMPLATE_CONTEXT_PROCESSORS``
setting)::

    'django_facebook.context_processors.facebook',

add this to your ``AUTHENTICATION_BACKENDS`` setting::

    'django_facebook.auth_backends.FacebookBackend',
    
add this line to your url config::

    (r'^facebook/', include('django_facebook.urls')),

**Update your models**

An abstract model is specified here django_facebook/models.py
Add these fields to your profile model or subclass the abstract class.
See the django docs for settings up a Profile model or understanding abstract classes.

**Check the example**

Right now you should have a working registration/connect/login in flow available at /facebook/connect/
Test if everything is working and ensure you didn't miss a step somewhere.
If you encounter any difficulties please open an issue.

**Django Userena**

A few settings changes are needed to play nicely with Django Userena.
In your settings point Django Facebook to the right registration form and template:

::

    FACEBOOK_REGISTRATION_FORM = 'userena.forms.SignupForm'
    FACEBOOK_REGISTRATION_TEMPLATE = 'userena/signup_form.html'

Supporting any other registration system is quite easy.
Adjust the above settings to point to your own code.
Note that the form's save method needs to return the new user object.


**Common bugs**

Django Facebook expects that you are using static files in order to load the required javascript.
If you are not using staticfiles you should load facebook.js provided in the static directory manually.

Another common issue are the url matching settings from Facebook. Facebook requires you to fill in a domain for your application.
In order for things to work with local development you need to use the same domain. So if you production site is www.mellowmorning.com you
should run your development server on something like local.mellowmorning.com in order for facebook to allow authentication.

If you encounter any difficulties please open an issue.

**Customize and integrate into your site**

Not it's time to customize things a little.
For an example you can look at connect.html in the templates directory.

First load the css:

::

    <link href="{{ STATIC_URL }}css/facebook.css" type="text/css" rel="stylesheet" media="all" />

Secondly load the javascript:

::

    {% include 'django_facebook/_facebook_js.html' %}
    
If you encounter issues here you probably don't have django static files setup correctly. 
Alternatively you might be missing the context processor.


Subsequently implement a form which calls Facebook via javascript.
Note that you can control which page to go to after connect using the next input field.

::

<form action="{% url facebook_connect %}?facebook_login=1" method="post">
<a href="javascript:void(0);" style="font-size: 20px;" onclick="F.connect(this.parentNode);">Register, login or connect with facebook</a>
<input type="hidden" value="{{ request.path }}" name="next" />
</form>



Signals
-------

Django-facebook ships with a few signals that you can use to easily accommodate Facebook related activities with your project.

``facebook_user_registered`` signal is sent whenever a new user is registered by Django-facebook, for example:

::

    from django.contrib.auth.models import User
    from django_facebook import signals

    def fb_user_registered_handler(sender, user, facebook_data, \*\*kwargs):
        # Do something involving user here

    signals.facebook_user_registered.connect(user_registered, sender=User)


``facebook_pre_update`` signal is sent just before Django-facebook updates the profile model with Facebook data. If you want to manipulate Facebook or profile information before it gets saved, this is where you should do it. For example:

::
    
    from django_facebook import signals
    from django_facebook.utils import get_profile_class

    def pre_facebook_update(sender, profile, facebook_data, \*\*kwargs):
        profile.facebook_information_updated = datetime.datetime.now()
        # Manipulate facebook_data here
    
    profile_class = get_profile_class()
    signals.facebook_pre_update.connect(pre_facebook_update, sender=profile_class)


``facebook_post_update`` signal is sent after Django-facebook finishes updating the profile model with Facebook data. You can perform other Facebook connect or registration related processing here. 

::
    
    from django_facebook import signals
    from django_facebook.utils import get_profile_class

    def post_facebook_update(sender, profile, facebook_data, \*\*kwargs):
        # Do other stuff
    
    profile_class = get_profile_class()
    signals.facebook_post_update.connect(post_facebook_update, sender=profile_class)

``facebook_post_store_friends`` signal is sent after Django-facebook finishes storing the user's friends.   

::
    
    from django_facebook import signals
    from django_facebook.utils import get_profile_class

    def post_friends(sender, user, friends, current_friends, inserted_friends, \*\*kwargs):
        # Do other stuff
    
    profile_class = get_profile_class()
    facebook_post_store_friends.connect(post_friends, sender=profile_class)

``facebook_post_store_likes`` signal is sent after Django-facebook finishes storing the user's likes. This is usefull if you want to customize what topics etc to follow.   

::
    
    from django_facebook import signals
    from django_facebook.utils import get_profile_class

    def post_likes(sender, user, likes, current_likes, inserted_likes, \*\*kwargs):
        # Do other stuff
    
    profile_class = get_profile_class()
    facebook_post_store_likes.connect(post_likes, sender=profile_class)

