"""
Django-facebook middleware
"""

class FBCanvasMiddleware:
    def process_request(self, request):
        """Process a request from the FB canvas
        
        - Validate signed requests from Facebook
          - Login when running in canvas
          - For the deauthorize_callback ping
        - Process the requests execution when a request_ids parameter
          is passed -> redirect to somewhere
        - We should also prevent CSRF code to be checked if the request
          is using ``signed_request``.
        """
        pass
