################################################################################
Module: models
################################################################################


.. py:class:: FacebookProfileModel(django.db.models.Model)

    Abstract model class, containing fields to be added to your profile model.
    
    .. NOTE::
       If you don't use this this abstract class, make sure you copy/paste
       the fields in your custom model.
    
    **Fields:**::
    
        about_me = models.TextField(blank=True)
        facebook_id = models.BigIntegerField(blank=True, unique=True, null=True)
        access_token = models.TextField(
            blank=True, help_text='Facebook token for offline access')
        facebook_name = models.CharField(max_length=255, blank=True)
        facebook_profile_url = models.TextField(blank=True)
        website_url = models.TextField(blank=True)
        blog_url = models.TextField(blank=True)
        image = models.ImageField(blank=True, null=True,
            upload_to='profile_images', max_length=255)
        date_of_birth = models.DateField(blank=True, null=True)
        raw_data = models.TextField(blank=True)

    .. py:attribute:: facebook_id

        A ``BigIntegerField`` containing the user's Facebook ID.

    .. py:attribute:: access_token

        Contains an OAuth ``access_token`` for this user.
        
        .. WARNING:: Unless the user granted us ``offline_access``
            permission, this ``access_token`` may expire and thus not
            always be usable..

    .. py:attribute:: facebook_name

        The full name, as seen on Facebook.

    .. py:attribute:: facebook_profile_url

        URL to the Facebook profile of the user. This isn't always
        ``https://www.facebook.com/profile.php?id=<user-id>``, since
        Facebook also support "vanity" urls such as ``https://www.facebook.com/myname``.

    .. py:attribute:: raw_data

        Raw user data, as retrieved from Graph API ``/me`` request.
        This is stored as a json-encoded string.

    .. py:method:: post_facebook_registration(request)

        This method is called after registering with Facebook

    .. py:method:: get_offline_graph()

        Returns an :py:mod:`open_facebook.api.OpenFacebook` API client,
        instantiated with the ``access_token`` stored in the user's profile.


.. py:class:: FacebookUser(django.db.models.Model)

    Model used to store user friends information.
    
    **Fields**::
    
        user_id = models.IntegerField()
        facebook_id = models.BigIntegerField()
        name = models.TextField(blank=True, null=True)

    .. py:attribute:: user_id
    
        An ``IntegerField`` containing the user's ID.
        
        This is a plain integer with no ForeignKey associated, in order
        to easily move this table to an external database, as per
        author needs.

    .. py:attribute:: facebook_id
    
        A ``BigIntegerField`` containing the user's Facebook ID.
    
    .. py:attribute:: name
    
        The full name of the user, as seen on Facebook.


.. py:class:: FacebookLike(django.db.models.Model)

    Model used to store Facebook "likes" of an user.

    **Fields**::
    
        user_id = models.IntegerField()
        facebook_id = models.BigIntegerField()
        name = models.TextField(blank=True, null=True)
        category = models.TextField(blank=True, null=True)
        created_time = models.DateTimeField(blank=True, null=True)
