from typing import Any


class AppError(Exception):
    """Expected application error with a safe public representation."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.public_message = message
        self.details = details or {}


class ConfigurationError(AppError):
    status_code = 503
    code = "configuration_error"


class ExternalServiceError(AppError):
    status_code = 502
    code = "external_service_error"


class AuthenticationError(ExternalServiceError):
    status_code = 503
    code = "external_authentication_failed"


class RateLimitError(ExternalServiceError):
    status_code = 503
    code = "external_rate_limited"


class CRMValidationError(ExternalServiceError):
    status_code = 422
    code = "crm_validation_failed"


class LLMOutputError(ExternalServiceError):
    code = "llm_output_invalid"


class RecordNotFoundError(AppError):
    status_code = 404
    code = "record_not_found"
