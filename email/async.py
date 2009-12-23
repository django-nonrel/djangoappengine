from . import EmailBackend

class EmailBackend(EmailBackend):
    can_defer = True
