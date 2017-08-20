# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.encoding import python_2_unicode_compatible
from django.shortcuts import reverse


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
        return self.order_by('-votes', '-created_at')[:5]


class VotableMixin(object):

    def vote(self, user, value):
        if user == self.author:
            return None
        vote, created = self.get_vote_object(user)
        if created:
            vote.value = True if value > 0 else False
            vote.save()
            self.votes += value
            self.save()
        elif vote.value != (True if value > 0 else False):
            vote.delete()
            self.votes += value
            self.save()


@python_2_unicode_compatible
class Question(VotableMixin, TimestampedModel):
    slug = models.SlugField(max_length=254)
    title = models.CharField(max_length=254)
    text = models.TextField()
    author = models.ForeignKey(User, related_name="questions", on_delete=models.CASCADE)
    votes = models.IntegerField(default=0)
    answered = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, related_name='questions')
    objects = QuestionManager()

    def save(self, *args, **kwargs):
        if not self.id:
            self.slug = slugify(self.title)
        super(Question, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("qa:question", kwargs={
            "slug": self.slug,
        })

    def get_vote_object(self, user):
        return QuestionVote.objects.get_or_create(user=user, question=self)

    def __str__(self):
        return self.title


@python_2_unicode_compatible
class Answer(VotableMixin, TimestampedModel):
    text = models.TextField()
    author = models.ForeignKey(User, related_name="answers", on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name="answers", on_delete=models.CASCADE)
    answer = models.BooleanField(default=False)
    votes = models.IntegerField(default=0)

    def get_vote_object(self, user):
        return AnswerVote.objects.get_or_create(user=user, answer=self)

    def __str__(self):
        return self.text


class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value = models.BooleanField(default=True)

    class Meta:
        abstract = True


class QuestionVote(Vote):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)


class AnswerVote(Vote):
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE)

