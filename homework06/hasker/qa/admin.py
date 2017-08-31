# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Question, Answer, Tag, Vote


@admin.register(Question)
class QuestionModelAdmin(admin.ModelAdmin):
    readonly_fields = ('slug', 'total_votes', 'answered')


@admin.register(Answer)
class AnswerModelAdmin(admin.ModelAdmin):
    readonly_fields = ('total_votes', 'answer')


admin.site.register(Tag)
admin.site.register(Vote)

