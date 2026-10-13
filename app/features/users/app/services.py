from datetime import datetime, timezone
import json
import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import get_password_hash
from app.features.users.infra.models import User, ALL_ADMIN_SCREENS
from app.features.users.infra.repositories import SqlAlchemyUserRepository
from app.features.users.app.schemas import UserCreate, UserUpdate, UserStatusUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = SqlAlchemyUserRepository(db)

    def check_can_manage_admins(self, current_user: User):
        if current_user.role != "admin" and "administradores" not in current_user.allowedScreens:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado. Apenas usuários com permissão para o módulo de Administradores podem gerenciar a equipe."
            )

    def list_users(self, current_user: User) -> List[User]:
        self.check_can_manage_admins(current_user)
        return self.repository.get_all()

    def get_user_by_id(self, user_id: str, current_user: User) -> User:
        self.check_can_manage_admins(current_user)
        user = self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Administrador não encontrado.")
        return user

    def create_user(self, user_in: UserCreate, current_user: User) -> User:
        self.check_can_manage_admins(current_user)
        email_clean = user_in.email.strip().lower()
        if self.repository.get_by_email(email_clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um usuário cadastrado com este e-mail."
            )

        target_role = (user_in.role or "personalizado").lower()
        # Se for admin geral
        if target_role == "admin":
            if current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Apenas um Administrador Geral pode conceder o nível de Administrador Geral a outro usuário."
                )
            screens = list(ALL_ADMIN_SCREENS)
        else:
            target_role = "personalizado"
            screens = user_in.allowed_screens or []
            if not screens:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selecione ao menos uma tela de acesso para o usuário ou marque como Administrador Geral."
                )

        backup_codes_raw = None
        if user_in.two_factor_backup_codes:
            backup_codes_raw = json.dumps(user_in.two_factor_backup_codes)

        new_user = User(
            id=f"adm-{uuid.uuid4().hex[:8]}",
            name=user_in.name.strip(),
            email=email_clean,
            password_hash=get_password_hash(user_in.password),
            role=target_role,
            allowed_screens=json.dumps(screens),
            is_active=user_in.is_active,
            two_factor_enabled=bool(user_in.two_factor_enabled if user_in.two_factor_enabled is not None else False),
            two_factor_method=user_in.two_factor_method or "email",
            two_factor_secret=user_in.two_factor_secret,
            two_factor_backup_codes=backup_codes_raw,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return self.repository.save(new_user)

    def update_user(self, user_id: str, user_in: UserUpdate, current_user: User) -> User:
        self.check_can_manage_admins(current_user)
        user = self.get_user_by_id(user_id, current_user)

        if user_in.email:
            email_clean = user_in.email.strip().lower()
            conflict = self.repository.get_by_email(email_clean)
            if conflict and conflict.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Outro usuário já está utilizando este e-mail."
                )
            user.email = email_clean

        if user_in.name:
            user.name = user_in.name.strip()

        target_role = user_in.role.lower() if user_in.role else user.role
        if user_in.role:
            if target_role == "admin" and current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Apenas um Administrador Geral pode conceder o nível de Administrador Geral a outro usuário."
                )
            if user_id == current_user.id and target_role != "admin" and current_user.role == "admin":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Você não pode desmarcar seu próprio nível de Administrador Geral."
                )
            user.role = target_role

        if target_role == "admin":
            user.allowed_screens = json.dumps(list(ALL_ADMIN_SCREENS))
        elif user_in.allowed_screens is not None:
            if not user_in.allowed_screens:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selecione ao menos uma tela de acesso para o usuário ou marque como Administrador Geral."
                )
            user.allowed_screens = json.dumps(user_in.allowed_screens)

        if user_in.password:
            user.password_hash = get_password_hash(user_in.password)

        if user_in.is_active is not None:
            if user_id == current_user.id and not user_in.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Você não pode desativar seu próprio usuário administrador."
                )
            user.is_active = user_in.is_active

        if user_in.two_factor_enabled is not None:
            user.two_factor_enabled = user_in.two_factor_enabled

        if user_in.two_factor_method is not None:
            user.two_factor_method = user_in.two_factor_method

        if user_in.two_factor_secret is not None:
            user.two_factor_secret = user_in.two_factor_secret

        if user_in.two_factor_backup_codes is not None:
            user.two_factor_backup_codes = json.dumps(user_in.two_factor_backup_codes)

        user.updated_at = datetime.now(timezone.utc)
        return self.repository.save(user)

    def toggle_status(self, user_id: str, status_in: UserStatusUpdate, current_user: User) -> User:
        self.check_can_manage_admins(current_user)
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você não pode desativar seu próprio usuário administrador."
            )
        user = self.get_user_by_id(user_id, current_user)
        user.is_active = status_in.is_active
        user.updated_at = datetime.now(timezone.utc)
        return self.repository.save(user)

    def delete_user(self, user_id: str, current_user: User) -> dict:
        self.check_can_manage_admins(current_user)
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você não pode excluir sua própria conta de administrador."
            )
        user = self.get_user_by_id(user_id, current_user)
        self.repository.delete(user)
        return {"success": True, "message": "Administrador excluído com sucesso."}
