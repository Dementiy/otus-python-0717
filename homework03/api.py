import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler
from scoring import get_score, get_interests
import store


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


class Field:
    empty_values = (None, '', [], (), {})

    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable

    def validate(self, value):
        if value is None and self.required:
            raise ValueError("Это поле является обязательным")
        if value in self.empty_values and not self.nullable:
            raise ValueError("Это поле не может быть пустым")

    def run_validator(self, value):
        pass

    def to_python(self, value):
        return value

    def clean(self, value):
        value = self.to_python(value)
        self.validate(value)
        if value in self.empty_values:
            return value
        self.run_validator(value)
        return value


class CharField(Field):
    
    def to_python(self, value):
        if value is not None and not isinstance(value, str):
            raise TypeError("Это поле должно быть строкой")
        return value


class ArgumentsField(Field):

    def to_python(self, value):
        if value is not None and not isinstance(value, dict):
            raise TypeError("Это поле должно быть словарем")
        return value


class EmailField(CharField):
    
    def run_validator(self, value):
        super().run_validator(value)
        if "@" not in value:
            raise ValueError("Неверно указан адрес электронной почты")


class PhoneField(Field):

    def to_python(self, value):
        if value is None:
            return value
        if not isinstance(value, (str, int)):
            raise TypeError("Это поле должно быть задано числом или строкой")
        return str(value)
    
    def run_validator(self, value):
        try:
            int(value)
        except ValueError:
            raise ValueError("Это поле должно содержать только цифры")
        
        if not value.startswith("7") or len(value) != 11:
            raise ValueError("Неверно указан номер телефона")


class DateField(CharField):

    def to_python(self, value):
        value = super().to_python(value)
        if value in self.empty_values:
            return value
        try:
            return self.strptime(value, "%d.%m.%Y")
        except ValueError:
            raise ValueError("Дата должна иметь формат DD.MM.YYYY")
    
    def strptime(self, value, format):
        return datetime.datetime.strptime(value, format).date()


class BirthDayField(DateField):
    
    def run_validator(self, value):
        super().run_validator(value)
        today = datetime.date.today()
        delta = today - value
        if delta.days / 365.25  > 70:
            raise ValueError("С даты рождения должно пройти не более 70 лет")


class GenderField(Field):

    def to_python(self, value):
        if value is not None and not isinstance(value, int):
            raise TypeError("Это поле должно быть целым положительным числом")
        return value
    
    def run_validator(self, value):
        if value not in GENDERS:
            raise ValueError("Пол должен быть задан значениями 0,1 или 2")


class ClientIDsField(Field):

    def to_python(self, value):
        if value is not None:
            if not isinstance(value, list) or not all(isinstance(v, int) for v in value):
                raise TypeError("Это поле должно содержать спискок целых чисел")
        return value
    
    def run_validator(self, value):
         if not all(v >=0 for v in value):
             raise ValueError("Это поле должно состоять из положительных целых чисел")


class RequestMeta(type):

    def __new__(cls, name, bases, namespace):
        fields = {
            filed_name: field
            for filed_name, field in namespace.items()
            if isinstance(field, Field)
        }

        new_namespace = namespace.copy()
        for filed_name in fields:
            del new_namespace[filed_name]
        new_namespace["_fields"] = fields
        return super().__new__(cls, name, bases, new_namespace)


class Request(metaclass=RequestMeta):

    def __init__(self, data=None):
        self._errors = None
        self.data = {} if not data else data
        self.non_empty_fields = []
    
    @property
    def errors(self):
        if self._errors is None:
            self.validate()
        return self._errors
    
    def is_valid(self):
        return not self.errors
    
    def validate(self):
        self._errors = {}

        for name, field in self._fields.items():
            try:
                value = self.data.get(name)
                value = field.clean(value)
                setattr(self, name, value)
                if value not in field.empty_values:
                    self.non_empty_fields.append(name)
            except (TypeError, ValueError) as e:
                self._errors[name] = str(e)


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
        super().validate()
        if not self._errors:
            if self.phone and self.email: return
            if self.first_name and self.last_name: return
            if self.gender is not None and self.birthday: return
            self._errors["arguments"] = "Неверный список аргументов"


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


class OnlineScoreHandler:

    def process_request(self, request, context, store):
        r = OnlineScoreRequest(request.arguments)
        if not r.is_valid():
            return r.errors, INVALID_REQUEST
        
        if request.is_admin:
            score = 42
        else:
            score = get_score(store, r.phone, r.email, r.birthday, r.gender, r.first_name, r.last_name)
        context["has"] = r.non_empty_fields
        return {"score": score}, OK


class ClientsInterestsHandler:

    def process_request(self, request, context, store):
        r = ClientsInterestsRequest(request.arguments)
        if not r.is_valid():
            return r.errors, INVALID_REQUEST
        
        context["nclients"] = len(r.client_ids)
        response_body = {cid: get_interests(store, cid) for cid in r.client_ids}
        return response_body, OK


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(bytes(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT, "utf-8")).hexdigest()
    else:
        digest = hashlib.sha512(bytes(request.account + request.login + SALT, "utf-8")).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    handlers = {
        "online_score": OnlineScoreHandler,
        "clients_interests": ClientsInterestsHandler
    }

    method_request = MethodRequest(request["body"])
    if not method_request.is_valid():
        return method_request.errors, INVALID_REQUEST
    if not check_auth(method_request):
        return "Forbidden", FORBIDDEN
    
    handler = handlers[method_request.method]()
    return handler.process_request(method_request, ctx, store)


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = store.Storage(store.RedisStorage())

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            data_string = data_string.decode("utf-8")
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
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
        self.wfile.write(bytes(json.dumps(r), "utf-8"))
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
