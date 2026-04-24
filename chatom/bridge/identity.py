"""Cross-backend user identity mapper.

Maps users across chat platforms using email as the primary join key.
Supports manual linking, automatic discovery, and cached resolution.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import Field

from chatom.base import BaseModel, User

log = logging.getLogger(__name__)

# Type alias for a backend-qualified user reference
UserRef = Tuple[str, str]  # (backend_name, user_id)

__all__ = ("IdentityMapper",)


class LinkedIdentity(BaseModel):
    """A set of linked user identities across backends.

    Each identity group represents the same person on different platforms,
    keyed by ``(backend_name, user_id)`` pairs.

    Attributes:
        email: The shared email address (if known).
        refs: Set of ``(backend, user_id)`` tuples.
        users: Cached User objects keyed by backend name.
    """

    email: str = Field(default="", description="Shared email address.")
    refs: Set[UserRef] = Field(default_factory=set, description="(backend, user_id) pairs.")
    users: Dict[str, User] = Field(default_factory=dict, description="Cached User objects by backend.")

    model_config = {"arbitrary_types_allowed": True}

    def has_backend(self, backend: str) -> bool:
        """Check if this identity has a mapping for the given backend."""
        return any(b == backend for b, _ in self.refs)

    def get_ref(self, backend: str) -> Optional[str]:
        """Get the user ID for a specific backend, or None."""
        for b, uid in self.refs:
            if b == backend:
                return uid
        return None

    def get_user(self, backend: str) -> Optional[User]:
        """Get the cached User object for a backend, or None."""
        return self.users.get(backend)

    def add(self, backend: str, user_id: str, user: Optional[User] = None) -> None:
        """Add a backend reference to this identity group."""
        self.refs.add((backend, user_id))
        if user is not None:
            self.users[backend] = user
            if not self.email and user.email:
                self.email = user.email


class IdentityMapper:
    """Maps user identities across chat backends.

    Uses email as the primary join key.  Backends are registered so
    the mapper can perform ``fetch_user(email=...)`` lookups.

    Example::

        mapper = IdentityMapper()
        mapper.register_backend("slack", slack_backend)
        mapper.register_backend("symphony", symphony_backend)

        # Auto-discover a user on all backends by email
        await mapper.link_by_email("alice@company.com")

        # Resolve from one backend to another
        sym_user = await mapper.resolve(slack_user, target="symphony")

        # Manual link
        mapper.link(slack_user, symphony_user, by="email")
    """

    def __init__(self) -> None:
        self._backends: Dict[str, Any] = {}  # name -> BackendBase
        self._identities: List[LinkedIdentity] = []
        # Fast lookup indexes
        self._by_ref: Dict[UserRef, LinkedIdentity] = {}  # (backend, uid) -> identity
        self._by_email: Dict[str, LinkedIdentity] = {}  # email -> identity

    def register_backend(self, name: str, backend: Any) -> None:
        """Register a backend for user lookups.

        Args:
            name: Short identifier (e.g. ``"slack"``, ``"symphony"``).
            backend: A chatom ``BackendBase`` instance.
        """
        self._backends[name] = backend

    @property
    def backends(self) -> List[str]:
        """List of registered backend names."""
        return list(self._backends.keys())

    def link(
        self,
        *users: User,
        by: str = "email",
        backends: Optional[List[str]] = None,
    ) -> LinkedIdentity:
        """Manually link User objects as the same person.

        Args:
            *users: Two or more User objects from different backends.
            by: The field to use as the join key (currently only ``"email"``).
            backends: Optional list of backend names corresponding to each user.
                      If not provided, uses ``user.metadata.get("backend")`` or
                      the user's class name as a fallback.

        Returns:
            The linked identity group.

        Raises:
            ValueError: If fewer than 2 users or join key is missing.
        """
        if len(users) < 2:
            raise ValueError("link() requires at least 2 users")

        # Determine backend names
        if backends:
            if len(backends) != len(users):
                raise ValueError("backends list must match number of users")
            names = backends
        else:
            names = [self._infer_backend(u) for u in users]

        # Find or create identity group
        identity: Optional[LinkedIdentity] = None

        # Check if any user already belongs to a group
        for name, user in zip(names, users):
            ref = (name, user.id)
            if ref in self._by_ref:
                identity = self._by_ref[ref]
                break

        # Check by email
        if identity is None and by == "email":
            for user in users:
                if user.email and user.email in self._by_email:
                    identity = self._by_email[user.email]
                    break

        if identity is None:
            identity = LinkedIdentity()
            self._identities.append(identity)

        # Add all users
        for name, user in zip(names, users):
            identity.add(name, user.id, user)
            self._by_ref[(name, user.id)] = identity
            if user.email:
                self._by_email[user.email] = identity

        return identity

    async def link_by_email(self, email: str) -> Optional[LinkedIdentity]:
        """Discover and link a user across all registered backends by email.

        Queries each registered backend with ``fetch_user(email=...)``.
        If found on 2+ backends, links them into an identity group.

        Args:
            email: The email address to search for.

        Returns:
            The linked identity group, or None if found on fewer than 2 backends.
        """
        # Check if we already have this email
        if email in self._by_email:
            identity = self._by_email[email]
        else:
            identity = LinkedIdentity(email=email)

        discovered = 0
        for name, backend in self._backends.items():
            if identity.has_backend(name):
                discovered += 1
                continue
            try:
                user = await backend.fetch_user(email=email)
                if user:
                    identity.add(name, user.id, user)
                    self._by_ref[(name, user.id)] = identity
                    discovered += 1
                    log.debug(f"Found {email} on {name}: {user.id}")
            except Exception:
                log.debug(f"Could not look up {email} on {name}", exc_info=True)

        if discovered >= 2:
            self._by_email[email] = identity
            if identity not in self._identities:
                self._identities.append(identity)
            return identity

        # Still store single-backend results for future linking
        if discovered == 1:
            self._by_email[email] = identity
            if identity not in self._identities:
                self._identities.append(identity)

        return identity if discovered >= 2 else None

    async def link_all_by_email(self, emails: List[str]) -> List[LinkedIdentity]:
        """Link multiple users by email in batch.

        Args:
            emails: List of email addresses.

        Returns:
            List of successfully linked identity groups (found on 2+ backends).
        """
        results = []
        for email in emails:
            identity = await self.link_by_email(email)
            if identity is not None:
                results.append(identity)
        return results

    async def resolve(
        self,
        user: Union[User, str],
        *,
        source: str = "",
        target: str,
    ) -> Optional[User]:
        """Resolve a user from one backend to another.

        Looks up the user's identity group and returns the cached User
        for the target backend.  If not cached, attempts a backend
        lookup by email.

        Args:
            user: A User object or user ID string.
            source: The backend the user is from (required if user is a string,
                    or if the user isn't already linked).
            target: The backend to resolve to.

        Returns:
            The User on the target backend, or None if not found.
        """
        identity = self._find_identity(user, source)

        if identity is None:
            # Try to discover by email
            if isinstance(user, User) and user.email:
                identity = await self.link_by_email(user.email)
            elif isinstance(user, User) and source:
                # Fetch full user to get email
                if source in self._backends:
                    try:
                        full_user = await self._backends[source].fetch_user(user.id)
                        if full_user and full_user.email:
                            identity = await self.link_by_email(full_user.email)
                    except Exception:
                        pass

        if identity is None:
            return None

        # Check cache first
        cached = identity.get_user(target)
        if cached:
            return cached

        # Try to fetch from target backend
        target_id = identity.get_ref(target)
        if target_id and target in self._backends:
            try:
                user_obj = await self._backends[target].fetch_user(target_id)
                if user_obj:
                    identity.users[target] = user_obj
                    return user_obj
            except Exception:
                pass

        # Last resort: look up by email on target backend
        if identity.email and target in self._backends:
            try:
                user_obj = await self._backends[target].fetch_user(email=identity.email)
                if user_obj:
                    identity.add(target, user_obj.id, user_obj)
                    self._by_ref[(target, user_obj.id)] = identity
                    return user_obj
            except Exception:
                pass

        return None

    def resolve_id(
        self,
        user: Union[User, str],
        *,
        source: str = "",
        target: str,
    ) -> Optional[str]:
        """Synchronously resolve a user ID on the target backend.

        Only uses the local cache — does not make backend calls.

        Args:
            user: A User object or user ID string.
            source: The source backend.
            target: The target backend.

        Returns:
            The user ID on the target backend, or None.
        """
        identity = self._find_identity(user, source)
        if identity is None:
            return None
        return identity.get_ref(target)

    def get_identity(self, user: Union[User, str], backend: str = "") -> Optional[LinkedIdentity]:
        """Get the identity group for a user.

        Args:
            user: A User object or user ID string.
            backend: The backend name (required if user is a string).

        Returns:
            The LinkedIdentity group, or None.
        """
        return self._find_identity(user, backend)

    @property
    def identities(self) -> List[LinkedIdentity]:
        """All linked identity groups."""
        return list(self._identities)

    def clear(self) -> None:
        """Clear all mappings."""
        self._identities.clear()
        self._by_ref.clear()
        self._by_email.clear()

    def _find_identity(self, user: Union[User, str], backend: str = "") -> Optional[LinkedIdentity]:
        """Find the identity group for a user."""
        if isinstance(user, User):
            # Try by ref with explicit backend
            if backend:
                ref = (backend, user.id)
                if ref in self._by_ref:
                    return self._by_ref[ref]

            # Try by email
            if user.email and user.email in self._by_email:
                return self._by_email[user.email]

            # Try all backends
            for b in self._backends:
                ref = (b, user.id)
                if ref in self._by_ref:
                    return self._by_ref[ref]

            return None
        else:
            # user is a string ID — need backend
            if backend:
                ref = (backend, user)
                return self._by_ref.get(ref)

            # Try all backends
            for b in self._backends:
                ref = (b, user)
                if ref in self._by_ref:
                    return self._by_ref[ref]
            return None

    def _infer_backend(self, user: User) -> str:
        """Infer the backend name from a User object.

        Checks, in order:
        1. ``user.metadata["backend"]`` if present.
        2. The registered backend whose name appears in ``type(user).__name__``
           (e.g. ``SlackUser`` -> ``"slack"``).
        """
        backend = getattr(user, "metadata", {}).get("backend", "")
        if backend:
            return backend
        cls_name = type(user).__name__.lower()
        for name in self._backends:
            if name.lower() in cls_name:
                return name
        return "unknown"
