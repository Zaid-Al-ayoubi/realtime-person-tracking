from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    def __init__(self, resource: str, id: str | None = None):
        detail = f"{resource} not found" if id is None else f"{resource} '{id}' not found"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ValidationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class ServiceError(Exception):
    """Internal service-layer error. Should be caught and converted to HTTP error at API layer."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
