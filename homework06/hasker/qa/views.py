# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.views.generic import ListView

from .models import Question


class IndexView(ListView):
    model = Question
    template_name = 'qa/index.html'
    context_object_name = 'questions'

