from django.conf.urls import url

from .views import IndexView, SearchView
from .views import ask

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^ask/?$', ask, name='ask'),
    url(r'^search/?$', SearchView.as_view(), name='search'),
]
