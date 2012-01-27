"""Urls for ``django_facebook``.

By default, these urls are defined:

- ``connect/`` -> ``django_facebook.views.connect``
- ``image_upload/`` -> ``django_facebook.views.image_upload``
- ``wall_post/`` -> ``django_facebook.views.wall_post``
- ``canvas/`` -> ``django_facebook.views.canvas``

"""

from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('django_facebook.views',
    ## Endpoint for OAuth
    url(r'^oauth/$', 'fb_oauth', name='facebook_oauth'),


   url(r'^connect/$', 'connect', name='facebook_connect'),
   url(r'^image_upload/$', 'image_upload', name='facebook_image_upload'),
   url(r'^wall_post/$', 'wall_post', name='facebook_wall_post'),
   url(r'^canvas/$', 'canvas', name='facebook_canvas'),
)


## help autodiscovery a bit
#from django_facebook import admin
