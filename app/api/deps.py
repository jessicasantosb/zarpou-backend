from typing import Optional, Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, get_db
from app.core.security import decode_access_token
from app.core.token_revocation import is_token_revoked
from app.models.user import User
from app.models.customer import Customer
from app.models.company import Company

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user_payload(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[dict]:
    if not token:
        return None
    payload = decode_access_token(token)
    if payload and is_token_revoked(
        db,
        payload.get("jti"),
        subject=payload.get("sub"),
        issued_at=payload.get("iat"),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão encerrada. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_admin_user(
    db: Session = Depends(get_db),
    payload: Optional[dict] = Depends(get_current_user_payload)
) -> User:
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("role") not in ["admin", "personalizado", "gestor", "atendente"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito à equipe administrativa da agência.",
        )
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
        )
    return user


def require_screen(screen_id: str):
    """
    Retorna uma dependência FastAPI que valida se o administrador possui permissão
    para acessar a tela/módulo especificado.
    Superadministradores ('admin') possuem acesso irrestrito a todas as telas.
    """
    def screen_checker(current_user: User = Depends(get_current_admin_user)) -> User:
        if current_user.role == "admin":
            return current_user

        user_screens = current_user.allowedScreens
        if screen_id not in user_screens:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado: seu perfil não possui permissão para o módulo '{screen_id}'. Apenas Administrador Geral ou usuários autorizados."
            )
        return current_user

    return screen_checker


def get_current_customer_user(
    db: Session = Depends(get_db),
    payload: Optional[dict] = Depends(get_current_user_payload)
) -> Customer:
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    customer_id = payload.get("sub")
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cliente não encontrado ou inativo.",
        )
    return customer


def get_optional_customer_user(
    db: Session = Depends(get_db),
    payload: Optional[dict] = Depends(get_current_user_payload)
) -> Optional[Customer]:
    if not payload:
        return None
    customer_id = payload.get("sub")
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
    return customer


def get_current_company_user(
    db: Session = Depends(get_db),
    payload: Optional[dict] = Depends(get_current_user_payload)
) -> Company:
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("role") != "company":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a contas empresariais Zarpou Empresas.",
        )
    company_id = payload.get("sub")
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empresa não localizada.",
        )
    if company.status == "bloqueada":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta corporativa suspensa ou bloqueada. Entre em contato com a Zarpou.",
        )
    return company


def get_optional_company_user(
    db: Session = Depends(get_db),
    payload: Optional[dict] = Depends(get_current_user_payload)
) -> Optional[Company]:
    if not payload or payload.get("role") != "company":
        return None
    company_id = payload.get("sub")
    company = db.query(Company).filter(Company.id == company_id).first()
    return company
