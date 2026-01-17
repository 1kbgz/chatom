"""Integration tests for chatom backends.

These are end-to-end tests that require real credentials and human interaction.
They are designed to verify that all backend functionality works correctly
and can also be used to verify that your credentials and permissions are set up correctly.

Run individual tests as standalone scripts:
    python -m chatom.tests.integration.discord_e2e
    python -m chatom.tests.integration.slack_e2e
    python -m chatom.tests.integration.symphony_e2e
    python -m chatom.tests.integration.matrix_e2e
    python -m chatom.tests.integration.irc_e2e
    python -m chatom.tests.integration.email_e2e

See docs/src/integration-testing.md for detailed setup instructions.
"""
