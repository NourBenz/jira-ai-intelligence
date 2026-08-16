from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.database.entities import (
    ChangelogEntity,
    CommentEntity,
    IssueEntity,
    ProjectEntity,
    RAGChunkEntity,
    SprintEntity,
    SprintIssueEntity,
    SyncChangeEntity,
    SyncRunEntity,
)
from app.models.ticket import Ticket
from app.rag.chunker import RAGChunk


class JiraRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_project(self, data: dict) -> ProjectEntity:
        entity = self.session.scalar(
            select(ProjectEntity).where(ProjectEntity.jira_id == str(data["id"]))
        )
        if entity is None:
            entity = ProjectEntity(jira_id=str(data["id"]), key=data["key"], name=data["name"])
            self.session.add(entity)
        entity.key, entity.name = data["key"], data["name"]
        entity.synchronized_at = datetime.now(UTC)
        self.session.flush()
        return entity

    def upsert_issue(self, project: ProjectEntity, issue: Ticket) -> IssueEntity:
        entity = self.session.scalar(
            select(IssueEntity).where(IssueEntity.jira_id == str(issue.id))
        )
        if entity is None:
            entity = IssueEntity(jira_id=str(issue.id), key=issue.key, project=project)
            self.session.add(entity)
        entity.key, entity.project = issue.key, project
        for target, value in {
            "summary": issue.summary,
            "description": issue.description,
            "status": issue.status,
            "status_category": issue.status_category,
            "priority": issue.priority,
            "issue_type": issue.issue_type,
            "assignee": issue.assignee,
            "reporter": issue.reporter,
            "created_at": issue.created,
            "updated_at": issue.updated,
            "resolution_date": issue.resolution_date,
            "due_date": issue.due_date,
            "story_points": issue.story_points,
            "labels": issue.labels,
        }.items():
            setattr(entity, target, value)
        self.session.flush()
        return entity

    def get_issue_by_jira_id(self, jira_id: str | None) -> IssueEntity | None:
        if jira_id is None:
            return None
        return self.session.scalar(select(IssueEntity).where(IssueEntity.jira_id == str(jira_id)))

    def get_issue_by_key(self, issue_key: str) -> IssueEntity | None:
        return self.session.scalar(select(IssueEntity).where(IssueEntity.key == issue_key.upper()))

    def upsert_sprint(self, project: ProjectEntity, data: dict) -> SprintEntity:
        jira_id = int(data["id"])
        entity = self.session.scalar(select(SprintEntity).where(SprintEntity.jira_id == jira_id))
        if entity is None:
            entity = SprintEntity(jira_id=jira_id, name=data["name"], state=data["state"])
            self.session.add(entity)
        entity.project, entity.board_id = project, data.get("originBoardId")
        entity.name, entity.state, entity.goal = data["name"], data["state"], data.get("goal")
        entity.start_date = self._datetime(data.get("startDate"))
        entity.end_date = self._datetime(data.get("endDate"))
        entity.complete_date = self._datetime(data.get("completeDate"))
        self.session.flush()
        return entity

    def upsert_changelog(self, issue: IssueEntity, data: dict) -> ChangelogEntity:
        history_id = str(data["id"])
        entity = self.session.scalar(
            select(ChangelogEntity).where(
                ChangelogEntity.issue_id == issue.id,
                ChangelogEntity.jira_history_id == history_id,
            )
        )
        if entity is None:
            entity = ChangelogEntity(
                issue=issue,
                jira_history_id=history_id,
                changed_at=self._datetime(data.get("created")) or datetime.now(UTC),
                items=[],
            )
            self.session.add(entity)
        author = data.get("author") or {}
        entity.changed_at = self._datetime(data.get("created")) or entity.changed_at
        entity.author_name, entity.items = author.get("displayName"), data.get("items") or []
        return entity

    def replace_comments(self, issue: IssueEntity, comments: list[dict]) -> int:
        """Replace one issue's comment snapshot without creating duplicates."""
        incoming_ids = {str(comment["id"]) for comment in comments if comment.get("id") is not None}
        stale = delete(CommentEntity).where(CommentEntity.issue_id == issue.id)
        if incoming_ids:
            stale = stale.where(CommentEntity.jira_id.not_in(incoming_ids))
        self.session.execute(stale)

        existing = (
            {
                entity.jira_id: entity
                for entity in self.session.scalars(
                    select(CommentEntity).where(
                        CommentEntity.issue_id == issue.id,
                        CommentEntity.jira_id.in_(incoming_ids),
                    )
                )
            }
            if incoming_ids
            else {}
        )

        for comment in comments:
            if comment.get("id") is None:
                continue
            jira_id = str(comment["id"])
            entity = existing.get(jira_id)
            if entity is None:
                entity = CommentEntity(issue=issue, jira_id=jira_id)
                self.session.add(entity)
            entity.author_name = comment.get("author")
            entity.body = comment.get("body")
            entity.created_at = self._datetime(comment.get("created"))
            entity.updated_at = self._datetime(comment.get("updated"))
        self.session.flush()
        return len(incoming_ids)

    def create_sync_run(self, project_key: str, mode: str = "full") -> SyncRunEntity:
        run = SyncRunEntity(
            project_key=project_key, mode=mode, status="running", started_at=datetime.now(UTC)
        )
        self.session.add(run)
        self.session.flush()
        return run

    def list_sync_runs(
        self,
        limit: int = 20,
        project_keys: set[str] | None = None,
    ) -> list[SyncRunEntity]:
        query = select(SyncRunEntity).order_by(SyncRunEntity.id.desc()).limit(limit)
        if project_keys is not None:
            if not project_keys:
                return []
            query = query.where(SyncRunEntity.project_key.in_(project_keys))
        return list(self.session.scalars(query))

    def get_sync_run(self, run_id: int) -> SyncRunEntity | None:
        return self.session.get(SyncRunEntity, run_id)

    def get_sync_run_with_changes(self, run_id: int) -> SyncRunEntity | None:
        return self.session.scalar(
            select(SyncRunEntity)
            .options(selectinload(SyncRunEntity.changes))
            .where(SyncRunEntity.id == run_id)
        )

    def record_sync_change(
        self,
        run: SyncRunEntity,
        *,
        issue_key: str,
        change_type: str,
        changed_fields: list[str],
        before_values: dict,
        after_values: dict,
        changelogs_inspected: int,
        comments_inspected: int,
    ) -> SyncChangeEntity:
        change = SyncChangeEntity(
            sync_run=run,
            issue_key=issue_key,
            change_type=change_type,
            changed_fields=changed_fields,
            before_values=before_values,
            after_values=after_values,
            changelogs_inspected=changelogs_inspected,
            comments_inspected=comments_inspected,
        )
        self.session.add(change)
        return change

    def last_successful_sync(self, project_key: str) -> SyncRunEntity | None:
        return self.session.scalar(
            select(SyncRunEntity)
            .where(
                SyncRunEntity.project_key == project_key,
                SyncRunEntity.status == "completed",
            )
            .order_by(SyncRunEntity.completed_at.desc())
            .limit(1)
        )

    def get_project(self, project_key: str) -> ProjectEntity | None:
        return self.session.scalar(select(ProjectEntity).where(ProjectEntity.key == project_key))

    def list_project_issues(self, project_key: str) -> list[IssueEntity]:
        return list(
            self.session.scalars(
                select(IssueEntity)
                .join(ProjectEntity)
                .where(ProjectEntity.key == project_key)
                .order_by(IssueEntity.created_at.desc(), IssueEntity.key.desc())
            )
        )

    def get_project_issue(self, project_key: str, issue_key: str) -> IssueEntity | None:
        """Return one exact issue only when it belongs to the requested project."""
        return self.session.scalar(
            select(IssueEntity)
            .join(ProjectEntity)
            .where(
                ProjectEntity.key == project_key,
                IssueEntity.key == issue_key,
            )
        )

    def replace_sprint_issues(
        self,
        sprint: SprintEntity,
        tickets: list[Ticket],
    ) -> None:
        self.session.execute(
            delete(SprintIssueEntity).where(SprintIssueEntity.sprint_id == sprint.id)
        )
        jira_ids = [str(ticket.id) for ticket in tickets]
        if not jira_ids:
            return
        issues = self.session.scalars(select(IssueEntity).where(IssueEntity.jira_id.in_(jira_ids)))
        for issue in issues:
            self.session.add(SprintIssueEntity(sprint=sprint, issue=issue))

    def project_histories(self, project_key: str) -> dict[str, list[dict]]:
        rows = self.session.execute(
            select(IssueEntity.key, ChangelogEntity)
            .join(ChangelogEntity, ChangelogEntity.issue_id == IssueEntity.id)
            .join(ProjectEntity, ProjectEntity.id == IssueEntity.project_id)
            .where(ProjectEntity.key == project_key)
            .order_by(ChangelogEntity.changed_at)
        )
        histories: dict[str, list[dict]] = {}
        for issue_key, history in rows:
            histories.setdefault(issue_key, []).append(
                {
                    "id": history.jira_history_id,
                    "created": history.changed_at.isoformat(),
                    "items": history.items,
                }
            )
        return histories

    def project_comments(self, project_key: str) -> dict[str, list[dict]]:
        rows = self.session.execute(
            select(IssueEntity.key, CommentEntity)
            .join(CommentEntity, CommentEntity.issue_id == IssueEntity.id)
            .join(ProjectEntity, ProjectEntity.id == IssueEntity.project_id)
            .where(ProjectEntity.key == project_key)
            .order_by(CommentEntity.created_at, CommentEntity.id)
        )
        comments: dict[str, list[dict]] = {}
        for issue_key, comment in rows:
            comments.setdefault(issue_key, []).append(
                {
                    "id": comment.jira_id,
                    "issue_key": issue_key,
                    "author": comment.author_name,
                    "body": comment.body,
                    "created": (comment.created_at.isoformat() if comment.created_at else None),
                    "updated": (comment.updated_at.isoformat() if comment.updated_at else None),
                }
            )
        return comments

    def get_sprint_by_jira_id(self, sprint_id: int) -> SprintEntity | None:
        return self.session.scalar(select(SprintEntity).where(SprintEntity.jira_id == sprint_id))

    def list_project_sprints(self, project_key: str) -> list[SprintEntity]:
        """Return synchronized sprints for one project in chronological order."""
        return list(
            self.session.scalars(
                select(SprintEntity)
                .join(ProjectEntity, ProjectEntity.id == SprintEntity.project_id)
                .where(ProjectEntity.key == project_key)
                .order_by(SprintEntity.start_date, SprintEntity.jira_id)
            )
        )

    def list_sprint_issues(self, sprint_id: int) -> list[IssueEntity]:
        return list(
            self.session.scalars(
                select(IssueEntity)
                .join(SprintIssueEntity, SprintIssueEntity.issue_id == IssueEntity.id)
                .join(SprintEntity, SprintEntity.id == SprintIssueEntity.sprint_id)
                .where(SprintEntity.jira_id == sprint_id)
            )
        )

    @staticmethod
    def _datetime(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


class RAGRepository:
    """Persistence and similarity queries for RAG chunks."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def synchronize_chunks(
        self,
        project_key: str,
        chunks: list[RAGChunk],
        embeddings: list[list[float]],
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("Each RAG chunk must have exactly one embedding.")

        incoming_ids = {chunk.id for chunk in chunks}
        stale_query = delete(RAGChunkEntity).where(RAGChunkEntity.project_key == project_key)
        if incoming_ids:
            stale_query = stale_query.where(RAGChunkEntity.chunk_id.not_in(incoming_ids))
        self.session.execute(stale_query)

        existing = (
            {
                entity.chunk_id: entity
                for entity in self.session.scalars(
                    select(RAGChunkEntity).where(RAGChunkEntity.chunk_id.in_(incoming_ids))
                )
            }
            if incoming_ids
            else {}
        )

        embedded_at = datetime.now(UTC)
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            entity = existing.get(chunk.id)
            if entity is None:
                entity = RAGChunkEntity(chunk_id=chunk.id)
                self.session.add(entity)
            entity.project_key = project_key
            entity.issue_key = str(chunk.metadata["issue_key"])
            entity.content_type = str(chunk.metadata["content_type"])
            entity.chunk_index = int(chunk.metadata["chunk_index"])
            entity.text = chunk.text
            entity.content_hash = sha256(chunk.text.encode("utf-8")).hexdigest()
            entity.source_metadata = chunk.metadata
            source_updated_at = chunk.metadata.get("source_updated_at")
            entity.source_updated_at = (
                datetime.fromisoformat(str(source_updated_at)) if source_updated_at else None
            )
            entity.embedded_at = embedded_at
            entity.embedding = embedding
        self.session.flush()
        return len(chunks)

    def search(
        self,
        project_key: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[tuple[RAGChunkEntity, float]]:
        distance = RAGChunkEntity.embedding.cosine_distance(query_embedding).label("distance")
        rows = self.session.execute(
            select(RAGChunkEntity, distance)
            .where(RAGChunkEntity.project_key == project_key)
            .order_by(distance)
            .limit(top_k)
        )
        return [(entity, float(value)) for entity, value in rows]

    def index_status(self, project_key: str) -> dict:
        """Summarize persisted project knowledge without calling the model."""
        row = self.session.execute(
            select(
                func.count(func.distinct(RAGChunkEntity.issue_key)),
                func.count(RAGChunkEntity.id),
                func.max(RAGChunkEntity.embedded_at),
                func.max(RAGChunkEntity.source_updated_at),
            ).where(RAGChunkEntity.project_key == project_key)
        ).one()
        return {
            "project_key": project_key,
            "issues_indexed": int(row[0] or 0),
            "chunks_indexed": int(row[1] or 0),
            "last_indexed_at": row[2],
            "latest_source_update": row[3],
        }
