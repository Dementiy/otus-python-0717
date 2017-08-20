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


@python_2_unicode_compatible
class Question(TimestampedModel):
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

    def __str__(self):
        return self.title


@python_2_unicode_compatible
class Answer(TimestampedModel):
    text = models.TextField()
    author = models.ForeignKey(User, related_name="answers", on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name="answers", on_delete=models.CASCADE)
    answer = models.BooleanField(default=False)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.text

