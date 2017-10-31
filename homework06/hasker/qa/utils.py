from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail


def notify_user_by_email(question, request):
    subject = "New answer on Hasker"
    message = """
    You have a new answer for your question '%s'.
    Check this link: %s
    """
    current_site = get_current_site(request)
    url = "http://%s%s" % (current_site.domain, question.get_absolute_url())
    message = message % (question.title, url)
    send_mail(subject, message, None, [question.author.email])

