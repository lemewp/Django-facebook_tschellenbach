################################################################################
Django-facebook documentation
################################################################################

Django Facebook assumes you want users to register through Facebook.
After registration it gives you access to the graph, allowing for such applications as:

* Inviting friends
* Finding friends
* Posting to a users profile
* Open graph beta functionality

For a demo of the signup flow have a look at Fashiolista's landing page (`fashiolista.com <http://www.fashiolista.com/intro_wide_minimal/>`_)

Contributions are welcome!!
Contact me here or `@tschellenbach <http://www.twitter.com/tschellenbach>`_
Updates and tutorials can be found on my blog `mellowmorning <http://www.mellowmorning.com/>`_


About Django Facebook
=====================

**Features**

- Access the Facebook API, from:

  - **Your website** (Using JavaScript OAuth)
  - **Facebook canvas pages** (For building Facebook applications)
  - **Mobile** (Or any other flow giving you a valid access token)

- Django User Registration (Convert Facebook user data into a user model)
- Use Facebook data to register a user with your Django app. Facebook connect using the open graph API.
- Access to the Facebook FQL API
- OAuth 2.0 compliant
- Includes **Open Facebook** (stable and tested Python Graph API client)


About this version
==================

This version comes from the `rshk/Django-facebook`_ fork made on GitHub by
`Samuele ~redShadow~ Santi <http://www.samuelesanti.it>`_, in order to
improve support for canvas apps and some other stuff.

.. _`rshk/Django-facebook` : https://github.com/rshk/Django-facebook/


Requirements
============
* Django_ >= 1.3
* Django registration or Django Userena (contact me if you use something else for registration.) 

.. _Django : https://www.djangoproject.com/

Generated documentation
=======================

.. toctree::
   :maxdepth: 2

   readme
   src-doc/django_facebook/index
   src-doc/open_facebook/index


Recipes
=======

.. toctree::
   :maxdepth: 2

   recipes/basic_usage
   recipes/contributing


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

