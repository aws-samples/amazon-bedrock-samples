from .invalid_row_exception import InvalidRowException


class MissingKeyException(InvalidRowException):
    def __init__(self, key, index):
        message = f"The '{key.args[0]}' key is missing in the input row."
        super().__init__(message=message, index=index)
