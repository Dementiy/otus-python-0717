# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required

from .models import Question, Tag
from .forms import QuestionForm


class IndexView(ListView):
    model = Question
    template_name = 'qa/index.html'
    context_object_name = 'questions'
    paginate_by = 5


@login_required()
def ask(request):
    form = QuestionForm(request.POST or None)
    if form.is_valid():
        question = form.save(commit=False)
        question.author = request.user
        question.save()
        tags_list = form.cleaned_data['tags'].split(',')
        for tag_name in tags_list:
            tag, created = Tag.objects.get_or_create(name=tag_name)
            question.tags.add(tag)
        return redirect(reverse("qa:question", kwargs={
            "slug": question.slug
        }))
    return render(request, "qa/ask.html", {
        "form": form
    })

