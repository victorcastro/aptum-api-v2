from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aptum.common.enums import AuditAction, AuditEntity
from aptum.core.exceptions import ConflictError, NotFoundError
from aptum.core.permissions import Actor
from aptum.modules.audit.service import AuditService, diff, snapshot
from aptum.modules.commons.models import Degree
from aptum.modules.commons.policy import canonical_level, clean_degree_name, place
from aptum.modules.commons.repository import CommonsRepository
from aptum.modules.commons.schemas import DegreeCreate, DegreeUpdate

DEGREE_FIELDS = ("name", "level", "rank")
IN_USE = "Degree is in use by educations"


class CommonsService:
    """Writes on the degree catalog. `degree:manage` is checked by the router."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CommonsRepository(db)
        self.audit = AuditService(db)

    def create_degree(self, actor: Actor, data: DegreeCreate) -> Degree:
        degrees = self.repository.list_degrees()
        name = clean_degree_name(data.name, degrees)
        level = canonical_level(data.level, {degree.level for degree in degrees})
        degree = self.repository.create_degree(name, level)
        self.repository.renumber_degrees(place(degrees, degree))
        self.audit.record(
            actor.id,
            AuditAction.degree_create,
            AuditEntity.degree,
            degree.id,
            diff({}, snapshot(degree, DEGREE_FIELDS)),
        )
        return self._commit(degree)

    def update_degree(self, actor: Actor, degree_id: int, data: DegreeUpdate) -> Degree:
        degree = self._get(degree_id)
        degrees = self.repository.list_degrees()
        others = [other for other in degrees if other.id != degree.id]
        before = snapshot(degree, DEGREE_FIELDS)
        if data.name is not None:
            degree.name = clean_degree_name(data.name, others, degree.id)
        if data.level is not None:
            degree.level = canonical_level(data.level, {other.level for other in others})
        if degree.level != before["level"]:
            self.repository.renumber_degrees(place(others, degree))
        changes = diff(before, snapshot(degree, DEGREE_FIELDS))
        if not changes:
            return degree
        self.audit.record(actor.id, AuditAction.degree_update, AuditEntity.degree, degree.id, changes)
        return self._commit(degree)

    def delete_degree(self, actor: Actor, degree_id: int) -> None:
        degree = self._get(degree_id)
        if self.repository.degree_in_use(degree.id):
            raise ConflictError(IN_USE)
        self.audit.record(
            actor.id,
            AuditAction.degree_delete,
            AuditEntity.degree,
            degree.id,
            {"deleted": snapshot(degree, DEGREE_FIELDS)},
        )
        self.repository.delete_degree(degree)
        try:
            self.db.commit()
        except IntegrityError as exc:  # an education started using it meanwhile (FK RESTRICT)
            self.db.rollback()
            raise ConflictError(IN_USE) from exc

    def _get(self, degree_id: int) -> Degree:
        degree = self.repository.get_degree(degree_id)
        if degree is None:
            raise NotFoundError("Degree not found")
        return degree

    def _commit(self, degree: Degree) -> Degree:
        try:
            self.db.commit()
        except IntegrityError as exc:  # concurrent create/rename to the same name
            self.db.rollback()
            raise ConflictError("A degree with that name already exists") from exc
        self.db.refresh(degree)
        return degree
