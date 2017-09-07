# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from qa.models import Question, Answer


class ViewsTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test', password='verysecret')
        self.question = Question.objects.create(title='Question 1', total_votes=2, author=self.user)
        Question.objects.create(title='Question 2', total_votes=3, author=self.user)
        Question.objects.create(title='Question 3', total_votes=1, author=self.user)
        Answer.objects.create(text='Answer 1', question=self.question, author=self.user)
        Answer.objects.create(text='Answer 2', question=self.question, author=self.user)
        Answer.objects.create(text='Answer 3', question=self.question, author=self.user)
        self.client = APIClient()

    def test_can_get_a_questions_list(self):
        response = self.client.get(reverse('api:questions'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['count'],
            Question.objects.count())

    def test_can_get_a_trending_list(self):
        response = self.client.get(reverse('api:trending'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        votes = [result['total_votes'] for result in response.json()['results']]
        self.assertEqual([3,2,1], votes)

    def test_can_get_an_answers_list(self):
        response = self.client.get(reverse('api:answers', kwargs={'pk': self.question.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], Answer.objects.count())

        response = self.client.get(reverse('api:answers', kwargs={'pk': 1000}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_question_search_returns_related_question(self):
        response = self.client.get(reverse('api:search'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.get(reverse('api:search'), {'q': '1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['results'][0]['title'], self.question.title)

    def test_only_authenticate_user_can_vote(self):
        response = self.client.post(reverse('api:question_vote', kwargs={'pk': self.question.id}),
            {'value': 1},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        bob = User.objects.create(username='bob', password='verysecret')
        self.client.force_authenticate(user=bob)
        response = self.client.post(reverse('api:question_vote', kwargs={'pk': self.question.id}),
            {'value': 1},
            format='json'
        )
        self.question.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['total_votes'], self.question.total_votes)

    def test_user_can_not_vote_for_own_questions(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('api:question_vote', kwargs={'pk': self.question.id}),
            {'value': 1},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

