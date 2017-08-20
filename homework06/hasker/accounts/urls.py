from django.conf.urls import url

from .views import signup

urlpatterns = [
    url(r'^signup/$', signup, name='signup'),
]
