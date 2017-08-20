# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import operator

from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Question, Tag
from .forms import QuestionForm, AnswerForm


class IndexView(ListView):
    model = Question
    template_name = 'qa/index.html'
    context_object_name = 'questions'
    paginate_by = 5


class SearchView(IndexView):

    def get_queryset(self):
        queryset = Question.objects.order_by('-votes', '-created_at')
        query = self.request.GET.get('q')
        if not query:
            return Question.objects.none()
        if query.startswith('tag:'):
            queryset = queryset.filter(tags__name=query[4:])
        else:
            query_list = query.split()
            queryset = queryset.filter(
                reduce(operator.and_,
                    (Q(title__icontains=q) for q in query_list)) |
                reduce(operator.and_,
                    (Q(text__icontains=q) for q in query_list))
            )
        return queryset


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


class QuestionView(DetailView):
    model = Question
    context_object_name = 'question'
    template_name = 'qa/question.html'

    def get_context_data(self, **kwargs):
        context_data = super(QuestionView, self).get_context_data(**kwargs)
        question = self.get_object()
        answers = question.answers.order_by('-votes', '-created_at')

        paginator = Paginator(answers, 5)
        page = self.request.GET.get('page')
        try:
            answers = paginator.page(page)
        except PageNotAnInteger:
            answers = paginator.page(1)
        except EmptyPage:
            answers = paginator.page(paginator.num_pages)

        form = AnswerForm()
        context_data.update({
            "answers": answers,
            "form": form
        })

        return context_data

    def post(self, request, *args, **kwargs):
        self.object = question = self.get_object()

        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.author = request.user
            answer.question = question
            answer.save()
            return redirect(reverse('qa:question', kwargs={
                "slug": question.slug
            }))
        else:
            context = self.get_context_data()
            return self.render_to_response(context)

