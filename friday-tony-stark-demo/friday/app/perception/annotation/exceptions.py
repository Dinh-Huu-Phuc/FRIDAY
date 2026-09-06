class AnnotationError(RuntimeError):
    """Base error for the local visual annotation workflow."""


class AnnotationNotFoundError(AnnotationError):
    pass


class AnnotationConflictError(AnnotationError):
    pass


class AnnotationValidationError(AnnotationError):
    pass


class AnnotationUnavailableError(AnnotationError):
    pass
