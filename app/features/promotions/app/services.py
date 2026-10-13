from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.features.customers.infra.models import Customer
from app.features.promotions.infra.models import Promotion
from app.features.promotions.infra.repositories import PromotionRepository
from app.features.promotions.app.schemas import PromotionCreate, PromotionUpdate


def send_promotion_notifications_task(
    title: str,
    subtitle: Optional[str],
    badge: Optional[str],
    discount_text: Optional[str],
    link: str,
    image_url: Optional[str],
    promo_id: str,
) -> None:
    """
    Trigger assíncrono em background para disparar a notificação da nova promoção
    aos viajantes que deram opt-in de WhatsApp e E-mail.
    """
    from app.core.database import SessionLocal
    import httpx

    db = SessionLocal()
    try:
        email_customers = (
            db.query(Customer)
            .filter(
                Customer.is_active == True,
                Customer.notification_email_promotions == True,
            )
            .all()
        )

        whatsapp_customers = (
            db.query(Customer)
            .filter(
                Customer.is_active == True,
                Customer.phone.isnot(None),
                Customer.notification_whatsapp_promotions == True,
            )
            .all()
        )

        from app.features.agency.infra.models import AgencySetting
        agency = db.query(AgencySetting).filter(AgencySetting.id == "default").first()

        full_link = f"https://www.zarpouviagens.com.br{link}" if link.startswith("/") else link
        badge_text = badge or "OFERTA EXCLUSIVA"
        discount = discount_text or "Descontos Especiais"

        api_key = (agency.resend_api_key if agency and agency.resend_api_key else None) or settings.RESEND_API_KEY
        if api_key and email_customers:
            try:
                for customer in email_customers:
                    first_name = customer.name.split()[0] if customer.name else "Viajante"
                    html_content = f"""
                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 18px; background-color: #ffffff;">
                      <div style="background: linear-gradient(135deg, #003366 0%, #001f3f 100%); padding: 24px; text-align: center; border-radius: 14px;">
                        <span style="background-color: #ebb343; color: #003366; font-size: 11px; font-weight: 800; padding: 4px 12px; border-radius: 20px; text-transform: uppercase;">{badge_text}</span>
                        <h1 style="color: #ffffff; margin: 12px 0 6px 0; font-size: 22px;">{title}</h1>
                        <p style="color: #ebb343; font-weight: bold; font-size: 18px; margin: 0;">{discount}</p>
                      </div>
                      <div style="padding: 24px 12px; color: #334155; line-height: 1.6;">
                        <p>Olá, <strong>{first_name}</strong>!</p>
                        <p>A Zarpou Viagens preparou uma nova oferta imperdível para sua próxima viagem:</p>
                        {f'<p style="background: #f8fafc; padding: 14px; border-left: 4px solid #003366; border-radius: 8px; font-style: italic;">{subtitle}</p>' if subtitle else ''}
                        <div style="text-align: center; margin: 28px 0;">
                          <a href="{full_link}" style="background-color: #003366; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 12px; font-weight: bold; font-size: 15px; display: inline-block;">Ver Oferta na Zarpou →</a>
                        </div>
                        <p style="font-size: 11px; color: #94a3b8; margin-top: 30px; text-align: center;">
                          Você está recebendo este e-mail porque se cadastrou na Zarpou Viagens e aceitou receber novidades e promoções.
                          Para alterar suas preferências, acesse <a href="https://www.zarpouviagens.com.br/minhas-viagens?tab=perfil" style="color: #003366;">Meu Perfil</a>.
                        </p>
                      </div>
                    </div>
                    """
                    with httpx.Client(timeout=8.0) as client:
                        client.post(
                            "https://api.resend.com/emails",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "from": "Zarpou Viagens <ofertas@zarpouviagens.com.br>",
                                "to": [customer.email],
                                "subject": f"✈️ Nova Oferta Zarpou: {title} ({discount})",
                                "html": html_content,
                            },
                        )
            except Exception as email_err:
                print(f"[Zarpou Promo Email Error]: {email_err}")

        if whatsapp_customers:
            wa_enabled = bool(agency and agency.whatsapp_api_enabled)
            wa_token = (agency.whatsapp_api_token if agency else None) or getattr(settings, "WHATSAPP_API_TOKEN", None)
            wa_phone_id = agency.whatsapp_phone_number_id if agency else None
            wa_url = agency.whatsapp_api_url if agency and agency.whatsapp_api_url else "https://graph.facebook.com/v19.0"

            for customer in whatsapp_customers:
                clean_phone = "".join(filter(str.isdigit, customer.phone or ""))
                if clean_phone.startswith("55") is False and len(clean_phone) in [10, 11]:
                    clean_phone = f"55{clean_phone}"
                first_name = customer.name.split()[0] if customer.name else "Viajante"
                wa_msg = (
                    f"✈️ *ZARPOU VIAGENS | {badge_text}*\n\n"
                    f"Olá {first_name}! Uma nova promoção exclusiva acaba de ser lançada:\n\n"
                    f"🔥 *{title}*\n"
                    f"🏷️ *Desconto:* {discount}\n\n"
                    f"👉 Aproveite agora no link:\n{full_link}\n\n"
                    f"_Para gerenciar preferências de mensagens, acesse seu perfil no site da Zarpou._"
                )

                if wa_enabled and wa_token and wa_phone_id:
                    # Envio real via Meta Cloud API
                    try:
                        meta_url = f"{wa_url.rstrip('/')}/{wa_phone_id}/messages"
                        with httpx.Client(timeout=6.0) as client:
                            res = client.post(
                                meta_url,
                                headers={
                                    "Authorization": f"Bearer {wa_token}",
                                    "Content-Type": "application/json",
                                },
                                json={
                                    "messaging_product": "whatsapp",
                                    "recipient_type": "individual",
                                    "to": clean_phone,
                                    "type": "text",
                                    "text": {"preview_url": True, "body": wa_msg},
                                },
                            )
                            if res.status_code not in [200, 201]:
                                print(f"[WhatsApp Meta API Error {res.status_code}]: {res.text}")
                    except Exception as wa_err:
                        print(f"[Zarpou Promo WA Error]: {wa_err}")
                elif wa_enabled and wa_token and not wa_phone_id:
                    print(f"[WhatsApp Trigger] API WhatsApp está ativa, mas falta preencher o 'ID do Número de Telefone' em /admin/configuracoes. Simulação para {customer.name} ({clean_phone}).")
                else:
                    print(f"[WhatsApp Trigger] API do WhatsApp está DESATIVADA no painel (/admin/configuracoes). Para envio real, ative a chave 'API Ativa' e insira as credenciais da Meta/Evolution. Simulação para {customer.name} ({clean_phone}): {title}")

        print(
            f"[Zarpou Promotion Trigger] Concluído: Promoção '{title}' ({promo_id}) processada para "
            f"{len(email_customers)} clientes por e-mail e {len(whatsapp_customers)} por WhatsApp."
        )
    finally:
        db.close()


class PromotionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PromotionRepository(db)

    def list(self, active_only: bool = True) -> List[Promotion]:
        return self.repo.list(active_only=active_only)

    def get_by_id(self, promo_id: str) -> Promotion:
        promo = self.repo.get_by_id(promo_id)
        if not promo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promoção não encontrada."
            )
        return promo

    def create(
        self,
        promo_in: PromotionCreate,
        background_tasks: BackgroundTasks,
        notify_subscribers: bool = True,
    ) -> Promotion:
        promo_id = promo_in.id or f"promo-{int(datetime.now(timezone.utc).timestamp())}"
        promo = Promotion(id=promo_id, **promo_in.model_dump(exclude={"id"}))
        created = self.repo.create(promo)

        if notify_subscribers and created.active:
            created.notification_sent = True
            created.notification_sent_at = datetime.now(timezone.utc)
            self.repo.update(created)

            background_tasks.add_task(
                send_promotion_notifications_task,
                title=created.title,
                subtitle=created.subtitle,
                badge=created.badge,
                discount_text=created.discount_text,
                link=created.link,
                image_url=created.image_url,
                promo_id=created.id,
            )

        return created

    def update(self, promo_id: str, promo_in: PromotionUpdate) -> Promotion:
        promo = self.repo.get_by_id(promo_id)
        if not promo:
            data = promo_in.model_dump(exclude_unset=True)
            new_promo = Promotion(
                id=promo_id,
                title=data.get("title", "Nova Promoção"),
                subtitle=data.get("subtitle"),
                badge=data.get("badge"),
                discount_text=data.get("discount_text"),
                image_url=data.get("image_url", ""),
                link=data.get("link", "/hospedagens"),
                button_text=data.get("button_text", "Aproveitar Oferta"),
                active=data.get("active", True),
                display_order=data.get("display_order", 0),
                notification_sent=data.get("notification_sent", False),
                notification_sent_at=data.get("notification_sent_at"),
            )
            return self.repo.create(new_promo)

        for field, val in promo_in.model_dump(exclude_unset=True).items():
            setattr(promo, field, val)
        return self.repo.update(promo)

    def toggle(self, promo_id: str) -> Promotion:
        promo = self.get_by_id(promo_id)
        promo.active = not promo.active
        return self.repo.update(promo)

    def notify_subscribers(self, promo_id: str, background_tasks: BackgroundTasks, force: bool = False) -> Dict[str, Any]:
        promo = self.get_by_id(promo_id)
        if promo.notification_sent and not force:
            return {
                "success": True,
                "already_sent": True,
                "message": f"A notificação desta promoção já foi disparada anteriormente ({promo.notification_sent_at})."
            }

        promo.notification_sent = True
        promo.notification_sent_at = datetime.now(timezone.utc)
        self.repo.update(promo)

        background_tasks.add_task(
            send_promotion_notifications_task,
            title=promo.title,
            subtitle=promo.subtitle,
            badge=promo.badge,
            discount_text=promo.discount_text,
            link=promo.link,
            image_url=promo.image_url,
            promo_id=promo.id,
        )
        return {
            "success": True,
            "message": f"Disparo de notificações iniciado para a promoção '{promo.title}'."
        }

    def delete(self, promo_id: str) -> None:
        promo = self.get_by_id(promo_id)
        self.repo.delete(promo)
