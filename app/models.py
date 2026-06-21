from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.utils import utc_now


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    numbers: Mapped[list["Number"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Number(Base):
    __tablename__ = "numbers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    phone_number: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    range_prefix: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="numbers")
    otps: Mapped[list["Otp"]] = relationship(
        back_populates="number",
        cascade="all, delete-orphan",
    )


class Otp(Base):
    __tablename__ = "otps"
    __table_args__ = (
        UniqueConstraint(
            "number_id",
            "otp_code",
            "raw_message",
            name="uq_otp_number_code_message",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number_id: Mapped[int] = mapped_column(ForeignKey("numbers.id"), index=True)
    otp_code: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_message: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )

    number: Mapped[Number] = relationship(back_populates="otps")

