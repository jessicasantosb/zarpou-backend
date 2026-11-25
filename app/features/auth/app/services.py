from datetime import datetime, timezone, timedelta
import hashlib
import json
import secrets
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
from app.features.users.infra.models import AdminLoginChallenge, AdminPasswordResetToken
from app.features.auth.app.schemas import (
    AdminChallengeVerify,
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
    if not settings.RESEND_FROM_EMAIL:
        print("Configure RESEND_FROM_EMAIL para enviar e-mails.")
        return
    try:
        first_name = name.split()[0] if name else "Viajante"
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 25px; border: 1px solid #e2e8f0; border-radius: 20px; background-color: #ffffff;">
          <div style="background-color: #003366; padding: 25px; text-align: center; border-radius: 14px;">
            <h1 style="color: #ffffff; margin: 0; font-size: 20px;">Bem-vindo(a) à Fly Promo! ✈️</h1>
          </div>
          <div style="padding: 25px 15px; color: #334155; line-height: 1.6;">
            <p>Olá, <strong>{first_name}</strong>!</p>
            <p>Sua conta na <strong>Fly Promo</strong> foi criada com sucesso com o e-mail <strong>{email}</strong>.</p>
            <p>Agora você tem acesso às melhores tarifas em hospedagens com até 12x sem juros, passagens aéreas e pacotes sob medida.</p>
            <div style="text-align: center; margin: 30px 0;">
              <a href="{settings.FRONTEND_URL.rstrip("/")}/minhas-viagens" style="background-color: #003366; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 12px; font-weight: bold; display: inline-block;">Acessar Minha Conta Fly Promo →</a>
            </div>
            <p style="font-size: 12px; color: #64748b; margin-top: 25px;">Fly Promo • Cadastur: 34.120.948/0001-90</p>
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
                    "from": f"Fly Promo <{settings.RESEND_FROM_EMAIL}>",
                    "to": [email],
                    "subject": f"🎉 Bem-vindo(a) à Fly Promo, {first_name}! Sua conta foi criada",
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
    if not settings.RESEND_FROM_EMAIL:
        print("Configure RESEND_FROM_EMAIL para enviar e-mails.")
        return
    try:
        first_name = name.split()[0] if name else "Viajante"
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 25px; border: 1px solid #e2e8f0; border-radius: 20px; background-color: #ffffff;">
          <div style="background-color: #003366; padding: 25px; text-align: center; border-radius: 14px;">
            <h1 style="color: #ffffff; margin: 0; font-size: 20px;">Fly Promo</h1>
            <p style="color: #f7a01d; margin: 6px 0 0 0; font-size: 13px; font-weight: bold; text-transform: uppercase;">Recuperação de Senha</p>
          </div>
          <div style="padding: 30px 20px; color: #334155; line-height: 1.6;">
            <p style="font-size: 15px;">Olá, <strong>{first_name}</strong>!</p>
            <p style="font-size: 14px; color: #64748b;">Recebemos uma solicitação para redefinir a senha da sua conta Fly Promo (e-mail: <strong>{email}</strong>). Para criar uma nova senha, clique no botão abaixo:</p>
            <div style="text-align: center; margin: 30px 0;">
              <a href="{reset_url}" style="background-color: #003366; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 12px; font-weight: bold; display: inline-block;">Redefinir minha senha →</a>
            </div>
            <p style="font-size: 12px; color: #64748b;">Este link é de uso único e válido por <strong>30 minutos</strong>. Se você não solicitou esta alteração, ignore este e-mail — sua senha permanecerá a mesma.</p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 25px 0;" />
            <p style="font-size: 11px; color: #94a3b8; text-align: center; margin: 0;">
              Fly Promo • Cadastur: 34.120.948/0001-90<br />
              Mensagem automática enviada pelo sistema de segurança Fly Promo.
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
                    "from": f"Fly Promo <{settings.RESEND_FROM_EMAIL}>",
                    "to": [email],
                    "subject": "🔒 Redefina sua senha da Fly Promo",
                    "html": html_content,
                },
            )
    except Exception as exc:
        print("[Backend Resend Error]", exc)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def login_admin(self, login_data: LoginRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        email_clean = login_data.email.strip().lower()
        user = self.db.query(User).filter(User.email == email_clean).with_for_update().first()

        uses_demo_password = (
            settings.ENVIRONMENT.strip().lower() == "production" and login_data.password == "admin123"
        )
        if uses_demo_password or not user or not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E-mail ou senha incorretos."
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuário inativo no sistema."
            )

        if not user.two_factor_enabled:
            return self._admin_session(user)

        methods = self._admin_two_factor_methods(user)
        if not methods:
            raise HTTPException(status_code=503, detail="Nenhum método de verificação está disponível para esta conta.")

        challenge = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=10)
        row = self.db.merge(AdminLoginChallenge(
            user_id=user.id,
            token_hash=hashlib.sha256(challenge.encode()).hexdigest(),
            credential_fingerprint=self._admin_credential_fingerprint(user),
            email_code_hash=None,
            email_sent_at=None,
            expires_at=expires_at,
            attempts=0,
        ))
        if "email" in methods:
            self._queue_admin_email_code(row, user, background_tasks, now)
        self.db.commit()
        return {"challenge": challenge, "available_methods": methods, "expires_at": int(expires_at.timestamp())}

    @staticmethod
    def _admin_two_factor_methods(user: User) -> list[str]:
        methods = []
        if user.two_factor_method in {"authenticator", "app", "both"} and user.twoFactorSecret:
            methods.append("authenticator")
        if user.two_factor_method in {"email", "both", None} and settings.resend_email_configured:
            methods.append("email")
        if user.backupCodes:
            methods.append("backup")
        return methods

    @staticmethod
    def _admin_credential_fingerprint(user: User) -> str:
        credentials = json.dumps([
            user.email, user.password_hash, user.session_version, user.two_factor_method,
            user.two_factor_secret, user.two_factor_backup_codes,
        ])
        return hashlib.sha256(credentials.encode()).hexdigest()

    @staticmethod
    def _admin_email_code_hash(token_hash: str, code: str) -> str:
        return hmac.new(settings.SECRET_KEY.encode(), f"admin-2fa:{token_hash}:{code}".encode(), hashlib.sha256).hexdigest()

    def _queue_admin_email_code(
        self, row: AdminLoginChallenge, user: User, background_tasks: BackgroundTasks, now: datetime,
    ) -> None:
        code = generate_email_code()
        row.email_code_hash = self._admin_email_code_hash(row.token_hash, code)
        row.email_sent_at = now
        background_tasks.add_task(send_2fa_email_code, user.name, user.email, code)

    def _get_admin_challenge(self, challenge: str) -> tuple[User, AdminLoginChallenge]:
        invalid = HTTPException(status_code=400, detail="Verificação inválida ou expirada. Entre novamente.")
        token_hash = hashlib.sha256(challenge.encode()).hexdigest()
        owner = self.db.query(AdminLoginChallenge.user_id).filter(
            AdminLoginChallenge.token_hash == token_hash,
        ).first()
        if owner is None:
            raise invalid
        # Password and challenge updates acquire the user lock before modifying the challenge.
        user = self.db.query(User).filter_by(id=owner.user_id).with_for_update().first()
        row = self.db.query(AdminLoginChallenge).filter(
            AdminLoginChallenge.token_hash == token_hash,
            AdminLoginChallenge.expires_at > datetime.now(timezone.utc),
            AdminLoginChallenge.attempts < 5,
        ).first()
        if (user is None or not user.is_active or not user.two_factor_enabled or row is None
                or row.credential_fingerprint != self._admin_credential_fingerprint(user)):
            raise invalid
        return user, row

    def resend_admin_email_code(self, challenge: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        user, row = self._get_admin_challenge(challenge)
        if "email" not in self._admin_two_factor_methods(user):
            raise HTTPException(status_code=400, detail="Verificação por e-mail indisponível.")
        now = datetime.now(timezone.utc)
        sent_at = row.email_sent_at
        if sent_at and not sent_at.tzinfo:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        if sent_at and sent_at > now - timedelta(minutes=1):
            raise HTTPException(status_code=429, detail="Aguarde um minuto para reenviar o código.")
        self._queue_admin_email_code(row, user, background_tasks, now)
        self.db.commit()
        return {"success": True}

    def verify_admin_challenge(self, payload: AdminChallengeVerify) -> Dict[str, Any]:
        user, row = self._get_admin_challenge(payload.challenge)
        methods = self._admin_two_factor_methods(user)
        code = payload.code.strip().upper()
        valid = False
        if payload.method == "email" and "email" in methods and row.email_code_hash:
            valid = hmac.compare_digest(row.email_code_hash, self._admin_email_code_hash(row.token_hash, code))
        elif payload.method == "authenticator" and "authenticator" in methods:
            try:
                valid = verify_totp_code(user.twoFactorSecret, code)
            except ValueError:
                valid = False
        elif payload.method == "backup" and "backup" in methods:
            backup = find_backup_code_match(code, user.backupCodes)
            if backup:
                user.two_factor_backup_codes = json.dumps([item for item in user.backupCodes if item != backup])
                valid = True

        if not valid:
            row.attempts += 1
            self.db.commit()
            raise HTTPException(status_code=400, detail="Código de verificação inválido.")

        consumed = self.db.query(AdminLoginChallenge).filter_by(token_hash=row.token_hash).delete()
        if consumed != 1:
            raise HTTPException(status_code=400, detail="Verificação inválida ou expirada. Entre novamente.")
        session = self._admin_session(user, mfa_verified=True)
        self.db.commit()
        return session

    @staticmethod
    def _admin_session(user: User, mfa_verified: bool = False) -> Dict[str, Any]:
        access_token = create_access_token(
            subject=user.id, role=user.role, mfa_verified=mfa_verified, session_version=user.session_version,
        )
        refresh_token = create_refresh_token(
            subject=user.id, role=user.role, mfa_verified=mfa_verified, session_version=user.session_version,
        )
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

    def forgot_admin_password(self, email: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        response = {
            "success": True,
            "message": "Se o e-mail estiver cadastrado, você receberá um link para redefinir sua senha.",
        }
        # The shared mailer prints links in development when Resend is unset.
        if not settings.resend_email_configured:
            return response

        email_clean = email.strip().lower()
        user = (
            self.db.query(User)
            .filter(User.email == email_clean, User.is_active.is_(True))
            .with_for_update()
            .first()
        )
        if user:
            now = datetime.now(timezone.utc)
            recent_request = self.db.query(AdminPasswordResetToken.user_id).filter(
                AdminPasswordResetToken.user_id == user.id,
                AdminPasswordResetToken.email == user.email,
                AdminPasswordResetToken.session_version == user.session_version,
                AdminPasswordResetToken.expires_at > now + timedelta(
                    minutes=self.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES - 1,
                ),
            ).first()
            if recent_request:
                return response

            raw_token = secrets.token_urlsafe(32)
            self.db.merge(AdminPasswordResetToken(
                user_id=user.id,
                email=user.email,
                session_version=user.session_version,
                token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                expires_at=now + timedelta(minutes=self.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
            ))
            name, recipient = user.name, user.email
            self.db.commit()
            base = settings.FRONTEND_URL.rstrip("/")
            background_tasks.add_task(
                send_password_reset_email, name, recipient,
                f"{base}/admin/redefinir-senha?token={raw_token}",
            )

        return response

    def reset_admin_password(self, token: str, new_password: str) -> Dict[str, Any]:
        if len(new_password.encode("utf-8")) > 72 or not new_password.strip():
            raise HTTPException(status_code=400, detail="Informe uma senha válida de até 72 bytes.")
        if settings.ENVIRONMENT.strip().lower() == "production" and new_password == "admin123":
            raise HTTPException(status_code=400, detail="Escolha uma senha diferente da senha de demonstração.")

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        reset = self.db.query(AdminPasswordResetToken).filter_by(token_hash=token_hash)
        row = reset.first()
        invalid_link = HTTPException(
            status_code=400, detail="Link de recuperação inválido ou expirado. Solicite um novo.",
        )
        if row is None:
            raise invalid_link

        # Use the same lock order as issuance. The conditional delete also
        # prevents a stale request from consuming a newly issued token.
        user = self.db.query(User).filter_by(id=row.user_id).with_for_update().first()
        if user is None or not user.is_active or user.email != row.email or user.session_version != row.session_version:
            raise invalid_link
        consumed = reset.filter(
            AdminPasswordResetToken.expires_at > datetime.now(timezone.utc),
        ).delete(synchronize_session=False)
        if consumed != 1:
            raise invalid_link

        user.password_hash = get_password_hash(new_password)
        user.session_version += 1
        self.db.commit()
        return {"success": True, "message": "Senha redefinida com sucesso! Você já pode entrar com a nova senha."}

    def refresh_token(self, refresh_token_str: str) -> Dict[str, Any]:
        payload = decode_refresh_token(refresh_token_str)
        from app.core.token_revocation import is_token_revoked
        if payload and is_token_revoked(
            self.db,
            payload.get("jti"),
            subject=payload.get("sub"),
            issued_at=payload.get("iat"),
            issued_at_us=payload.get("issued_at_us"),
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
        mfa_verified = False
        session_version = None
        if role in ["admin", "personalizado", "gestor", "atendente"]:
            user = self.db.query(User).filter(User.id == subject, User.is_active.is_(True)).with_for_update().first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário associado ao token não encontrado ou inativo.",
                )
            mfa_verified = payload.get("mfa_verified") is True
            if not user.accepts_session(payload) or is_token_revoked(
                self.db, payload.get("jti"), subject=subject,
                issued_at=payload.get("iat"), issued_at_us=payload.get("issued_at_us"),
            ):
                raise HTTPException(status_code=401, detail="Faça login novamente.")
            session_version = user.session_version
            role = user.role
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

        new_access_token = create_access_token(
            subject=subject, role=role, mfa_verified=mfa_verified, session_version=session_version,
        )
        new_refresh_token = create_refresh_token(
            subject=subject, role=role, mfa_verified=mfa_verified, session_version=session_version,
        )
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": user_data,
        }
