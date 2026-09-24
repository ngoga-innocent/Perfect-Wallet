from django.db import IntegrityError

from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.response import Response


def custom_exception_handler(exc, context):

    response = exception_handler(exc, context)

    if response is not None:

        return Response(
            {
                "success": False,
                "message": "Validation failed.",
                "errors": response.data,
            },
            status=response.status_code,
        )

    if isinstance(exc, IntegrityError):

        return Response(
            {
                "success": False,
                "message": "Duplicate record.",
            },
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {
            "success": False,
            "message": "Internal server error.",
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )