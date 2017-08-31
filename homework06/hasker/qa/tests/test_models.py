# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from qa.models import Question, Answer


class QuestionModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create(
            username='test1',
            email='test1@example.com',
            password='secret'
        )
        self.other_user = User.objects.create(
            username='test2',
            email='test2@example.com',
            password='secret'
        )

    def test_cannot_save_empty_question(self):
        question = Question(title='', text='', author=self.user)
        with self.assertRaises(ValidationError):
            question.save()
            question.full_clean()

        question = Question(title='Title', text='', author=self.user)
        with self.assertRaises(ValidationError):
            question.save()
            question.full_clean()

        question = Question(title='Title', text='Text', author=self.user)
        question.save()
        question.full_clean()
        self.assertEqual(question, Question.objects.first())

    def test_questions_with_the_same_title_have_a_different_urls(self):
        question1 = Question.objects.create(
            title='To be or not to be?',
            author=self.user)
        question2 = Question.objects.create(
            title='To be or not to be?',
            author=self.user)
        self.assertNotEqual(
            question1.get_absolute_url(),
            question2.get_absolute_url())

    def test_author_cannot_vote_for_own_question(self):
        question = Question.objects.create(
            title='To be or not to be?',
            author=self.user)
        total_votes_old = question.total_votes
        question.vote(self.user, 1)
        total_votes_new = question.total_votes
        self.assertEqual(total_votes_old, total_votes_new)

    def test_user_cannot_vote_twice(self):
        question = Question.objects.create(
            title='To be or not to be?',
            author=self.user)
        question.vote(self.other_user, 1)
        total_votes_old = question.total_votes
        question.vote(self.other_user, 1)
        total_votes_new = question.total_votes
        self.assertEqual(total_votes_old, total_votes_new)

    def test_user_can_revote(self):
        question = Question.objects.create(
            title='To be or not to be?',
            author=self.user)
        question.vote(self.other_user, 1)
        total_votes_old = question.total_votes
        question.vote(self.other_user, -1)
        question.vote(self.other_user, -1)
        total_votes_new = question.total_votes
        self.assertNotEqual(total_votes_old, total_votes_new)

    def test_trending_questions_ordering_by_created_at(self):
        question1 = Question.objects.create(
            title='Question 1', author=self.user)
        question2 = Question.objects.create(
            title='Question 2', author=self.user)
        question3 = Question.objects.create(
            title='Question 3', author=self.user)
        self.assertEqual(
            list(Question.objects.trending()),
            [question3, question2, question1]
        )

    def test_trending_questions_ordering_by_total_votes(self):
        question1 = Question.objects.create(
            title='Question 1', total_votes=2, author=self.user)
        question2 = Question.objects.create(
            title='Question 2', total_votes=1, author=self.user)
        question3 = Question.objects.create(
            title='Question 3', total_votes=3, author=self.user)
        self.assertEqual(
            list(Question.objects.trending()),
            [question3, question1, question2]
        )


class AnswerModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create(
            username='test1',
            email='test1@example.com',
            password='secret'
        )
        self.other_user = User.objects.create(
            username='test2',
            email='test2@example.com',
            password='secret'
        )
        self.question = Question.objects.create(
            title='To be or not to be?',
            author=self.user)

    def test_cannot_save_empty_answers(self):
        answer = Answer(text='',
            question=self.question, author=self.other_user)
        with self.assertRaises(ValidationError):
            answer.save()
            answer.full_clean()

        answer = Answer(text='Text',
            question=self.question, author=self.other_user)
        answer.save()
        answer.full_clean()
        self.assertEqual(answer, Answer.objects.first())

    def test_only_one_answer_can_be_marked(self):
        answer1 = Answer.objects.create(
            text='To be',
            question=self.question,
            author=self.user)
        answer2 = Answer.objects.create(
            text='Not to be',
            question=self.question,
            author=self.other_user)

        answer1.mark()
        self.assertTrue(self.question.answered)
        self.assertTrue(answer1.answer)

        answer2.mark()
        self.assertTrue(self.question.answered)
        self.assertTrue(answer1.answer)
        self.assertFalse(answer2.answer)

        answer1.mark()
        self.assertFalse(self.question.answered)

        answer2.mark()
        self.assertTrue(self.question.answered)
        self.assertFalse(answer1.answer)
        self.assertTrue(answer2.answer)

    def test_user_cannot_vote_twice(self):
        answer = Answer.objects.create(
            text='To be',
            question=self.question,
            author=self.user)
        answer.vote(self.other_user, 1)
        total_votes_old = answer.total_votes
        answer.vote(self.other_user, 1)
        total_votes_new = answer.total_votes
        self.assertEqual(total_votes_old, total_votes_new)

    def test_user_can_revote(self):
        answer = Answer.objects.create(
            text='To be',
            question=self.question,
            author=self.user)
        answer.vote(self.other_user, 1)
        total_votes_old = answer.total_votes
        answer.vote(self.other_user, -1)
        answer.vote(self.other_user, -1)
        total_votes_new = answer.total_votes
        self.assertNotEqual(total_votes_old, total_votes_new)

