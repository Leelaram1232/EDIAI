"""
Auth Service — handles user registration, login, and profile management.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """Authentication business logic."""

    async def register(self, email: str, name: str, password: str, db: AsyncSession) -> User:
        """Register a new user."""
        # Check for existing user
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        # Check if this is the first user (make them admin)
        count_result = await db.execute(select(func.count(User.id)))
        user_count = count_result.scalar()

        user = User(
            email=email,
            name=name,
            hashed_password=hash_password(password),
            role="admin" if user_count == 0 else "user",
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

        logger.info(f"User registered: {email} (role={user.role})")
        return user

    async def authenticate(self, email: str, password: str, db: AsyncSession) -> tuple[User, str]:
        """Authenticate user and return user + JWT token."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Account is disabled")

        token = create_access_token(data={"sub": user.id, "role": user.role})
        logger.info(f"User logged in: {email}")
        return user, token

    async def update_profile(
        self, user: User, name: str = None, email: str = None, db: AsyncSession = None
    ) -> User:
        """Update user profile."""
        if name:
            user.name = name
        if email and email != user.email:
            # Check uniqueness
            result = await db.execute(select(User).where(User.email == email))
            if result.scalar_one_or_none():
                raise ValueError("Email already in use")
            user.email = email

        await db.flush()
        await db.refresh(user)
        return user


auth_service = AuthService()
