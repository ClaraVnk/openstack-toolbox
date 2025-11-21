#!/usr/bin/env python3
"""
Custom exceptions for OpenStack Toolbox.

This module defines specific exceptions to replace generic Exception catches
and improve error handling throughout the application.
"""


class OpenStackToolboxError(Exception):
    """Base exception for all OpenStack Toolbox errors."""

    pass


class ConfigurationError(OpenStackToolboxError):
    """Raised when there's a configuration error."""

    pass


class CredentialsError(ConfigurationError):
    """Raised when OpenStack credentials are missing or invalid."""

    pass


class SMTPConfigError(ConfigurationError):
    """Raised when SMTP configuration is missing or invalid."""

    pass


class ConnectionError(OpenStackToolboxError):
    """Raised when connection to OpenStack fails."""

    pass


class AuthenticationError(OpenStackToolboxError):
    """Raised when authentication to OpenStack fails."""

    pass


class ResourceNotFoundError(OpenStackToolboxError):
    """Raised when a requested resource is not found."""

    pass


class MetricsCollectionError(OpenStackToolboxError):
    """Raised when metrics collection fails."""

    pass


class GnocchiError(MetricsCollectionError):
    """Raised when Gnocchi API operations fail."""

    pass


class BillingError(OpenStackToolboxError):
    """Raised when billing data retrieval fails."""

    pass


class ParsingError(OpenStackToolboxError):
    """Raised when parsing data fails."""

    pass


class FileOperationError(OpenStackToolboxError):
    """Raised when file operations fail."""

    pass
