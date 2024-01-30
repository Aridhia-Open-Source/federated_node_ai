from werkzeug.exceptions import HTTPException

def exception_handler(e:HTTPException):
    return {"error": e.description}, getattr(e, 'code', 500)


class InvalidDBEntry(HTTPException):
    code = 500

class DBError(HTTPException):
    code = 500

class DBRecordNotFoundError(HTTPException):
    code = 404

class InvalidRequest(HTTPException):
    code = 500

class AuthenticationError(HTTPException):
    code = 401
