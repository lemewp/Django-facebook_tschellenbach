# Create your views here.
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_exempt
from django_facebook.api import get_facebook_graph

@csrf_exempt
def home(request):
    
    debugmsg = ""
    fb = get_facebook_graph(request)
    if fb:
        fb_user = fb.get('me')
        debugmsg = str(fb.get('me'))
    else:
        fb_user = None
        debugmsg = "Not authenticated"
    
    return render_to_response(
        "canvas-test.html",
        dict(request=request, debug=debugmsg, fb_user=fb_user),
        context_instance=RequestContext(request))
