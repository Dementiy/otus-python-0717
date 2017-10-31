# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import operator

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.encoding import python_2_unicode_compatible
from django.shortcuts import reverse
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from django.db import transaction
from django.contrib.postgres.search import SearchVector, SearchQuery

from .utils import notify_user_by_email


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ('-created_at', '-updated_at')


@python_2_unicode_compatible
class Tag(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name


class QuestionManager(models.Manager):

    def trending(self):
        return self.order_by('-total_votes', '-created_at')[:5]

    def search(self, query_list=[]):
        vectors = SearchVector('title') + SearchVector('text')
        terms = [SearchQuery(term) for term in query_list]
        query = reduce(operator.or_, terms)
        return self.annotate(search=vectors).filter(search=query)

    def search_by_tags(self, tags_list=[]):
        vectors = SearchVector('tags__name')
        terms = [SearchQuery(term) for term in tags_list]
        query = reduce(operator.or_, terms)
        return self.annotate(search=vectors).filter(search=query)


class VotableMixin(object):

    @transaction.atomic
    def vote(self, user, value):
        if user == self.author:
            return None
        vote, created = self.votes.get_or_create(user=user)
        if created:
            vote.value = True if value > 0 else False
            vote.save()
            self.total_votes += value
            self.save()
            return vote
        elif vote.value != (True if value > 0 else False):
            vote.delete()
            self.total_votes += value
            self.save()
            return vote
        return None


@python_2_unicode_compatible
class Question(VotableMixin, TimestampedModel):
    slug = models.SlugField(max_length=254)
    title = models.CharField(max_length=254)
    text = models.TextField()
    author = models.ForeignKey(User, related_name="questions", on_delete=models.CASCADE)
    votes = GenericRelation('Vote', related_name='questions')
    total_votes = models.IntegerField(default=0)
    answered = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, related_name='questions')
    objects = QuestionManager()

    def save(self, tags_list=[], *args, **kwargs):
        if not self.id:
            self.slug = slugify(self.title)
        super(Question, self).save(*args, **kwargs)
        tags = []
        for tag_name in tags_list:
            tag, created = Tag.objects.get_or_create(name=tag_name)
            tags.append(tag)
        self.tags.add(*tags)

    def get_absolute_url(self):
        return reverse("qa:question", kwargs={
            "slug": self.slug,
            "pk": self.pk,
        })

    def notify_author(self, request):
        notify_user_by_email(self, request)

    def __str__(self):
        return self.title


@python_2_unicode_compatible
class Answer(VotableMixin, TimestampedModel):
    text = models.TextField()
    author = models.ForeignKey(User, related_name="answers", on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name="answers", on_delete=models.CASCADE)
    answer = models.BooleanField(default=False)
    votes = GenericRelation('Vote', related_name='answers')
    total_votes = models.IntegerField(default=0)

    @transaction.atomic
    def mark(self):
        if self.question.answered and self.answer:
            self.question.answered = False
            self.answer = not self.answer
            self.question.save()
            self.save()
            return True
        elif not self.question.answered:
            self.question.answered = True
            self.answer = True
            self.question.save()
            self.save()
            return True
        return False

    def __str__(self):
        return self.text


class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value = models.BooleanField(default=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

