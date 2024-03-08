from werkzeug.exceptions import HTTPException
from werkzeug.sansio.response import Response
import logging

logger = logging.getLogger('exception_handler')
logger.setLevel(logging.INFO)

def exception_handler(e:HTTPException):
    return {"error": e.description}, getattr(e, 'code', 500)

class LogAndException(HTTPException):
    code = 500
    def __init__(self, description: str | None = None, code=None, response: Response | None = None) -> None:
        super().__init__(description, response)
        logger.info(description)
        self.details = description
        if code:
            self.code = code

class InvalidDBEntry(HTTPException):
    code = 500

class DBError(HTTPException):
    code = 500

class DBRecordNotFoundError(HTTPException):
    code = 404

class InvalidRequest(HTTPException):
    code = 500

class AuthenticationError(LogAndException):
    code = 401
    description = "Unauthorized"

class KeycloakError(LogAndException):
    description = "An internal Keycloak error occurred"

class TaskImageException(LogAndException):
    description = "An error occurred with the Task's docker image"

class TaskExecutionException(LogAndException):
    description = "An error occurred with the Task execution"

class KubernetesException(LogAndException):
    description = "A kubernetes error occurred. Check the logs for more info"

class AcrException(LogAndException):
    description = "Failed to communicate with the Container Registry"
