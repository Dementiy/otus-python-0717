from django.conf.urls import url

from .views import (
    IndexView, SearchView, QuestionView, JsonQuestionVote, JsonAnswerVote, JsonAnswerMark, ask
)

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^question/(?P<slug>[-\w\d]+),(?P<pk>\d+)/?$', QuestionView.as_view(), name='question'),
    url(r'^question/(?P<pk>[0-9]+)/vote/?$', JsonQuestionVote.as_view(), name='question_vote'),
    url(r'^answer/(?P<pk>[0-9]+)/vote/?$', JsonAnswerVote.as_view(), name='answer_vote'),
    url(r'^answer/(?P<pk>[0-9]+)/mark/?$', JsonAnswerMark.as_view(), name='answer_mark'),
    url(r'^ask/?$', ask, name='ask'),
    url(r'^search/?$', SearchView.as_view(), name='search'),
]
