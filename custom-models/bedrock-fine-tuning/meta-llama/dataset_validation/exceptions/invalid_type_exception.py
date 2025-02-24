from .invalid_row_exception import InvalidRowException


class InvalidTypeException(InvalidRowException):
    def __init__(self, index):
        super().__init__(
            "Null values and strings are not accessible. Refer to the stack trace to identify the attempted dictionary access that raised this exception.",
            index,
        )
