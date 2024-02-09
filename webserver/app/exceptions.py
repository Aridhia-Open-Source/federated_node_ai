from werkzeug.exceptions import HTTPException
from werkzeug.sansio.response import Response
import logging

logger = logging.getLogger('exception_handler')
logger.setLevel(logging.INFO)

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
    def __init__(self, description: str | None = None, response: Response | None = None) -> None:
        super().__init__(description, response)
        logger.info(description)
        self.description = "Unauthorized"

class KeycloakError(HTTPException):
    code = 500

class TaskImageException(HTTPException):
    code = 500
    def __init__(self, description: str | None = None, response: Response | None = None) -> None:
        super().__init__(description, response)
        logger.info(description)
        self.description = "An internal Keycloak error occurred"
