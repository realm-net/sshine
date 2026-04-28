"""
This module provides integration with Beszel (https://beszel.dev).

It allows sshine to connect to Beszel instances and retrieve
monitoring data for managed servers, including system metrics,
health status, and resource usage.

The integration enables:
- fetching real-time server metrics
- linking servers to their Beszel monitors
- exposing monitoring data directly in the sshine CLI
- unifying access management and observability in a single workflow

Designed to be lightweight and optional, this integration
seamlessly extends sshine with monitoring capabilities
without introducing additional complexity.
"""
