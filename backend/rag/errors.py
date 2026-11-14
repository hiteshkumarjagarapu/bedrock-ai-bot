from botocore.exceptions import BotoCoreError, ClientError


class AWSServiceError(Exception):
    """Friendly wrapper around AWS errors with an HTTP status code."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def translate_aws_error(exc: Exception) -> AWSServiceError:
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        msg = exc.response.get("Error", {}).get("Message", str(exc))
        if code in {"ThrottlingException", "TooManyRequestsException", "ServiceQuotaExceededException"}:
            return AWSServiceError("AWS Bedrock is throttling requests. Please retry shortly.", 429)
        if code in {"AccessDeniedException", "UnrecognizedClientException", "ExpiredTokenException"}:
            return AWSServiceError(f"AWS access denied: {msg}", 502)
        if code == "ValidationException":
            return AWSServiceError(f"AWS rejected the request: {msg}", 400)
        if code == "ResourceNotFoundException":
            return AWSServiceError(f"AWS model not found or not enabled: {msg}", 502)
        return AWSServiceError(f"AWS error ({code}): {msg}", 502)
    if isinstance(exc, BotoCoreError):
        return AWSServiceError(f"AWS connection error: {exc}", 503)
    return AWSServiceError(str(exc), 500)
