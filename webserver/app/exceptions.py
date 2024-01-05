from werkzeug.exceptions import HTTPException


class InvalidDBEntry(HTTPException):
    code = 500

def handle_500(e:HTTPException):
    return e.description,getattr(e, 'code', 500)


class DBError(HTTPException):
    code = 500

class DBRecordNotFoundError(HTTPException):
    code = 404
