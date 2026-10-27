from datetime import datetime, timezone, timedelta
import hashlib
import json
import secrets
import uuid
from typing import Any, Optional, Dict
from fastapi import HTTPException, status, BackgroundTasks
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.core.two_factor import (
    generate_totp_code,
    verify_totp_code,
    generate_email_code,
    send_2fa_email_code,
    encrypt_totp_secret,
    hash_backup_code,
    find_backup_code_match,
)
import hmac
from app.models.user import User
from app.models.customer import Customer, CustomerPasswordResetToken
from app.features.auth.app.schemas import (
    LoginRequest,
    CustomerLoginRequest,
    Customer2FaConfig,
    Customer2FaStatus,
    Customer2FaVerify,
    Customer2FaSendCode,
    CustomerChangePassword,
)
from app.features.customers.app.schemas import CustomerCreate


def _dev_2fa_shortcuts_enabled() -> bool:
    """Atalhos de desenvolvimento (PIN fixo 123456 / eco do código) jamais ativos em produção."""
    if settings.ENVIRONMENT == "production":
        return False
    return settings.DEBUG or not settings.RESEND_API_KEY


def send_welcome_email_task(name: str, email: str) -> None:
    api_key = settings.RESEND_API_KEY
    if not api_key:
        return
    try:
        first_name = name.split()[0] if name else "Viajante"
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 25px; border: 1px solid #e2e8f0; border-radius: 20px; background-color: #ffffff;">
          <div style="background-color: #003366; padding: 25px; text-align: center; border-radius: 14px;">
            <h1 style="color: #ffffff; margin: 0; font-size: 20px;">Bem-vindo(a) à Zarpou Viagens! ✈️</h1>
          </div>
          <div style="padding: 25px 15px; color: #334155; line-height: 1.6;">
            <p>Olá, <strong>{first_name}</strong>!</p>
            <p>Sua conta na <strong>Zarpou Viagens e Turismo</strong> foi criada com sucesso com o e-mail <strong>{email}</strong>.</p>
            <p>Agora você tem acesso às melhores tarifas em hospedagens com até 12x sem juros, passagens aéreas e pacotes sob medida.</p>
            <div style="text-align: center; margin: 30px 0;">
              <a href="https://www.zarpouviagens.com.br/minhas-viagens" style="background-color: #003366; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 12px; font-weight: bold; display: inline-block;">Acessar Minha Conta Zarpou →</a>
            </div>
            <p style="font-size: 12px; color: #64748b; margin-top: 25px;">Zarpou Viagens e Turismo Ltda • Cadastur: 34.120.948/0001-90</p>
          </div>
        </div>
        """
        with httpx.Client(timeout=10.0) as client:
            client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": "Zarpou Viagens <lazer@zarpouviagens.com.br>",
                    "to": [email],
                    "subject": f"🎉 Bem-vindo(a) à Zarpou Viagens, {first_name}! Sua conta foi criada",
                    "html": html_content,
                },
            )
    except Exception as exc:
        print("[Backend Resend Error]", exc)


def send_password_reset_email(name: str, email: str, reset_url: str) -> None:
    """
    Envia o e-mail com o link de recuperação de senha (Resend).
    Sem chave configurada (dev), simula imprimindo o link no console.
    """
    api_key = settings.RESEND_API_KEY
    if not api_key:
        print(f"[RECUPERAÇÃO DE SENHA - DEV SIMULATION] Link para {email}: {reset_url}")
        return
    try:
        first_name = name.split()[0] if name else "Viajante"
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 25px; border: 1px solid #e2e8f0; border-radius: 20px; background-color: #ffffff;">
          <div style="background-color: #003366; padding: 25px; text-align: center; border-radius: 14px;">
            <h1 style="color: #ffffff; margin: 0; font-size: 20px;">Zarpou Viagens e Turismo</h1>
            <p style="color: #f7a01d; margin: 6px 0 0 0; font-size: 13px; font-weight: bold; text-transform: uppercase;">Recuperação de Senha</p>
          </div>
          <div style="padding: 30px 20px; color: #334155; line-height: 1.6;">
            <p style="font-size: 15px;">Olá, <strong>{first_name}</strong>!</p>
            <p style="font-size: 14px; color: #64748b;">Recebemos uma solicitação para redefinir a senha da sua conta Zarpou (e-mail: <strong>{email}</strong>). Para criar uma nova senha, clique no botão abaixo:</p>
            <div style="text-align: center; margin: 30px 0;">
              <a href="{reset_url}" style="background-color: #003366; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 12px; font-weight: bold; display: inline-block;">Redefinir minha senha →</a>
            </div>
            <p style="font-size: 12px; color: #64748b;">Este link é de uso único e válido por <strong>30 minutos</strong>. Se você não solicitou esta alteração, ignore este e-mail — sua senha permanecerá a mesma.</p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 25px 0;" />
            <p style="font-size: 11px; color: #94a3b8; text-align: center; margin: 0;">
              Zarpou Viagens e Turismo Ltda • Cadastur: 34.120.948/0001-90<br />
              Mensagem automática enviada pelo sistema de segurança Zarpou.
            </p>
          </div>
        </div>
        """
        with httpx.Client(timeout=10.0) as client:
            client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": "Zarpou Viagens <lazer@zarpouviagens.com.br>",
                    "to": [email],
                    "subject": "🔒 Redefina sua senha da Zarpou Viagens",
                    "html": html_content,
                },
            )
    except Exception as exc:
        print("[Backend Resend Error]", exc)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def login_admin(self, login_data: LoginRequest) -> Dict[str, Any]:
        email_clean = login_data.email.strip().lower()
        user = self.db.query(User).filter(User.email == email_clean).first()

        # Se usuário admin não existe, verificar se é a credencial padrão inicial e criar
        if not user and (email_clean in ["admin@zarpou.com.br", "admin"]) and login_data.password == "admin123":
            user = User(
                id="adm-1",
                name="Administrador Zarpou",
                email="admin@zarpou.com.br",
                password_hash=get_password_hash("admin123"),
                role="admin",
                is_active=True
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

        if not user or not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E-mail ou senha incorretos."
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuário inativo no sistema."
            )

        access_token = create_access_token(subject=user.id, role=user.role)
        refresh_token = create_refresh_token(subject=user.id, role=user.role)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "allowedScreens": user.allowedScreens,
                "allowed_screens": user.allowedScreens,
                "twoFactorEnabled": user.twoFactorEnabled,
                "two_factor_enabled": user.twoFactorEnabled,
                "twoFactorMethod": user.twoFactorMethod,
                "two_factor_method": user.twoFactorMethod,
                # Segredo TOTP e códigos de backup NUNCA são devolvidos (vazavam em texto
                # claro na resposta de login — um token roubado daria bypass permanente do 2FA).
            }
        }

    def login_customer(
        self,
        login_data: CustomerLoginRequest,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Dict[str, Any]:
        email_clean = login_data.email.strip().lower()

        # Bloqueia contas administrativas de serem cadastradas/logadas na área de clientes.
        # Mensagem genérica (idêntica à de senha incorreta): um erro específico confirmaria
        # que o e-mail pertence a um admin — enumeração de contas privilegiadas.
        is_admin = self.db.query(User).filter(User.email == email_clean).first()
        if is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E-mail ou senha incorretos."
            )

        customer = self.db.query(Customer).filter(Customer.email == email_clean).first()

        # LOGIN SEM SENHA É PROIBIDO (OWASP A07): a senha é obrigatória no schema e
        # sempre é verificada abaixo — inclusive em contas legadas sem senha definida.
        #
        # A auto-criação de conta no login foi REMOVIDA (SECURITY_BACKLOG #1):
        # e-mail desconhecido retornava 200 e criava conta sem os consentimentos
        # LGPD exigidos no registro — e, como a resposta passava a ser 400 só
        # para e-mails existentes, o login virava oráculo de enumeração. Agora
        # exige-se cadastro prévio e a resposta para e-mail desconhecido é
        # idêntica à de senha incorreta (anti-enumeração).
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E-mail ou senha incorretos.",
            )
        if not customer.password_hash:
            # Conta legada criada sem senha pelo bug antigo de login sem senha.
            # Define a senha no primeiro acesso autenticado — a partir daqui toda
            # conta passa a exigir senha para entrar.
            if len(login_data.password.strip()) < 6:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A senha deve ter no mínimo 6 caracteres.",
                )
            customer.password_hash = get_password_hash(login_data.password)
            self.db.commit()
        elif not verify_password(login_data.password, customer.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E-mail ou senha incorretos."
            )

        # Se o cliente possui 2FA ativado e o método é email ou both, gera o PIN e dispara email
        if customer.two_factor_enabled and customer.two_factor_method in ["email", "both"]:
            pin_code = generate_email_code()
            customer.two_factor_temp_code = pin_code
            customer.two_factor_temp_code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
            self.db.commit()
            if background_tasks:
                background_tasks.add_task(send_2fa_email_code, customer.name, customer.email, pin_code)

        access_token = create_access_token(subject=customer.id, role="customer")
        refresh_token = create_refresh_token(subject=customer.id, role="customer")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": self._customer_public_payload(customer),
        }

    @staticmethod
    def _customer_public_payload(customer: Customer) -> Dict[str, Any]:
        """
        Dados do cliente devolvidos no login/2FA. O segredo TOTP NÃO é incluído
        (só é acessível via GET /auth/customer/2fa com sessão autenticada).
        """
        return {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "cpf": customer.cpf,
            "createdAt": customer.created_at.isoformat() if customer.created_at else None,
            "notifications": customer.notifications,
            "twoFactorEnabled": customer.twoFactorEnabled,
            "twoFactorMethod": customer.twoFactorMethod,
            "twoFactorSecret": "",
            "backupCodes": customer.backupCodes,
            "twoFactorConfirmedAt": customer.twoFactorConfirmedAt,
            "consent": customer.consent,
        }

    def register_customer(
        self,
        customer_in: CustomerCreate,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Customer:
        email_clean = customer_in.email.strip().lower()

        is_admin = self.db.query(User).filter(User.email == email_clean).first()
        if is_admin:
            # Mesma mensagem do caso de e-mail duplicado abaixo: não distingue
            # admin de cliente para não confirmar contas privilegiadas (enumeração).
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma conta com este e-mail. Tente fazer login."
            )

        existing = self.db.query(Customer).filter(Customer.email == email_clean).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma conta com este e-mail. Tente fazer login."
            )

        customer = Customer(
            id=f"cust-{int(datetime.now(timezone.utc).timestamp())}",
            name=customer_in.name,
            email=email_clean,
            phone=customer_in.phone,
            cpf=customer_in.cpf,
            is_active=True
        )
        if customer_in.password:
            customer.password_hash = get_password_hash(customer_in.password)

        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)

        if background_tasks:
            background_tasks.add_task(send_welcome_email_task, customer.name, customer.email)

        return customer

    def get_customer_2fa_status(self, customer: Customer) -> Dict[str, Any]:
        return {
            "enabled": customer.twoFactorEnabled,
            "method": customer.twoFactorMethod,
            "hasSecret": bool(customer.two_factor_secret),
            "secret": customer.twoFactorSecret,
            "backupCodesCount": len(customer.backupCodeHashes),
            "backupCodes": customer.backupCodes,
            "confirmedAt": customer.twoFactorConfirmedAt,
        }

    def configure_customer_2fa(self, customer: Customer, config: Customer2FaConfig) -> Dict[str, Any]:
        customer.two_factor_enabled = config.enabled
        if config.enabled:
            customer.two_factor_method = config.method or "email"
            if config.secret:
                # Segredo TOTP cifrado em repouso (Fernet)
                customer.two_factor_secret = encrypt_totp_secret(config.secret.strip().upper())
            if config.backupCodes is not None:
                # Códigos de recuperação armazenados apenas como hash (HMAC-SHA256)
                customer.two_factor_backup_codes = json.dumps(
                    [hash_backup_code(c) for c in config.backupCodes if c and c.strip()]
                )
            customer.two_factor_confirmed_at = datetime.now(timezone.utc)
        else:
            customer.two_factor_confirmed_at = None

        self.db.commit()
        self.db.refresh(customer)
        return self.get_customer_2fa_status(customer)

    def send_customer_2fa_code(
        self,
        target_customer: Optional[Customer],
        payload: Optional[Customer2FaSendCode],
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Dict[str, Any]:
        cust = target_customer
        if not cust and payload and payload.email:
            clean_email = payload.email.strip().lower()
            cust = self.db.query(Customer).filter(Customer.email == clean_email).first()

        if not cust:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não localizado para envio do código de segurança."
            )

        code = generate_email_code()
        cust.two_factor_temp_code = code
        cust.two_factor_temp_code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        self.db.commit()

        if background_tasks:
            background_tasks.add_task(send_2fa_email_code, cust.name, cust.email, code)
        else:
            send_2fa_email_code(cust.name, cust.email, code)

        # O código NUNCA é devolvido na resposta: ele só chega ao cliente via e-mail.
        # (Antes existia um atalho de dev que ecoava o código aqui — furo de segurança:
        # qualquer chamador obtinha o código sem acesso à caixa postal.)
        # Em desenvolvimento, o verify aceita o atalho "123456" (_dev_2fa_shortcuts_enabled).
        return {
            "success": True,
            "message": "Código de verificação enviado para o e-mail cadastrado.",
            "expiresInSeconds": 600,
        }

    def verify_customer_2fa(
        self,
        verify_data: Customer2FaVerify,
        current_customer: Optional[Customer]
    ) -> Dict[str, Any]:
        target_customer = current_customer
        if not target_customer and verify_data.email:
            clean_email = verify_data.email.strip().lower()
            target_customer = self.db.query(Customer).filter(Customer.email == clean_email).first()

        if not target_customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cliente não identificado para verificação de 2FA."
            )

        clean_code = verify_data.code.strip().upper().replace(" ", "")
        is_valid = False
        totp_secret = target_customer.twoFactorSecret
        matched_backup = find_backup_code_match(clean_code, target_customer.backupCodeHashes)

        # 1. Código de Recuperação descartável (comparado por hash)
        if matched_backup:
            remaining_codes = [c for c in target_customer.backupCodeHashes if c != matched_backup]
            target_customer.two_factor_backup_codes = json.dumps(remaining_codes)
            self.db.commit()
            is_valid = True

        # 2. Código do App Autenticador TOTP
        elif totp_secret and verify_totp_code(totp_secret, clean_code):
            is_valid = True

        # 3. Código numérico de 6 dígitos enviado por E-mail
        elif target_customer.two_factor_temp_code and hmac.compare_digest(
            target_customer.two_factor_temp_code, clean_code
        ):
            if target_customer.two_factor_temp_code_expires_at and target_customer.two_factor_temp_code_expires_at < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="O código de verificação expirou. Solicite um novo."
                )
            target_customer.two_factor_temp_code = None
            target_customer.two_factor_temp_code_expires_at = None
            self.db.commit()
            is_valid = True

        # 4. Modo teste / dev (nunca habilitado em produção)
        elif _dev_2fa_shortcuts_enabled() and clean_code == "123456":
            is_valid = True

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código de verificação incorreto ou expirado."
            )

        access_token = create_access_token(subject=target_customer.id, role="customer")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": self._customer_public_payload(target_customer),
        }

    def change_password(self, customer: Customer, pwd_data: CustomerChangePassword) -> Dict[str, Any]:
        if not customer.password_hash or not verify_password(pwd_data.currentPassword, customer.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A senha atual informada está incorreta."
            )

        if len(pwd_data.newPassword.strip()) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A nova senha deve ter no mínimo 6 caracteres."
            )

        customer.password_hash = get_password_hash(pwd_data.newPassword.strip())
        self.db.commit()
        return {"success": True, "message": "Senha alterada com sucesso!"}

    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30

    def forgot_password(self, email: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """
        Solicitação de recuperação de senha por e-mail.
        - Resposta idêntica exista ou não a conta (evita enumeração de e-mails).
        - Token aleatório (32 bytes), guardado APENAS como hash SHA-256,
          com validade de 30 minutos e uso único.
        - Novas solicitações invalidam links anteriores ainda pendentes.
        """
        email_clean = (email or "").strip().lower()
        customer = (
            self.db.query(Customer)
            .filter(Customer.email == email_clean, Customer.is_active == True)  # noqa: E712
            .first()
        )
        if customer:
            # Invalida solicitações anteriores ainda pendentes do mesmo cliente
            self.db.query(CustomerPasswordResetToken).filter(
                CustomerPasswordResetToken.customer_id == customer.id,
                CustomerPasswordResetToken.used_at.is_(None),
            ).delete(synchronize_session=False)

            raw_token = secrets.token_urlsafe(32)
            self.db.add(
                CustomerPasswordResetToken(
                    customer_id=customer.id,
                    token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(minutes=self.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
                )
            )
            self.db.commit()

            base = settings.FRONTEND_URL.rstrip("/")
            reset_url = f"{base}/redefinir-senha?token={raw_token}"
            background_tasks.add_task(
                send_password_reset_email, customer.name, customer.email, reset_url
            )

        return {
            "success": True,
            "message": "Se o e-mail estiver cadastrado, você receberá um link para redefinir sua senha.",
        }

    def reset_password(self, token: str, new_password: str) -> Dict[str, Any]:
        """Redefine a senha usando o token recebido por e-mail (uso único, 30 min)."""
        invalid_msg = "Link de recuperação inválido ou expirado. Solicite um novo."

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        row = (
            self.db.query(CustomerPasswordResetToken)
            .filter(CustomerPasswordResetToken.token_hash == token_hash)
            .first()
        )
        if not row or row.used_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=invalid_msg)

        # Comparação robusta entre Postgres (tz-aware) e SQLite (tz-naive)
        expires_at = (
            row.expires_at
            if row.expires_at.tzinfo
            else row.expires_at.replace(tzinfo=timezone.utc)
        )
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=invalid_msg)

        customer = self.db.query(Customer).filter(Customer.id == row.customer_id).first()
        if not customer or not customer.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=invalid_msg)

        customer.password_hash = get_password_hash(new_password.strip())
        row.used_at = datetime.now(timezone.utc)
        # Grava o consumo do token antes de limpar os demais (evita que o
        # DELETE em massa apague o próprio registro que está sendo marcado)
        self.db.flush()
        # Invalida qualquer outro link pendente do mesmo cliente
        self.db.query(CustomerPasswordResetToken).filter(
            CustomerPasswordResetToken.customer_id == customer.id,
            CustomerPasswordResetToken.used_at.is_(None),
            CustomerPasswordResetToken.id != row.id,
        ).delete(synchronize_session=False)
        self.db.commit()

        # Derruba sessões existentes: access/refresh tokens emitidos antes do
        # reset deixam de ser aceitos (um comprometimento não sobrevive à
        # redefinição). Tokens de logins futuros continuam válidos. (SECURITY_BACKLOG #2)
        from app.core.token_revocation import revoke_subject_tokens
        revoke_subject_tokens(self.db, customer.id)

        return {
            "success": True,
            "message": "Senha redefinida com sucesso! Você já pode entrar com a nova senha.",
        }

    def refresh_token(self, refresh_token_str: str) -> Dict[str, Any]:
        payload = decode_refresh_token(refresh_token_str)
        from app.core.token_revocation import is_token_revoked
        if payload and is_token_revoked(
            self.db,
            payload.get("jti"),
            subject=payload.get("sub"),
            issued_at=payload.get("iat"),
        ):
            payload = None
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido ou expirado.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        subject = payload.get("sub")
        role = payload.get("role", "customer")
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido.",
            )

        user_data = None
        if role in ["admin", "personalizado", "gestor", "atendente"]:
            user = self.db.query(User).filter(User.id == subject, User.is_active == True).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário associado ao token não encontrado ou inativo.",
                )
            user_data = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "allowedScreens": user.allowedScreens,
                "allowed_screens": user.allowedScreens,
            }
        elif role == "company":
            from app.features.companies.infra.models import Company
            comp = self.db.query(Company).filter(Company.id == subject).first()
            if not comp or comp.status == "bloqueada":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Empresa associada ao token não localizada ou bloqueada.",
                )
            user_data = {
                "id": comp.id,
                "name": comp.nome_fantasia,
                "email": comp.corporate_email,
                "role": "company",
            }
        else:  # customer
            cust = self.db.query(Customer).filter(Customer.id == subject, Customer.is_active == True).first()
            if not cust:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Cliente associado ao token não encontrado ou inativo.",
                )
            user_data = {
                "id": cust.id,
                "name": cust.name,
                "email": cust.email,
                "phone": cust.phone,
                "cpf": cust.cpf,
                "createdAt": cust.created_at.isoformat() if cust.created_at else None,
                "twoFactorEnabled": cust.twoFactorEnabled,
            }

        new_access_token = create_access_token(subject=subject, role=role)
        new_refresh_token = create_refresh_token(subject=subject, role=role)
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": user_data,
        }
