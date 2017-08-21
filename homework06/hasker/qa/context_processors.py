from .models import Question

def trending(request):
    return {
        'trending': Question.objects.trending()
    }

