from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('fbcanvas.views',
    (r'^/?$', 'home'),
)
