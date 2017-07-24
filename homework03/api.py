#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Нужно реализовать простое HTTP API сервиса скоринга. Шаблон уже есть в api.py, тесты в test.py.
# API необычно тем, что польщователи дергают методы POST запросами. Чтобы получить результат
# пользователь отправляет в POST запросе валидный JSON определенного формата на локейшн /method

# Структура json-запроса:

# {"account": "<имя компании партнера>", "login": "<имя пользователя>", "method": "<имя метода>",
#  "token": "<аутентификационный токен>", "arguments": {<словарь с аргументами вызываемого метода>}}

# account - строка, опционально, может быть пустым
# login - строка, обязательно, может быть пустым
# method - строка, обязательно, может быть пустым
# token - строка, обязательно, может быть пустым
# arguments - словарь (объект в терминах json), обязательно, может быть пустым

# Валидация:
# запрос валиден, если валидны все поля по отдельности

# Структура ответа:
# {"code": <числовой код>, "response": {<ответ вызываемого метода>}}
# {"code": <числовой код>, "error": {<сообщение об ошибке>}}

# Аутентификация:
# смотри check_auth в шаблоне. В случае если не пройдена, нужно возвращать
# {"code": 403, "error": "Forbidden"}

# Метод online_score.
# Аргументы:
# phone - строка или число, длиной 11, начинается с 7, опционально, может быть пустым
# email - строка, в которой есть @, опционально, может быть пустым
# first_name - строка, опционально, может быть пустым
# last_name - строка, опционально, может быть пустым
# birthday - дата в формате DD.MM.YYYY, с которой прошло не больше 70 лет, опционально, может быть пустым
# gender - число 0, 1 или 2, опционально, может быть пустым

# Валидация аругементов:
# аргументы валидны, если валидны все поля по отдельности и если присутсвует хоть одна пара
# phone-email, first name-last name, gender-birthday с непустыми значениями.

# Ответ:
# в ответ выдается произвольное число, которое больше или равно 0
# {"score": <число>}
# или если запрос пришел от валидного пользователя admin
# {"score": 42}
# или если произошла ошибка валидации
# {"code": 422, "error": "<сообщение о том какое поле невалидно>"}

# $ curl -X POST  -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95", "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Стансилав", "last_name": "Ступников", "birthday": "01.01.1990", "gender": 1}}' http://127.0.0.1:8080/method/
# -> {"code": 200, "response": {"score": 5.0}}

# Метод clients_interests.
# Аргументы:
# client_ids - массив числе, обязательно, не пустое
# date - дата в формате DD.MM.YYYY, опционально, может быть пустым

# Валидация аругементов:
# аргументы валидны, если валидны все поля по отдельности.

# Ответ:
# в ответ выдается словарь <id клиента>:<список интересов>. Список генерировать произвольно.
# {"client_id1": ["interest1", "interest2" ...], "client2": [...] ...}
# или если произошла ошибка валидации
# {"code": 422, "error": "<сообщение о том какое поле невалидно>"}

# $ curl -X POST  -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "admin", "method": "clients_interests", "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f24091386050205c324687a0", "arguments": {"client_ids": [1,2,3,4], "date": "20.07.2017"}}' http://127.0.0.1:8080/method/
# -> {"code": 200, "response": {"1": ["books", "hi-tech"], "2": ["pets", "tv"], "3": ["travel", "music"], "4": ["cinema", "geek"]}}

# Требование: в результате в git должно быть только два(2!) файлика: api.py, test.py.
# Deadline: следующее занятие

import abc
import json
import random
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from six import string_types
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class ValidationError(Exception):
    """ An error while validating data """
    pass


class Field(object):
    __metaclass__ = abc.ABCMeta
    empty_values = (None, (), [], {}, '')

    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable

    @abc.abstractmethod
    def validate(self, value):
        pass


class CharField(Field):
    def validate(self, value):
        if not isinstance(value, string_types):
            raise ValidationError("This field must be a string")


class ArgumentsField(Field):
    def validate(self, value):
        if not isinstance(value, dict):
            raise ValidationError("This field must be a dict")


class EmailField(CharField):
    def validate(self, value):
        super(EmailField, self).validate(value)
        if "@" not in value:
            raise ValidationError("Invalid email address")


class PhoneField(Field):
    def validate(self, value):
        if not isinstance(value, string_types) and not isinstance(value, int):
            raise ValidationError("Phone number must be numeric or string value")
        if not str(value).startswith("7"):
            raise ValidationError("Incorrect phone number format, should be 7XXXXXXXXX")


class DateField(Field):
    def validate(self, value):
        try:
            datetime.datetime.strptime(value, '%d.%m.%Y')
        except ValueError:
            raise ValidationError("Incorrect data format, should be DD.MM.YYYY")


class BirthDayField(DateField):
    def validate(self, value):
        super(BirthDayField, self).validate(value)
        bdate = datetime.datetime.strptime(value, '%d.%m.%Y')
        if datetime.datetime.now().year - bdate.year > 70:
            raise ValidationError("Incorrect birth day")


class GenderField(Field):
    def validate(self, value):
        if value not in GENDERS:
            raise ValidationError("Gender must be equal to 0,1 or 2")


class ClientIDsField(Field):
    def validate(self, values):
        if not isinstance(values, list):
            raise ValidationError("Invalid data type, must be an array")
        if not all(isinstance(v, int) and v >= 0 for v in values):
            raise ValidationError("All elements must be positive integers")


class DeclarativeFieldsMetaclass(type):
    def __new__(meta, name, bases, attrs):
        new_class = super(DeclarativeFieldsMetaclass, meta).__new__(meta, name, bases, attrs)
        fields = []
        for field_name, field in attrs.items():
            if isinstance(field, Field):
                field._name = field_name
                fields.append((field_name, field))
        new_class.fields = fields
        return new_class


class Request(object):
    __metaclass__ = DeclarativeFieldsMetaclass

    def __init__(self, **kwargs):
        self._errors = {}
        for field_name, value in kwargs.items():
            setattr(self, field_name, value)

    def validate(self):
        for name, field in self.fields:
            if name not in self.__dict__:
                if field.required:
                    self._errors[name] = "This field is required"
                continue

            value = getattr(self, name)
            if value in field.empty_values and not field.nullable:
                self._errors[name] = "This field can't be blank"

            try:
                field.validate(value)
            except ValidationError as e:
                self._errors[name] = e.message

    @property
    def errors(self):
        return self._errors

    def is_valid(self):
        return not self.errors

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            ','.join(['%s="%s"'%(name, repr(getattr(self, name))) for name, _ in self.fields])
        )


class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def validate(self):
        super(OnlineScoreRequest, self).validate()
        if not self._errors:
            field_sets = [
                ("phone", "email"),
                ("first_name", "last_name"),
                ("gender", "birthday")
            ]
            if not any(all(name in self.__dict__ for name in fields) for fields in field_sets):
                self._errors["arguments"] = "Invalid arguments list"


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=True)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.login == ADMIN_LOGIN:
        digest = hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx):
    requests = {
        "clients_interests": ClientsInterestsRequest,
        "online_score": OnlineScoreRequest,
    }

    method_request = MethodRequest(**request["body"])
    method_request.validate()

    if method_request._errors:
        return method_request._errors, INVALID_REQUEST
    if not check_auth(method_request):
        return "Forbidden", FORBIDDEN

    sub_request = requests[method_request.method](**method_request.arguments)
    sub_request.validate()
    if sub_request._errors:
        return sub_request._errors, INVALID_REQUEST

    if method_request.method == "online_score":
        ctx['has'] = method_request.arguments.keys()  # Context?
        if method_request.is_admin:
            return {"score": 42}, OK
        else:
            return {"score": random.randint(0, 100)}, OK

    if method_request.method == "clients_interests":
        ctx['nclients'] = len(sub_request.client_ids)  # Context?
        choices = ["books", "tv", "music", "it", "travel", "pets"]
        response = {}
        for client_id in sub_request.client_ids:
            response[client_id] = [random.choice(choices) for _ in range(2)]
        return response, OK

    return {}, BAD_REQUEST


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context)
                except Exception, e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r))
        return

if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
