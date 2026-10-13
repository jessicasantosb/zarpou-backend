from typing import Any, Optional
from fastapi import APIRouter, Depends, status, BackgroundTasks, Request, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import (
    get_db,
    get_current_admin_user,
    get_current_customer_user,
    get_optional_customer_user,
    oauth2_scheme,
)
from app.core.limiter import limiter
from app.core.token_revocation import revoke_token
from app.models.user import User
from app.models.customer import Customer
from app.features.auth.app.schemas import (
    LoginRequest,
    CustomerLoginRequest,
    Token,
    RefreshTokenRequest,
    LogoutRequest,
    TokenResponse,
    Customer2FaConfig,
    Customer2FaStatus,
    Customer2FaVerify,
    Customer2FaSendCode,
    CustomerChangePassword,
)
from app.features.customers.app.schemas import CustomerCreate, CustomerResponse
from app.features.auth.app.services import AuthService

router = APIRouter()


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login_admin(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Login de administrador da Zarpou Viagens.
    Compatível com os dados do auth-store.ts do frontend (admin@zarpou.com.br / admin123).
    """
    service = AuthService(db)
    return service.login_admin(login_data)


@router.post("/customer/login", response_model=Token)
@limiter.limit("5/minute")
def login_customer(
    request: Request,
    login_data: CustomerLoginRequest,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
) -> Any:
    """
    Login simplificado do cliente / viajante.
    Se o cliente não existir, cria o cadastro inicial automaticamente com base no e-mail.
    """
    service = AuthService(db)
    return service.login_customer(login_data, background_tasks)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh_access_token(
    request: Request,
    refresh_in: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Renovação de access_token utilizando um refresh_token válido.
    Suporta Administradores, Clientes B2C e Contas Corporativas B2B.
    """
    service = AuthService(db)
    return service.refresh_token(refresh_in.refresh_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    token: Optional[str] = Depends(oauth2_scheme),
    logout_in: Optional[LogoutRequest] = None,
    db: Session = Depends(get_db),
) -> Any:
    """
    Logout imediato: revoga o access_token atual (e o refresh_token, se enviado)
    adicionando seus identificadores (jti) à blacklist até a expiração natural.
    """
    revoked = 0
    for raw in [token, logout_in.refresh_token if logout_in else None]:
        if raw and revoke_token(db, raw):
            revoked += 1
    if revoked == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nenhum token válido informado para logout.",
        )
    return {"detail": "Sessão encerrada com sucesso.", "revokedTokens": revoked}


@router.post("/customer/register", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def register_customer(
    customer_in: CustomerCreate,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
) -> Any:
    """
    Cadastro completo de novo cliente com disparo automático de e-mail de boas-vindas.
    """
    service = AuthService(db)
    return service.register_customer(customer_in, background_tasks)


@router.get("/me")
def read_current_user(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
) -> Any:
    """
    Retorna os dados do usuário autenticado no painel admin.
    """
    return {
        "id": admin.id,
        "name": admin.name,
        "email": admin.email,
        "role": admin.role,
        "allowedScreens": admin.allowedScreens,
        "allowed_screens": admin.allowedScreens,
        "twoFactorEnabled": admin.twoFactorEnabled,
        "two_factor_enabled": admin.twoFactorEnabled,
        "twoFactorMethod": admin.twoFactorMethod,
        "two_factor_method": admin.twoFactorMethod,
        "twoFactorSecret": admin.twoFactorSecret,
        "backupCodes": admin.backupCodes,
    }


@router.patch("/me/2fa")
def update_admin_2fa(
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> Any:
    """
    Atualiza as configurações de 2FA do administrador logado.
    """
    import json
    enabled = payload.get("enabled", False)
    method = payload.get("method")
    secret = payload.get("secret")
    backup_codes = payload.get("backupCodes") or payload.get("backup_codes")

    admin.two_factor_enabled = enabled
    if method:
        admin.two_factor_method = method
    if secret:
        admin.two_factor_secret = secret
    if backup_codes:
        admin.two_factor_backup_codes = json.dumps(backup_codes) if isinstance(backup_codes, list) else str(backup_codes)
    elif not enabled:
        admin.two_factor_secret = None
        admin.two_factor_backup_codes = None

    db.commit()
    db.refresh(admin)
    return {
        "success": True,
        "twoFactorEnabled": admin.twoFactorEnabled,
        "twoFactorMethod": admin.twoFactorMethod,
        "twoFactorSecret": admin.twoFactorSecret,
        "backupCodes": admin.backupCodes,
    }


@router.get("/customer/me", response_model=CustomerResponse)
def read_current_customer(
    customer: Customer = Depends(get_current_customer_user),
) -> Any:
    """
    Retorna os dados do cliente B2C autenticado.
    """
    return customer


@router.get("/customer/2fa", response_model=Customer2FaStatus)
def get_customer_2fa_status(
    customer: Customer = Depends(get_current_customer_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Retorna o status atual da autenticação de dois fatores (2FA) do cliente autenticado.
    """
    service = AuthService(db)
    return service.get_customer_2fa_status(customer)


@router.patch("/customer/2fa", response_model=Customer2FaStatus)
@router.post("/customer/2fa", response_model=Customer2FaStatus)
def configure_customer_2fa(
    config: Customer2FaConfig,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer_user),
) -> Any:
    """
    Ativa ou desativa o 2FA para o cliente autenticado, salvando preferências, chave TOTP e códigos de backup.
    """
    service = AuthService(db)
    return service.configure_customer_2fa(customer, config)


@router.post("/customer/2fa/send-code")
@limiter.limit("3/minute")
def send_customer_2fa_code(
    request: Request,
    payload: Optional[Customer2FaSendCode] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_optional_customer_user),
) -> Any:
    """
    Gera e envia um código numérico de 6 dígitos por e-mail para confirmação de login ou configuração de 2FA.
    """
    service = AuthService(db)
    return service.send_customer_2fa_code(current_customer, payload, background_tasks)


@router.post("/customer/2fa/verify", response_model=Token)
@limiter.limit("5/minute")
def verify_customer_2fa(
    request: Request,
    verify_data: Customer2FaVerify,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_optional_customer_user),
) -> Any:
    """
    Valida código de 2FA (seja TOTP, código de e-mail ou código de recuperação descartável).
    Retorna o token de acesso (JWT) e dados completos do cliente autenticado.
    """
    service = AuthService(db)
    return service.verify_customer_2fa(verify_data, current_customer)


@router.post("/customer/change-password")
def change_customer_password(
    pwd_data: CustomerChangePassword,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer_user),
) -> Any:
    """
    Altera a senha de acesso do cliente autenticado.
    """
    service = AuthService(db)
    return service.change_password(customer, pwd_data)
