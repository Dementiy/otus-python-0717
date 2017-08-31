# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import generics
from rest_framework import views
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from .serializers import (
    QuestionSerializer, AnswerSerializer, LoginSerializer, VoteSerializer
)
from qa.models import Question, Answer


class TrendingAPIView(generics.ListAPIView):
    """ Получить список популярных вопросов """
    queryset = Question.objects.trending()
    serializer_class = QuestionSerializer


class AnswersAPIView(generics.ListCreateAPIView):
    """ Просмотреть список ответов или добавить новый """
    serializer_class = AnswerSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get_queryset(self, *args, **kwargs):
        question_id = self.kwargs.get("pk")
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            raise NotFound()
        return question.answers.all()

    def perform_create(self, serializer):
        question_id = self.kwargs.get("pk")
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            raise NotFound()
        serializer.save(author=self.request.user, question=question)


class LoginAPIView(views.APIView):
    """ Авторизация пользователя по логину и паролю """
    serializer_class = LoginSerializer

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        data = {
            'username': username,
            'password': password
        }
        serializer = self.serializer_class(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VoteAPIView(views.APIView):
    serializer_class = VoteSerializer

    def post(self, request, pk):
        try:
            content_object = self.content_object_class.objects.get(id=pk)
        except self.content_object_class.DoesNotExist:
            raise NotFound("Object with this ID does not exist.")
        data = {
            'value': request.data.get("value")
        }
        serializer = self.serializer_class(data=data, context={
            'user': request.user,
            'content_object': content_object
        })
        serializer.is_valid(raise_exception=True)
        return Response({
            "total_votes": content_object.total_votes
        }, status=status.HTTP_201_CREATED)


class QuestionVoteAPIView(VoteAPIView):
    """ Проголосовать за вопрос """
    content_object_class = Question


class AnswerVoteAPIView(VoteAPIView):
    """ Проголосовать за ответ """
    content_object_class = Answer
