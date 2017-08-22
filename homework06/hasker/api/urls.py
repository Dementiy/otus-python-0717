from django.conf.urls import url, include
from rest_framework.urlpatterns import format_suffix_patterns

from .views import TrendingAPIView, AnswersAPIView, LoginAPIView

urlpatterns = [
    url(r'^trending/$', TrendingAPIView.as_view(), name="trending"),
    url(r'^question/(?P<pk>[0-9]+)/answers/$', AnswersAPIView.as_view(), name="answers"),
    url(r'^login/?$', LoginAPIView.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
