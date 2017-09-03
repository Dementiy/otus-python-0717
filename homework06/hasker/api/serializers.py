from rest_framework import serializers
from django.contrib.auth import authenticate, login

from qa.models import Question, Answer


class AnswerSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")

    class Meta:
        model = Answer
        fields = ("text", "author", "answer", "total_votes")
        read_only_fields = ("author", "answer", "total_votes")


class QuestionSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")
    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name"
    )

    class Meta:
        model = Question
        fields = ("title", "text", "author", "total_votes", "answered", "tags")
        read_only_fields = ("author", "total_votes", "answered")


class SearchFieldsSerializer(serializers.Serializer):
    q = serializers.CharField(max_length=254)


class VoteSerializer(serializers.Serializer):
    value = serializers.IntegerField()

    def validate(self, data):
        content_object = self.context.get("content_object")
        author = self.context.get("user")
        value = data.get("value")
        vote = content_object.vote(author, value)
        if vote is None:
            raise serializers.ValidationError("You can't vote twice or for yourself.")
        return {
            "value": value
        }


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255, write_only=True)
    password = serializers.CharField(max_length=128, min_length=8, write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username is None:
            raise serializers.ValidationError('An username is required to log in.')
        if password is None:
            raise serializers.ValidationError('A password is required to log in.')

        user = authenticate(username=username, password=password)

        if user is None:
            raise serializers.ValidationError('A user with this username and password was not found.')
        if not user.is_active:
            raise serializers.ValidationError('This user has been deactivated.')

        login(self.context["request"], user)

        return {
            "username": user.username
        }

