from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("owner", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    runs: Mapped[list["WorkflowRun"]] = relationship(back_populates="repository")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        UniqueConstraint("repo_id", "github_run_id", "run_attempt"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    github_run_id: Mapped[int] = mapped_column(BigInteger)
    run_attempt: Mapped[int] = mapped_column(Integer, default=1)
    workflow_name: Mapped[str] = mapped_column(String(200))
    event: Mapped[str] = mapped_column(String(50))
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    head_sha: Mapped[str] = mapped_column(String(40), index=True)
    conclusion: Mapped[str | None] = mapped_column(String(30), nullable=True)
    html_url: Mapped[str] = mapped_column(Text)
    run_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    github_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    repository: Mapped["Repository"] = relationship(back_populates="runs")
    jobs: Mapped[list["Job"]] = relationship(back_populates="run")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("run_id", "github_job_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id"), index=True)
    github_job_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(255))
    conclusion: Mapped[str | None] = mapped_column(String(30), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    log_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped["WorkflowRun"] = relationship(back_populates="jobs")
