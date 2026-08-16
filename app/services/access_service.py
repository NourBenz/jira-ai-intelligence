"""Central project authorization and Scrum-team access management."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.database.entities import (
    ProjectAdministratorEntity,
    ProjectEntity,
    TeamEntity,
    TeamMembershipEntity,
    UserEntity,
)


class AccessService:
    """Apply the one-company, one-owning-team-per-project access policy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_accessible_projects(self, user: UserEntity) -> list[ProjectEntity]:
        query = select(ProjectEntity).order_by(ProjectEntity.name, ProjectEntity.key)
        if user.role != "admin":
            team_ids = select(TeamMembershipEntity.team_id).where(
                TeamMembershipEntity.user_id == user.id,
                TeamMembershipEntity.is_active.is_(True),
            )
            administered_ids = select(ProjectAdministratorEntity.project_id).where(
                ProjectAdministratorEntity.user_id == user.id,
                ProjectAdministratorEntity.is_active.is_(True),
            )
            query = query.where(
                or_(
                    ProjectEntity.owning_team_id.in_(team_ids),
                    ProjectEntity.id.in_(administered_ids),
                )
            )
        return list(self.session.scalars(query))

    def can_access_project(self, user: UserEntity, project_key: str) -> bool:
        if user.role == "admin":
            return True
        return (
            self.session.scalar(
                select(ProjectEntity.id)
                .outerjoin(
                    TeamMembershipEntity,
                    (TeamMembershipEntity.team_id == ProjectEntity.owning_team_id)
                    & (TeamMembershipEntity.user_id == user.id)
                    & TeamMembershipEntity.is_active.is_(True),
                )
                .outerjoin(
                    ProjectAdministratorEntity,
                    (ProjectAdministratorEntity.project_id == ProjectEntity.id)
                    & (ProjectAdministratorEntity.user_id == user.id)
                    & ProjectAdministratorEntity.is_active.is_(True),
                )
                .where(
                    ProjectEntity.key == project_key.upper(),
                    or_(
                        TeamMembershipEntity.id.is_not(None),
                        ProjectAdministratorEntity.id.is_not(None),
                    ),
                )
            )
            is not None
        )

    def can_administer_project(self, user: UserEntity, project_key: str) -> bool:
        if user.role == "admin":
            return True
        return (
            self.session.scalar(
                select(ProjectAdministratorEntity.id)
                .join(ProjectEntity)
                .where(
                    ProjectEntity.key == project_key.upper(),
                    ProjectAdministratorEntity.user_id == user.id,
                    ProjectAdministratorEntity.is_active.is_(True),
                )
            )
            is not None
        )

    def list_administered_project_keys(self, user: UserEntity) -> list[str]:
        if user.role == "admin":
            return [project.key for project in self.list_accessible_projects(user)]
        return list(
            self.session.scalars(
                select(ProjectEntity.key)
                .join(ProjectAdministratorEntity)
                .where(
                    ProjectAdministratorEntity.user_id == user.id,
                    ProjectAdministratorEntity.is_active.is_(True),
                )
                .order_by(ProjectEntity.key)
            )
        )

    def create_team(self, name: str, description: str | None) -> TeamEntity:
        cleaned_name = name.strip()
        if self.session.scalar(select(TeamEntity).where(TeamEntity.name == cleaned_name)):
            raise HTTPException(status.HTTP_409_CONFLICT, "A team with this name already exists.")
        team = TeamEntity(
            name=cleaned_name,
            description=description.strip() if description else None,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        self.session.add(team)
        self.session.commit()
        self.session.refresh(team)
        return team

    def list_teams(self) -> list[TeamEntity]:
        return list(self.session.scalars(select(TeamEntity).order_by(TeamEntity.name)))

    def assign_user_to_team(
        self,
        team_id: int,
        user_id: int,
        scrum_role: str | None,
    ) -> TeamMembershipEntity:
        team = self._team(team_id)
        user = self._user(user_id)
        membership = self.session.scalar(
            select(TeamMembershipEntity).where(
                TeamMembershipEntity.team_id == team.id,
                TeamMembershipEntity.user_id == user.id,
            )
        )
        if membership is None:
            membership = TeamMembershipEntity(
                team=team,
                user=user,
                joined_at=datetime.now(UTC),
            )
            self.session.add(membership)
        membership.scrum_role = scrum_role
        membership.is_active = True
        self.session.commit()
        self.session.refresh(membership)
        return membership

    def remove_user_from_team(self, team_id: int, user_id: int) -> None:
        membership = self.session.scalar(
            select(TeamMembershipEntity).where(
                TeamMembershipEntity.team_id == team_id,
                TeamMembershipEntity.user_id == user_id,
            )
        )
        if membership is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Team membership not found.")
        membership.is_active = False
        self.session.commit()

    def assign_project_team(self, project_key: str, team_id: int) -> ProjectEntity:
        project = self._project(project_key)
        project.owning_team = self._team(team_id)
        self.session.commit()
        self.session.refresh(project)
        return project

    def grant_project_administrator(
        self,
        project_key: str,
        user_id: int,
        granted_by: UserEntity,
    ) -> ProjectAdministratorEntity:
        project = self._project(project_key)
        user = self._user(user_id)
        assignment = self.session.scalar(
            select(ProjectAdministratorEntity).where(
                ProjectAdministratorEntity.project_id == project.id,
                ProjectAdministratorEntity.user_id == user.id,
            )
        )
        if assignment is None:
            assignment = ProjectAdministratorEntity(
                project=project,
                user=user,
                granted_at=datetime.now(UTC),
            )
            self.session.add(assignment)
        assignment.granted_by = granted_by
        assignment.is_active = True
        self.session.commit()
        self.session.refresh(assignment)
        return assignment

    def revoke_project_administrator(self, project_key: str, user_id: int) -> None:
        project = self._project(project_key)
        assignment = self.session.scalar(
            select(ProjectAdministratorEntity).where(
                ProjectAdministratorEntity.project_id == project.id,
                ProjectAdministratorEntity.user_id == user_id,
            )
        )
        if assignment is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project administrator not found.")
        assignment.is_active = False
        self.session.commit()

    def list_users(self) -> list[UserEntity]:
        return list(self.session.scalars(select(UserEntity).order_by(UserEntity.username)))

    def project_access_summary(self, project_key: str) -> ProjectEntity:
        project = self.session.scalar(
            select(ProjectEntity)
            .options(
                selectinload(ProjectEntity.owning_team)
                .selectinload(TeamEntity.member_links)
                .selectinload(TeamMembershipEntity.user),
                selectinload(ProjectEntity.administrator_links),
            )
            .where(ProjectEntity.key == project_key.upper())
        )
        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project is not available.")
        return project

    def _team(self, team_id: int) -> TeamEntity:
        team = self.session.get(TeamEntity, team_id)
        if team is None or not team.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found.")
        return team

    def _user(self, user_id: int) -> UserEntity:
        user = self.session.get(UserEntity, user_id)
        if user is None or not user.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Active user not found.")
        return user

    def _project(self, project_key: str) -> ProjectEntity:
        project = self.session.scalar(
            select(ProjectEntity).where(ProjectEntity.key == project_key.upper())
        )
        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project is not available.")
        return project
