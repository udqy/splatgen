import enum
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, DateTime, Enum, Text
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class JobStatus(enum.Enum):
    QUEUED = "QUEUED"
    PREPROCESSING = "PREPROCESSING"
    RUNNING_COLMAP = "RUNNING_COLMAP"
    RUNNING_SPLATTING = "RUNNING_SPLATTING" 
    POSTPROCESSING = "POSTPROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Base(DeclarativeBase):
    pass


class Job(Base):
    """
    Create a table named 'job' and then creates the columns using SQLAlchemy Mapped and mapped_columns.
    Does automatic type checking.
    """
    __tablename__ = "job"

    jobid: Mapped[str] = mapped_column(String(12), primary_key=True, index=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, default=JobStatus.QUEUED, index=True)
    failed_at_step: Mapped[str | None] = mapped_column(String(50), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    input_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_video_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_splat_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Job(jobid='{self.jobid}', name='{self.name}', status='{self.status.name}')>"
    