import re
from email_validator import validate_email, EmailNotValidError
import phonenumbers

def is_valid_email(email: str) -> bool:
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False

def is_valid_phone(phone: str) -> bool:
    try:
        number = phonenumbers.parse(phone, 'RU')
        return phonenumbers.is_valid_number(number)
    except Exception:
        return False
