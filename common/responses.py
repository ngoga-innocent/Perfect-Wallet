from rest_framework.response import Response


def normalize_errors(errors):
    """
    Convert DRF ErrorDetail objects
    into normal JSON serializable strings.
    """

    if isinstance(errors, dict):
        return {
            key: normalize_errors(value)
            for key, value in errors.items()
        }

    if isinstance(errors, list):
        return [
            normalize_errors(item)
            for item in errors
        ]

    return str(errors)


class ApiResponse:

    @staticmethod
    def success(
        message="Success",
        data=None,
        status=200,
        meta=None,
    ):
        return Response(
            {
                "success": True,
                "message": message,
                "data": data if data is not None else {},
                "errors": {},
                "meta": meta if meta is not None else {},
            },
            status=status,
        )


    @staticmethod
    def error(
        message="Something went wrong.",
        errors=None,
        status=400,
        data=None,
    ):
        return Response(
            {
                "success": False,
                "message": message,
                "data": data if data is not None else {},
                "errors": normalize_errors(errors) if errors else {},
                "meta": {},
            },
            status=status,
        )