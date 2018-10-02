import unittest
import functools
import datetime as dt

import api


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)
        return wrapper
    return decorator


class TestCharField(unittest.TestCase):

    @cases(['test', '', None])
    def test_valid_value(self, value):
        self.assertEqual(value, api.CharField().to_python(value))
        self.assertEqual(value, api.CharField(nullable=True).clean(value))
    
    @cases([0])
    def test_invalid_value(self, value):
        with self.assertRaises(TypeError):
            api.CharField().to_python(value)


class TestArgumentsField(unittest.TestCase):

    @cases([{'test': None}, {}, None])
    def test_valid_value(self, value):
        self.assertEqual(value, api.ArgumentsField().to_python(value))
        self.assertEqual(value, api.ArgumentsField(nullable=True).clean(value))
    
    @cases([0])
    def test_invalid_value(self, value):
        with self.assertRaises(TypeError):
            api.ArgumentsField().to_python(value)


class TestEmailField(TestCharField):
    
    @cases(['user@example.com', '@'])
    def test_valid_email_address(self, value):
        self.assertIsNone(api.EmailField().run_validator(value))
    
    @cases(['user', ''])
    def test_invalid_email_address(self, value):
        with self.assertRaises(ValueError):
            api.EmailField().run_validator(value)


class TestPhoneField(unittest.TestCase):

    @cases([79991234567, '79991234567'])
    def test_valid_value(self, value):
        self.assertIn(api.PhoneField().to_python(value), str(value))
        self.assertIn(api.PhoneField().clean(value), str(value))
    
    @cases([7.9991234567])
    def test_invalid_value(self, value):
        with self.assertRaises(TypeError):
            api.PhoneField().to_python(value)
    
    @cases(['79991234567', 79991234567])
    def test_valid_phone_number(self, value):
        self.assertIsNone(api.PhoneField().run_validator(str(value)))
    
    @cases([None, '', '7999123456', '9991234567', 7999123456, 9991234567, '7abcdefghij'])
    def test_invalid_phone_number(self, value):
        with self.assertRaises(ValueError):
            api.PhoneField().clean(value)


class TestDateField(unittest.TestCase):

    @cases(['21.09.2018'])
    def test_valid_value(self, value):
        self.assertIsInstance(api.DateField().to_python(value), dt.date)
        self.assertIsInstance(api.DateField().clean(value), dt.date)
    
    @cases([21092018])
    def test_invalid_value(self, value):
        with self.assertRaises(TypeError):
            api.DateField().to_python(value)


class TestBirthDayField(unittest.TestCase):

    @cases(['21.09.2018'])
    def test_valid_value(self, value):
        self.assertIsInstance(api.BirthDayField().to_python(value), dt.date)
        self.assertIsInstance(api.BirthDayField().clean(value), dt.date)
    
    @cases([21092018])
    def test_invalid_value(self, value):
        with self.assertRaises(TypeError):
            api.BirthDayField().to_python(value)
    
    @cases([dt.datetime.today().date()])
    def test_valid_bdate(self, value):
        self.assertIsNone(api.BirthDayField().run_validator(value))
    
    @cases([dt.datetime.today().date()])
    def test_invalid_bdate(self, value):
        max_days = 365.25 * 70 + 1
        value = value - dt.timedelta(max_days)
        with self.assertRaises(ValueError):
            api.BirthDayField().run_validator(value)


class TestGenderField(unittest.TestCase):

    @cases([0, 1, 2, None])
    def test_valid_value(self, value):
        self.assertEqual(value, api.GenderField().to_python(value))
        self.assertEqual(value, api.GenderField(nullable=True).clean(value))
    
    @cases(['0'])
    def test_invalid_value(self, value):
        with self.assertRaises(TypeError):
            api.GenderField().to_python(value)

    @cases([0, 1, 2, None])
    def test_valid_gender(self, value):
        self.assertIsNone(api.GenderField().run_validator(value))
    
    @cases([-1, 3])
    def test_valid_gender(self, value):
        with self.assertRaises(ValueError):
            api.GenderField().run_validator(value)


class TestClientIDsField(unittest.TestCase):

    @cases([[0, 1, 2], [], None])
    def test_valid_value(self, value):
        self.assertEqual(value, api.ClientIDsField().to_python(value))
        self.assertEqual(value, api.ClientIDsField(nullable=True).clean(value))

    @cases([[None]])
    def test_invalid_value(self, value):
        with self.assertRaises(TypeError):
            api.ClientIDsField().to_python(value)

    @cases([[0, -1, 2]])
    def test_invalid_client_ids(self, value):
        with self.assertRaises(ValueError):
            api.ClientIDsField().run_validator(value)


if __name__ == "__main__":
    unittest.main()