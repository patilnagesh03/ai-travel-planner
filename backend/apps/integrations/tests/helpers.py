"""
Shared helpers for the integration tests.
"""

from django.core.cache import cache


class CacheClearingMixin:
    """Clears the shared cache around every test.

    The place search cache is process-wide state, not per-test state.
    Without clearing it, one test can read a result that a previous test
    cached, and the suite quietly stops being reliable.

    The hooks are ``setUpClass`` and ``tearDown`` rather than ``setUp``,
    because a test class that defines its own ``setUp`` would shadow the
    mixin's and silently disable the clearing.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cache.clear()

    def tearDown(self):
        cache.clear()

        super().tearDown()
