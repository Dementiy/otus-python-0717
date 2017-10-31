# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import operator

from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import ListView, DetailView
from django.views.generic.detail import BaseDetailView
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction

from .models import Question, Answer, Tag
from .forms import QuestionForm, AnswerForm, SearchForm


class IndexView(ListView):
    model = Question
    template_name = 'qa/index.html'
    context_object_name = 'questions'
    paginate_by = 5

    def get_queryset(self):
        order = self.request.GET.get('order')
        queryset = Question.objects.\
            select_related('author').\
            prefetch_related('answers').\
            prefetch_related('tags').all()
        if order:
            queryset = queryset.order_by('-total_votes')
        return queryset


class SearchView(IndexView):

    def get_queryset(self):
        q = self.request.GET.get('q')
        queryset = Question.objects.none()
        if not q:
            return queryset
        form = SearchForm(self.request.GET)
        if form.is_valid():
            query = form.cleaned_data['q']
            if query.startswith('tag:'):
                query_list = query[4:].split(',')
                queryset = Question.objects.search_by_tags(query_list)
            else:
                query_list = query.split()
                queryset = Question.objects.search(query_list)
            queryset = queryset.\
                select_related('author').\
                prefetch_related('answers').\
                prefetch_related('tags')
        return queryset


@login_required()
@require_http_methods(["GET", "POST"])
def ask(request):
    form = QuestionForm(request.POST or None)
    if form.is_valid():
        question = form.save(commit=False)
        question.author = request.user
        tags_list = form.cleaned_data['tags']
	with transaction.atomic():
            question.save(tags_list=tags_list)
        return redirect(reverse("qa:question", kwargs={
            "slug": question.slug,
            "pk": question.pk
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
        answers = question.answers.\
            select_related('author').\
            select_related('author__profile').\
            order_by('-total_votes', '-created_at')

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

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        self.object = question = self.get_object()

        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.author = request.user
            answer.question = question
            answer.save()
            question.notify_author(request)
            return redirect(reverse('qa:question', kwargs={
                "slug": question.slug,
                "pk": question.pk
            }))
        else:
            # TODO: Add 'form' to context for display errors
            context = self.get_context_data()
            return self.render_to_response(context)


class JsonVote(LoginRequiredMixin, BaseDetailView):

    def post(self, request, *args, **kwargs):
        value = int(request.POST.get("value"))
        obj = self.get_object()
        obj.vote(request.user, value)
        return JsonResponse({
            "votes": obj.total_votes
        })


class JsonQuestionVote(JsonVote):
    model = Question


class JsonAnswerVote(JsonVote):
    model = Answer


class JsonAnswerMark(LoginRequiredMixin, BaseDetailView):
    model = Answer

    def post(self, request, *args, **kwargs):
        answer = self.get_object()
        marked = answer.mark()
        return JsonResponse({
            "mark": marked
        })

