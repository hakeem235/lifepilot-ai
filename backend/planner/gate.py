"""The proposal → apply safety gate (Issue 10.3, D10).

10.0–10.2 each split their work across a preview call and an apply call. This
module turns that convention into something the codebase *enforces* rather than
something four files happen to agree on.

Every planner endpoint inherits from exactly one of two bases:

    ProposalEndpoint   declares `writes = False` — must not mutate user data
    ApplyEndpoint      declares `writes = True`  — the user-confirmed write path

`test_gate.py` walks the planner URLconf and fails if any endpoint doesn't
declare itself, and calls every ProposalEndpoint to assert the database is
untouched. The point is the *next* AI feature: an endpoint added in a later phase
that quietly writes from a proposal path cannot pass CI without someone
deliberately mislabelling it, which is a reviewable act rather than an oversight.

Why the proposal itself is never persisted: a stored proposal is state that can
go stale, be replayed, or be applied twice. Instead the client holds it and hands
it back, and every apply re-validates from the database as if it had never seen
the proposal before — so a tampered or stale payload can only ever do what the
user could do by hand.
"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class PlannerEndpoint(APIView):
    """Base for every planner endpoint. Authentication is not optional here."""

    permission_classes = [IsAuthenticated]
    # Subclasses must set this to True or False; the audit rejects None.
    writes: bool | None = None


class ProposalEndpoint(PlannerEndpoint):
    """An endpoint that generates a preview and must not mutate user data.

    Anything reached from here may read the user's tasks and calendar and may
    call the model, but must not create, update or delete a Task. Logging AI
    spend is not a user-data write and is expected.
    """

    writes = False


class ApplyEndpoint(PlannerEndpoint):
    """An endpoint that performs a user-confirmed write.

    Every one of these re-validates ownership and conflicts against the database
    at call time, because the proposal it is handed may be stale or edited.
    """

    writes = True


def owned_task(user, task_id: object):
    """The caller's task with this id, or None — the single ownership lookup.

    Filtering by `user` is what makes another user's id indistinguishable from a
    nonexistent one: apply paths report "not_found" and move on, leaking nothing.

    A malformed id (not a UUID) is also just None. Django raises ValidationError
    when coercing a bad UUID in a filter, which would surface as a 500 on what is
    really an invalid-input case — and these ids arrive from a client-held
    proposal, so malformed input is expected, not exceptional.
    """
    from django.core.exceptions import ValidationError

    from tasks.models import Task

    if not task_id:
        return None
    try:
        return Task.objects.filter(user=user, id=task_id).first()
    except (ValidationError, ValueError, TypeError):
        return None
