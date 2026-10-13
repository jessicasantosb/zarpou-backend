from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import get_password_hash
from app.features.customers.infra.models import Customer
from app.features.customers.infra.repositories import SqlAlchemyCustomerRepository
from app.features.customers.app.schemas import (
    CustomerAdminCreate,
    CustomerAdminUpdate,
    CustomerStatusUpdate,
    CustomerUpdateNotifications,
    CustomerUpdateProfile,
    CustomerConsentUpdate,
    CustomerDeleteRequest,
)
from app.models.booking import Booking
from app.models.user import User


class CustomerService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = SqlAlchemyCustomerRepository(db)

    def list_customers(
        self,
        q: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = self.db.query(Customer)

        # Exclui e-mails da equipe administrativa do sistema da lista de clientes viajantes
        admin_emails = [u[0].strip().lower() for u in self.db.query(User.email).all()]
        if admin_emails:
            query = query.filter(~Customer.email.in_(admin_emails))

        if q:
            search = f"%{q.strip().lower()}%"
            query = query.filter(
                (Customer.name.ilike(search)) |
                (Customer.email.ilike(search)) |
                (Customer.phone.ilike(search)) |
                (Customer.cpf.ilike(search))
            )

        if is_active is not None:
            query = query.filter(Customer.is_active == is_active)

        customers = query.order_by(Customer.created_at.desc()).offset(skip).limit(limit).all()

        results = []
        for c in customers:
            total_bookings = self.db.query(Booking).filter(Booking.customer_id == c.id).count()
            cust_dict = {
                "id": c.id,
                "name": c.name,
                "fullName": c.name,
                "email": c.email,
                "phone": c.phone,
                "cpf": c.cpf,
                "is_active": c.is_active,
                "created_at": c.created_at,
                "notification_whatsapp_promotions": c.notification_whatsapp_promotions,
                "notification_email_promotions": c.notification_email_promotions,
                "notification_updated_at": c.notification_updated_at,
                "notifications": c.notifications,
                "total_bookings": total_bookings,
                "twoFactorEnabled": c.twoFactorEnabled,
                "twoFactorMethod": c.twoFactorMethod,
                "twoFactorSecret": None,
                "backupCodes": c.backupCodes,
                "twoFactorConfirmedAt": c.twoFactorConfirmedAt,
            }
            results.append(cust_dict)

        return results

    def get_customer_details(self, customer_id: str) -> Dict[str, Any]:
        customer = self.repository.get_by_id(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente não encontrado.")

        bookings = self.db.query(Booking).filter(Booking.customer_id == customer.id).order_by(Booking.created_at.desc()).all()
        bookings_data = [
            {
                "id": b.id,
                "locator_code": b.locator_code,
                "status": b.status,
                "payment_status": b.payment_status,
                "total_amount": float(b.total_amount) if b.total_amount else 0.0,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "lead_passenger_name": b.lead_passenger_name,
                "booking_type": b.booking_type,
            }
            for b in bookings
        ]

        return {
            "id": customer.id,
            "name": customer.name,
            "fullName": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "cpf": customer.cpf,
            "is_active": customer.is_active,
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
            "notification_whatsapp_promotions": customer.notification_whatsapp_promotions,
            "notification_email_promotions": customer.notification_email_promotions,
            "notification_updated_at": customer.notification_updated_at.isoformat() if customer.notification_updated_at else None,
            "notifications": customer.notifications,
            "total_bookings": len(bookings),
            "bookings": bookings_data,
            "twoFactorEnabled": customer.twoFactorEnabled,
            "twoFactorMethod": customer.twoFactorMethod,
            "twoFactorSecret": None,
            "backupCodes": customer.backupCodes,
            "twoFactorConfirmedAt": customer.twoFactorConfirmedAt,
        }

    def create_customer(self, customer_in: CustomerAdminCreate) -> Customer:
        email_clean = customer_in.email.strip().lower()
        if self.repository.get_by_email(email_clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um cliente cadastrado com este e-mail."
            )

        customer = Customer(
            id=f"cust-{int(datetime.now(timezone.utc).timestamp())}",
            name=customer_in.name.strip(),
            email=email_clean,
            phone=customer_in.phone.strip() if customer_in.phone else None,
            cpf=customer_in.cpf.strip() if customer_in.cpf else None,
            is_active=customer_in.is_active,
            notification_whatsapp_promotions=True,
            notification_email_promotions=True,
        )
        if customer_in.password:
            customer.password_hash = get_password_hash(customer_in.password)

        return self.repository.save(customer)

    def update_customer(self, customer_id: str, customer_in: CustomerAdminUpdate) -> Customer:
        customer = self.repository.get_by_id(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente não encontrado.")

        if customer_in.email:
            email_clean = customer_in.email.strip().lower()
            conflict = self.repository.get_by_email(email_clean)
            if conflict and conflict.id != customer_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Outro cliente já utiliza este e-mail."
                )
            customer.email = email_clean

        if customer_in.name:
            customer.name = customer_in.name.strip()

        if customer_in.phone is not None:
            customer.phone = customer_in.phone.strip() or None

        if customer_in.cpf is not None:
            customer.cpf = customer_in.cpf.strip() or None

        if customer_in.is_active is not None:
            customer.is_active = customer_in.is_active

        customer.updated_at = datetime.now(timezone.utc)
        return self.repository.save(customer)

    def toggle_status(self, customer_id: str, status_in: CustomerStatusUpdate) -> Customer:
        customer = self.repository.get_by_id(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente não encontrado.")

        customer.is_active = status_in.is_active
        customer.updated_at = datetime.now(timezone.utc)
        return self.repository.save(customer)

    def delete_customer(self, customer_id: str) -> dict:
        customer = self.repository.get_by_id(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente não encontrado.")

        self.db.query(Booking).filter(Booking.customer_id == customer_id).update({"customer_id": None})
        self.repository.delete(customer)
        return {"success": True, "message": "Cliente removido com sucesso."}

    def update_notifications(self, customer: Customer, prefs: CustomerUpdateNotifications) -> Customer:
        if prefs.whatsappPromotions is not None:
            customer.notification_whatsapp_promotions = prefs.whatsappPromotions
        if prefs.emailPromotions is not None:
            customer.notification_email_promotions = prefs.emailPromotions

        customer.notification_updated_at = datetime.now(timezone.utc)
        return self.repository.save(customer)

    def update_profile(self, customer: Customer, profile_data: CustomerUpdateProfile) -> Customer:
        if profile_data.name:
            customer.name = profile_data.name.strip()
        if profile_data.phone is not None:
            customer.phone = profile_data.phone.strip()

        return self.repository.save(customer)

    # ------------------------------------------------------------------
    # LGPD (Lei 13.709/2018) - Direitos do Titular
    # ------------------------------------------------------------------

    def record_consent(
        self, customer: Customer, consent_in: CustomerConsentUpdate, ip_address: Optional[str]
    ) -> Dict[str, Any]:
        """Art. 8º: consentimento livre, informado, inequívoco e com prova (data, versão, IP)."""
        now = datetime.now(timezone.utc)
        customer.accepted_privacy_policy = consent_in.acceptedPrivacyPolicy
        customer.accepted_terms_of_use = consent_in.acceptedTermsOfUse
        customer.consent_version = consent_in.version
        customer.consent_at = now
        customer.consent_ip = ip_address
        if consent_in.whatsappPromotions is not None:
            customer.notification_whatsapp_promotions = consent_in.whatsappPromotions
            customer.notification_updated_at = now
        if consent_in.emailPromotions is not None:
            customer.notification_email_promotions = consent_in.emailPromotions
            customer.notification_updated_at = now
        self.repository.save(customer)
        return {"consent": customer.consent, "notifications": customer.notifications}

    def export_personal_data(self, customer: Customer) -> Dict[str, Any]:
        """Art. 18 II e V: confirmação, acesso e portabilidade em formato estruturado (JSON)."""
        from app.features.bookings.app.services import BookingService
        from app.features.chat.infra.models import ChatLog

        bookings = (
            self.db.query(Booking)
            .filter(Booking.customer_id == customer.id)
            .order_by(Booking.created_at.desc())
            .all()
        )
        chats = (
            self.db.query(ChatLog)
            .filter(ChatLog.customer_id == customer.id)
            .order_by(ChatLog.created_at.asc())
            .all()
        )
        return {
            "exportedAt": datetime.now(timezone.utc).isoformat(),
            "controller": {
                "name": "Zarpou Viagens e Turismo Ltda",
                "contact": "privacidade@zarpouviagens.com.br",
            },
            "profile": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "cpf": customer.cpf,
                "birthDate": customer.birth_date.isoformat() if customer.birth_date else None,
                "createdAt": customer.created_at.isoformat() if customer.created_at else None,
                "updatedAt": customer.updated_at.isoformat() if customer.updated_at else None,
            },
            "consent": {**customer.consent, "ipAddress": customer.consent_ip},
            "notifications": customer.notifications,
            "security": {
                "twoFactorEnabled": customer.twoFactorEnabled,
                "twoFactorMethod": customer.twoFactorMethod,
            },
            "bookings": [BookingService.format_booking(b) for b in bookings],
            "chatHistory": [
                {
                    "sessionId": c.session_id,
                    "role": c.role,
                    "content": c.content,
                    "createdAt": c.created_at.isoformat() if c.created_at else None,
                }
                for c in chats
            ],
        }

    def anonymize_customer(self, customer: Customer, delete_in: CustomerDeleteRequest) -> Dict[str, Any]:
        """
        Art. 18 IV/VI: eliminação/anonimização dos dados pessoais.
        Registros de reservas e pagamentos são mantidos (Art. 16 I - obrigação legal/fiscal),
        porém desvinculados de dados de contato identificáveis.
        """
        from datetime import date as date_cls
        from app.features.bookings.infra.models import BookingTraveler
        from app.features.chat.infra.models import ChatLog
        from app.core.security import verify_password

        if not delete_in.confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirme a exclusão definitiva da conta enviando 'confirm': true.",
            )
        if customer.password_hash and not (
            delete_in.password and verify_password(delete_in.password, customer.password_hash)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha incorreta. Informe sua senha atual para excluir a conta.",
            )

        # Viagens futuras ativas impedem a exclusão (o titular precisa dos vouchers)
        today = date_cls.today()
        active_trip = (
            self.db.query(Booking)
            .filter(
                Booking.customer_id == customer.id,
                Booking.status.in_(["confirmada", "pendente_pagamento"]),
                Booking.check_in_date != None,  # noqa: E711
                Booking.check_in_date >= today,
            )
            .first()
        )
        if active_trip:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Existe uma viagem ativa ({active_trip.locator_code}). "
                       "Cancele-a ou aguarde sua conclusão antes de excluir a conta.",
            )

        anon_tag = f"anon-{customer.id}"
        booking_ids = [b.id for b in self.db.query(Booking.id).filter(Booking.customer_id == customer.id).all()]
        if booking_ids:
            self.db.query(BookingTraveler).filter(BookingTraveler.booking_id.in_(booking_ids)).update(
                {
                    BookingTraveler.email: f"{anon_tag}@anonimizado.com",
                    BookingTraveler.phone: "0000000000",
                },
                synchronize_session=False,
            )

        # Histórico do concierge pode conter dados pessoais livres -> eliminado
        self.db.query(ChatLog).filter(ChatLog.customer_id == customer.id).delete(synchronize_session=False)

        now = datetime.now(timezone.utc)
        customer.name = "Titular Anonimizado"
        customer.email = f"{anon_tag}@anonimizado.com"
        customer.phone = None
        customer.cpf = None
        customer.birth_date = None
        customer.password_hash = None
        customer.is_active = False
        customer.notification_whatsapp_promotions = False
        customer.notification_email_promotions = False
        customer.two_factor_enabled = False
        customer.two_factor_secret = None
        customer.two_factor_backup_codes = None
        customer.two_factor_temp_code = None
        customer.two_factor_temp_code_expires_at = None
        customer.consent_ip = None
        customer.anonymized_at = now
        self.repository.save(customer)

        return {
            "success": True,
            "message": "Conta excluída. Seus dados pessoais foram anonimizados conforme a LGPD.",
            "anonymizedAt": now.isoformat(),
            "retainedRecords": len(booking_ids),
        }
