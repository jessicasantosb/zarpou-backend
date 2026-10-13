from typing import Any, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_admin_user, require_screen
from app.features.users.infra.models import User
from app.features.users.app.schemas import (
    UserCreate,
    UserUpdate,
    UserStatusUpdate,
    UserResponse,
)
from app.features.users.app.services import UserService

router = APIRouter()


@router.get("", response_model=List[UserResponse])
def list_admin_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen("administradores")),
) -> Any:
    """
    Lista todos os usuários administradores do sistema Zarpou.
    Apenas Administrador Geral.
    """
    service = UserService(db)
    return service.list_users(current_user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen("administradores")),
) -> Any:
    """
    Cadastra um novo usuário administrador ou operador do sistema.
    Apenas Administrador Geral.
    """
    service = UserService(db)
    return service.create_user(user_in, current_user)


@router.get("/{id}", response_model=UserResponse)
def get_admin_user(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen("administradores")),
) -> Any:
    """
    Retorna os detalhes de um administrador específico.
    Apenas Administrador Geral.
    """
    service = UserService(db)
    return service.get_user_by_id(id, current_user)


@router.put("/{id}", response_model=UserResponse)
def update_admin_user(
    id: str,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen("administradores")),
) -> Any:
    """
    Atualiza dados de um administrador existente.
    Apenas Administrador Geral.
    """
    service = UserService(db)
    return service.update_user(id, user_in, current_user)


@router.patch("/{id}/status", response_model=UserResponse)
def toggle_admin_user_status(
    id: str,
    status_in: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen("administradores")),
) -> Any:
    """
    Ativa ou desativa um administrador do sistema.
    Apenas Administrador Geral.
    """
    service = UserService(db)
    return service.toggle_status(id, status_in, current_user)


@router.delete("/{id}")
def delete_admin_user(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen("administradores")),
) -> Any:
    """
    Remove um administrador do sistema.
    Apenas Administrador Geral.
    """
    service = UserService(db)
    return service.delete_user(id, current_user)
