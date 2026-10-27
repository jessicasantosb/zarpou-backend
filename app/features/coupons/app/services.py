from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.features.coupons.infra.models import Coupon
from app.features.coupons.infra.repositories import CouponRepository
from app.features.coupons.app.schemas import CouponCreate, CouponUpdate
from app.features.coupons.app.coupon_code import generate_unique_coupon_code


def send_coupon_notifications_task(
    code: str,
    description: Optional[str],
    discount_type: str,
    discount_value: float,
    valid_to: Optional[str],
    coupon_id: str,
) -> None:
    """
    Trigger assíncrono em background para disparar a notificação do cupom
    aos viajantes que deram opt-in de WhatsApp e E-mail.
    """
    from app.core.database import SessionLocal
    import httpx

    db = SessionLocal()
    try:
        from app.features.customers.infra.models import Customer

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

        site_link = f"https://www.zarpouviagens.com.br/?cupom={code}"
        if discount_type == "percent":
            discount_label = f"{discount_value:g}% de desconto"
        else:
            discount_label = f"R$ {discount_value:.2f} de desconto"

        validity_line = "Sem prazo de validade"
        if valid_to:
            try:
                validity_line = f"Válido até {datetime.fromisoformat(valid_to).strftime('%d/%m/%Y')}"
            except Exception:
                validity_line = f"Válido até {valid_to}"

        api_key = (agency.resend_api_key if agency and agency.resend_api_key else None) or settings.RESEND_API_KEY
        if api_key and email_customers:
            try:
                for customer in email_customers:
                    first_name = customer.name.split()[0] if customer.name else "Viajante"
                    description_block = (
                        f'<p style="background: #f8fafc; padding: 14px; border-left: 4px solid #003366; border-radius: 8px; font-style: italic;">{description}</p>'
                        if description else ''
                    )
                    html_content = f"""
                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 18px; background-color: #ffffff;">
                      <div style="background: linear-gradient(135deg, #003366 0%, #001f3f 100%); padding: 24px; text-align: center; border-radius: 14px;">
                        <span style="background-color: #ebb343; color: #003366; font-size: 11px; font-weight: 800; padding: 4px 12px; border-radius: 20px; text-transform: uppercase;">CUPOM EXCLUSIVO</span>
                        <h1 style="color: #ffffff; margin: 12px 0 6px 0; font-size: 22px;">Cupom {code}</h1>
                        <p style="color: #ebb343; font-weight: bold; font-size: 18px; margin: 0;">{discount_label}</p>
                      </div>
                      <div style="padding: 24px 12px; color: #334155; line-height: 1.6;">
                        <p>Olá, <strong>{first_name}</strong>!</p>
                        <p>A Zarpou Viagens preparou um cupom de desconto exclusivo para a sua próxima viagem:</p>
                        {description_block}
                        <div style="text-align: center; margin: 24px 0;">
                          <span style="display: inline-block; font-family: 'Courier New', monospace; font-size: 28px; font-weight: 800; letter-spacing: 6px; color: #003366; background-color: #f8fafc; border: 2px dashed #ebb343; border-radius: 12px; padding: 16px 28px;">{code}</span>
                          <p style="font-size: 13px; color: #64748b; margin: 12px 0 0 0;">Use este código na tela de pagamento para aplicar o desconto.</p>
                          <p style="font-size: 12px; color: #94a3b8; margin: 4px 0 0 0;">{validity_line}</p>
                        </div>
                        <div style="text-align: center; margin: 28px 0;">
                          <a href="{site_link}" style="background-color: #003366; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 12px; font-weight: bold; font-size: 15px; display: inline-block;">Usar cupom na Zarpou →</a>
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
                                "subject": f"🎟️ Cupom {code} liberado: {discount_label} na Zarpou",
                                "html": html_content,
                            },
                        )
            except Exception as email_err:
                print(f"[Zarpou Coupon Email Error]: {email_err}")

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
                    f"🎟️ *ZARPOU VIAGENS | CUPOM EXCLUSIVO*\n\n"
                    f"Olá {first_name}! Liberamos um cupom de desconto só para você:\n\n"
                    f"🔑 *Código:* `{code}`\n"
                    f"🏷️ *Benefício:* {discount_label}\n"
                    f"📅 {validity_line}\n\n"
                    f"👉 Use o código na tela de pagamento:\n{site_link}\n\n"
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
                        print(f"[Zarpou Coupon WA Error]: {wa_err}")
                elif wa_enabled and wa_token and not wa_phone_id:
                    print(f"[WhatsApp Trigger] API WhatsApp está ativa, mas falta preencher o 'ID do Número de Telefone' em /admin/configuracoes. Simulação para {customer.name} ({clean_phone}).")
                else:
                    print(f"[WhatsApp Trigger] API do WhatsApp está DESATIVADA no painel (/admin/configuracoes). Para envio real, ative a chave 'API Ativa' e insira as credenciais da Meta/Evolution. Simulação para {customer.name} ({clean_phone}): cupom {code}")

        print(
            f"[Zarpou Coupon Trigger] Concluído: Cupom '{code}' ({coupon_id}) processado para "
            f"{len(email_customers)} clientes por e-mail e {len(whatsapp_customers)} por WhatsApp."
        )
    finally:
        db.close()


class CouponService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CouponRepository(db)

    def list(self, active_only: bool = False, search: Optional[str] = None) -> List[Coupon]:
        return self.repo.list(active_only=active_only, search=search)

    def get_by_id(self, coupon_id: str) -> Coupon:
        coupon = self.repo.get_by_id(coupon_id)
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cupom não encontrado."
            )
        return coupon

    def create(self, coupon_in: CouponCreate, created_by: Optional[str] = None) -> Coupon:
        self._validate_business_rules(
            discount_type=coupon_in.discount_type,
            discount_value=coupon_in.discount_value,
            valid_from=coupon_in.valid_from,
            valid_to=coupon_in.valid_to,
        )

        if self.repo.get_by_code(coupon_in.code):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Já existe um cupom cadastrado com o código '{coupon_in.code}'."
            )

        coupon_id = coupon_in.id or f"cpn-{int(datetime.now(timezone.utc).timestamp())}"
        coupon = Coupon(
            id=coupon_id,
            code=coupon_in.code,
            description=coupon_in.description,
            discount_type=coupon_in.discount_type,
            discount_value=coupon_in.discount_value,
            min_order_amount=coupon_in.min_order_amount,
            max_uses=coupon_in.max_uses,
            used_count=0,
            per_customer_limit=coupon_in.per_customer_limit,
            valid_from=coupon_in.valid_from,
            valid_to=coupon_in.valid_to,
            active=coupon_in.active,
            created_by=created_by,
        )
        return self.repo.create(coupon)

    def update(self, coupon_id: str, coupon_in: CouponUpdate) -> Coupon:
        coupon = self.repo.get_by_id(coupon_id)
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cupom não encontrado."
            )

        data = coupon_in.model_dump(exclude_unset=True)

        if "code" in data and data["code"] != coupon.code:
            existing = self.repo.get_by_code(data["code"])
            if existing and existing.id != coupon.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Já existe um cupom cadastrado com o código '{data['code']}'."
                )

        self._validate_business_rules(
            discount_type=data.get("discount_type", coupon.discount_type),
            discount_value=data.get("discount_value", float(coupon.discount_value)),
            valid_from=data.get("valid_from", coupon.valid_from),
            valid_to=data.get("valid_to", coupon.valid_to),
        )

        if data.get("max_uses") is not None and data["max_uses"] < coupon.used_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"O limite total de usos ({data['max_uses']}) é menor que o número de usos já realizados ({coupon.used_count})."
            )

        for field, val in data.items():
            setattr(coupon, field, val)
        return self.repo.update(coupon)

    def toggle(self, coupon_id: str) -> Coupon:
        coupon = self.get_by_id(coupon_id)
        coupon.active = not coupon.active
        return self.repo.update(coupon)

    def generate(self, prefix: Optional[str] = None, length: int = 10) -> Dict[str, str]:
        """Gera um código aleatório único, sempre em maiúsculas, para novo cupom."""
        code = generate_unique_coupon_code(self.db, prefix=prefix or "", length=length)
        return {"code": code}

    def validate_for_checkout(
        self,
        code: str,
        order_amount: Optional[float] = None,
        customer_email: Optional[str] = None,
        customer_id: Optional[str] = None,
    ):
        """
        Valida um cupom para uso no checkout (público). Levanta HTTP 400 com mensagem
        em pt-BR quando o cupom não pode ser usado. Retorna (cupom, valor_do_desconto).
        """
        clean_code = (code or "").strip().upper()
        if not clean_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe o código do cupom."
            )

        coupon = self.repo.get_by_code(clean_code)
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cupom '{clean_code}' não encontrado. Confira o código e tente novamente."
            )
        if not coupon.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este cupom está desativado e não pode ser usado."
            )

        today = date.today()
        if coupon.valid_from and today < coupon.valid_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este cupom ainda não está válido."
            )
        if coupon.valid_to and today > coupon.valid_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este cupom expirou."
            )
        if coupon.max_uses is not None and int(coupon.used_count or 0) >= int(coupon.max_uses):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este cupom atingiu o limite máximo de usos."
            )
        if (
            order_amount is not None
            and coupon.min_order_amount is not None
            and float(order_amount) < float(coupon.min_order_amount)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Este cupom exige pedido mínimo de R$ {float(coupon.min_order_amount):.2f}."
            )
        if customer_email or customer_id:
            uses = self._customer_usage_count(coupon, customer_id=customer_id, customer_email=customer_email)
            if uses >= int(coupon.per_customer_limit or 1):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Você já atingiu o limite de {int(coupon.per_customer_limit or 1)} uso(s) deste cupom."
                )

        return coupon, self.compute_discount(coupon, order_amount)

    def notify(
        self,
        coupon_id: str,
        background_tasks: BackgroundTasks,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Dispara manualmente a notificação do cupom (e-mail + WhatsApp) para clientes com opt-in."""
        coupon = self.get_by_id(coupon_id)
        if not coupon.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ative o cupom antes de enviar a notificação."
            )
        if coupon.notification_sent and not force:
            return {
                "success": True,
                "already_sent": True,
                "message": f"A notificação deste cupom já foi disparada anteriormente ({coupon.notification_sent_at})."
            }

        coupon.notification_sent = True
        coupon.notification_sent_at = datetime.now(timezone.utc)
        self.repo.update(coupon)

        background_tasks.add_task(
            send_coupon_notifications_task,
            code=coupon.code,
            description=coupon.description,
            discount_type=coupon.discount_type,
            discount_value=float(coupon.discount_value),
            valid_to=coupon.valid_to.isoformat() if coupon.valid_to else None,
            coupon_id=coupon.id,
        )
        return {
            "success": True,
            "message": f"Disparo de notificações iniciado para o cupom '{coupon.code}'."
        }

    def delete(self, coupon_id: str) -> None:
        coupon = self.get_by_id(coupon_id)
        self.repo.delete(coupon)

    @staticmethod
    def compute_discount(coupon: Coupon, order_amount: Optional[float]) -> float:
        """Calcula o valor do desconto do cupom sobre o valor do pedido."""
        if order_amount is None:
            return 0.0
        amount = round(float(order_amount), 2)
        if amount <= 0:
            return 0.0
        if coupon.discount_type == "percent":
            return round(amount * float(coupon.discount_value) / 100.0, 2)
        return min(round(float(coupon.discount_value), 2), amount)

    def _customer_usage_count(
        self,
        coupon: Coupon,
        customer_id: Optional[str] = None,
        customer_email: Optional[str] = None,
    ) -> int:
        """Conta os usos do cupom pelo cliente (por id ou e-mail do titular/viajante)."""
        from app.features.bookings.infra.models import Booking

        bookings = self.db.query(Booking).filter(Booking.coupon_code == coupon.code).all()
        email = (customer_email or "").strip().lower()
        count = 0
        for b in bookings:
            if customer_id and b.customer_id == customer_id:
                count += 1
                continue
            if email:
                if b.customer and (b.customer.email or "").lower() == email:
                    count += 1
                    continue
                if any((t.email or "").lower() == email for t in b.travelers):
                    count += 1
        return count

    @staticmethod
    def _validate_business_rules(
        discount_type: str,
        discount_value: float,
        valid_from: Optional[object],
        valid_to: Optional[object],
    ) -> None:
        if discount_type == "percent" and discount_value > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O desconto percentual não pode ser maior que 100%."
            )
        if valid_from and valid_to and valid_to < valid_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A data de término do cupom não pode ser anterior à data de início."
            )
