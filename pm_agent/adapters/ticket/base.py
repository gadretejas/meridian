from abc import ABC, abstractmethod

from pm_agent.adapters.ticket.models import (
    Ticket,
    TicketDelta,
    TicketFilter,
    TicketSpec,
    TeamMember,
)


class TicketSourceAdapter(ABC):
    @abstractmethod
    async def list_tickets(self, filters: TicketFilter) -> list[Ticket]: ...

    @abstractmethod
    async def get_ticket(self, id: str) -> Ticket: ...

    @abstractmethod
    async def create_ticket(self, spec: TicketSpec) -> Ticket: ...

    @abstractmethod
    async def update_ticket(self, id: str, delta: TicketDelta) -> Ticket: ...

    @abstractmethod
    async def add_comment(self, id: str, body: str) -> None: ...

    @abstractmethod
    async def list_members(self) -> list[TeamMember]: ...
