from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from .views import signup, profile

urlpatterns = [
    url(r'^signup/$', signup, name='signup'),
    url(r'^login/$', auth_views.LoginView.as_view(redirect_authenticated_user=True,
        template_name="accounts/login.html"), name='login'),
    url(r'^logout/$', auth_views.LogoutView.as_view(next_page=reverse_lazy('accounts:login')), name='logout'),
    url(r'^profile/$', profile, name='profile'),
]
