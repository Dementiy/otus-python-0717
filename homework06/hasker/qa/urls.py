from django.conf.urls import url

from .views import IndexView, SearchView, QuestionView
from .views import ask

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^question/(?P<slug>[-\w]+)/?$', QuestionView.as_view(), name='question'),
    url(r'^ask/?$', ask, name='ask'),
    url(r'^search/?$', SearchView.as_view(), name='search'),
]
