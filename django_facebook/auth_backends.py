from django.contrib.auth import models, backends
from django.db.utils import DatabaseError
from django_facebook.utils import get_profile_class
#from user import models as models_user


class FacebookBackend(backends.ModelBackend):
    """Authentication backend for use with Facebook"""
    
    def authenticate(self, facebook_id=None, facebook_email=None):
        """Authenticate the Facebook user by ``facebook_id`` or ``facebook_email``.
        
        We filter using an OR to allow existing members to connect with
        their Facebook ID using email.
        
        :param facebook_id: ID of the Facebook user.
        :param facebook_email: EMail the user is authenticated on Facebook
            with. We need to make sure the email was verified on Facebook,
            before trusting this!
        :returns: a ``django.contrib.auth.models.User`` or ``None``
        """
        if facebook_id or facebook_email:
            profile_class = get_profile_class()
            profile_query = profile_class.objects.all().order_by('user').select_related('user')
            profile = None

            ## Filter on email or ``facebook_id``, two queries for better
            ## queryplan with large data sets
            
            if facebook_id:
                profiles = profile_query.filter(facebook_id=facebook_id)[:1]
                profile = profiles[0] if profiles else None
            
            if profile is None and facebook_email:
                try:
                    ## WARNING! We assume that all the user emails are verified
                    profiles = profile_query.filter(user__email__iexact=facebook_email)[:1]
                    profile = profiles[0] if profiles else None
                except DatabaseError:
                    try:
                        user = models.User.objects.get(email=facebook_email)
                    except models.User.DoesNotExist:
                        user = None
                    profile = user.get_profile() if user else None

            if profile:
                ## Populate the profile cache while we're getting it anyway
                user = profile.user
                user._profile = profile
                return user
