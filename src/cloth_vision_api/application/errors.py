class ApplicationError(Exception):
    """Base application error."""


class NotFoundError(ApplicationError):
    pass


class ConflictError(ApplicationError):
    pass


class InvalidImageError(ApplicationError):
    pass


class UnauthorizedError(ApplicationError):
    pass
