"""
[Reserved for v2.0+]

Wingman is the server-side component of sshine.

It runs alongside your infrastructure and exposes a secure control API,
allowing the sshine CLI to interact with servers without direct SSH overhead.

Wingman is responsible for:
- executing commands and returning results
- managing users and SSH keys (including temporary access)
- providing access and system insights
- integrating with monitoring and automation workflows

Designed to be lightweight and easy to deploy, Wingman can run on any server
as a minimal, isolated service (e.g. Docker container).

Wingman acts as a secure execution layer — handling server-side operations,
while sshine remains the control interface.
"""
