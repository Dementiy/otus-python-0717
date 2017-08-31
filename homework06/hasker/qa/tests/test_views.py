from django.test import TestCase
from django.contrib.auth.models import User

from qa.models import Question, Tag

class SearchViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create(
            username="test",
            email="test@example.com",
            password="secret"
        )

    def test_search_questions_by_title(self):
        question1 = Question.objects.create(
            title="Question 1 title", author=self.user)
        question2 = Question.objects.create(
            title="Title of second question", author=self.user)
        question3 = Question.objects.create(
            title="No title", author=self.user)

        response = self.client.get("/search?q=title")
        self.assertEqual(
            set(response.context["questions"]),
            set([question1, question2, question3])
        )

        response = self.client.get("/search?q=question+title")
        self.assertEqual(
            set(response.context["questions"]),
            set([question1, question2])
        )

    def test_search_questions_by_tags(self):
        tag1 = Tag.objects.create(name="foo")
        tag2 = Tag.objects.create(name="bar")
        tag3 = Tag.objects.create(name="baz")

        question1 = Question.objects.create(
            title="Question 1", author=self.user)
        question1.tags.add(*[tag1, tag3])

        question2 = Question.objects.create(
            title="Question 2", author=self.user)
        question2.tags.add(tag2)

        question3 = Question.objects.create(
            title="Question 3", author=self.user)
        question3.tags.add(*[tag2, tag3])

        response = self.client.get("/search?q=tag:baz")
        self.assertEqual(
            set(response.context["questions"]),
            set([question1, question3])
        )

