from django.conf.urls import url, include
from rest_framework.urlpatterns import format_suffix_patterns

from .views import (
    IndexAPIView, TrendingAPIView, SearchAPIView, AnswersAPIView,
    LoginAPIView, QuestionVoteAPIView, AnswerVoteAPIView,
)

urlpatterns = [
    url(regex=r"^$",
        view=IndexAPIView.as_view(),
        name="questions"),
    url(regex=r"^trending/$",
        view=TrendingAPIView.as_view(),
        name="trending"),
    url(regex=r'^search/?$',
        view=SearchAPIView.as_view(),
        name="search"),
    url(regex=r"^questions/(?P<pk>[0-9]+)/answers/$",
        view=AnswersAPIView.as_view(),
        name="answers"),
    url(regex=r"^questions/(?P<pk>[0-9]+)/vote/$",
        view=QuestionVoteAPIView.as_view(),
        name="question_vote"),
    url(regex=r"^answers/(?P<pk>[0-9]+)/vote/$",
        view=AnswerVoteAPIView.as_view(),
        name="answer_vote"),
    url(regex=r"^login/?$",
        view=LoginAPIView.as_view(),
        name="login"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
