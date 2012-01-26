from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    #(r'^accounts/', include('registration.backends.default.urls')),
    #(r'^facebook/', include('django_facebook.urls')),
    (r'^fbcanvas/', include('fbcanvas.urls')),
)
