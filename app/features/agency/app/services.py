from sqlalchemy.orm import Session
from typing import Optional
from app.features.agency.infra.repositories import SqlAlchemyAgencyRepository
from app.features.agency.app.schemas import (
    AgencySettingSchema,
    WhatsAppApiConfigSchema,
    PaymentGatewayConfigSchema,
    PaymentActiveMethodsSchema,
    AiChatConfigSchema,
    StorageBucketConfigSchema,
    HeroConfigSchema,
    DashboardMetrics,
)
from app.models.hotel import Hotel
from app.models.flight import Flight
from app.models.booking import Booking
from app.models.promotion import Promotion
from app.models.inquiry import ContactInquiry

# Máscara retornada no lugar de credenciais sensíveis (chaves de API, tokens e secrets).
# O valor real nunca sai do banco; se o painel reenviar a máscara no PUT, o segredo armazenado é preservado.
SECRET_MASK = "••••••••"


def _mask_secret(value) -> str:
    """Retorna a máscara quando o segredo existe; string vazia quando não configurado."""
    return SECRET_MASK if value else ""


def _keep_secret(new_value: Optional[str], current_value: Optional[str]) -> Optional[str]:
    """Preserva o valor armazenado quando o cliente reenvia a máscara sem alterações."""
    return current_value if new_value == SECRET_MASK else new_value


class AgencyService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = SqlAlchemyAgencyRepository(db)

    def get_settings(self) -> AgencySettingSchema:
        setting = self.repository.get_or_create_settings()
        return AgencySettingSchema(
            companyName=setting.company_name or "Zarpou Viagens e Turismo Ltda",
            tradingName=setting.trading_name or "Zarpou Viagens",
            cnpj=setting.cnpj or "55.849.201/0001-38",
            cadastur=setting.cadastur or "34.120.948/0001-90",
            whatsapp=setting.whatsapp or "5531984210000",
            whatsappMessage=setting.whatsapp_message or "Olá! Gostaria de planejar minha próxima viagem com a Zarpou.",
            email=setting.email or "contato@zarpouviagens.com.br",
            phone=setting.phone or "(31) 3245-8900",
            instagram=setting.instagram or "zarpouviagens",
            linkedin=setting.linkedin or "zarpouviagens",
            address=setting.address or "Belo Horizonte - MG, Brasil",
            termsAndConditions=setting.terms_and_conditions,
            privacyPolicy=setting.privacy_policy,
            resendApiKey=_mask_secret(setting.resend_api_key),
            whatsappApi=WhatsAppApiConfigSchema(
                provider=setting.whatsapp_api_provider or "meta_cloud",
                enabled=bool(setting.whatsapp_api_enabled),
                apiToken=_mask_secret(setting.whatsapp_api_token),
                phoneNumberId=setting.whatsapp_phone_number_id or "",
                businessAccountId=setting.whatsapp_business_account_id or "",
                apiUrl=setting.whatsapp_api_url or "https://graph.facebook.com/v19.0",
            ),
            paymentGateway=PaymentGatewayConfigSchema(
                provider=setting.payment_gateway_provider or "mercadopago",
                environment=setting.payment_environment or "sandbox",
                publicKey=setting.payment_public_key or "",
                secretKey=_mask_secret(setting.payment_secret_key),
                pixKey=setting.payment_pix_key or "",
                webhookSecret=_mask_secret(setting.payment_webhook_secret),
                activeMethods=PaymentActiveMethodsSchema(
                    creditCard=bool(setting.payment_active_credit_card),
                    pix=bool(setting.payment_active_pix),
                    boleto=bool(setting.payment_active_boleto),
                ),
            ),
            aiChat=AiChatConfigSchema(
                enabled=bool(setting.ai_chat_enabled),
                provider=setting.ai_chat_provider or "openai",
                apiKey=_mask_secret(setting.ai_chat_api_key),
                model=setting.ai_chat_model or "gpt-4o-mini",
                systemPrompt=setting.ai_chat_system_prompt or "Você é o Concierge Virtual da Zarpou Viagens e Turismo.",
                welcomeMessage=setting.ai_chat_welcome_message or "Olá! 👋 Sou o Concierge Virtual da Zarpou Viagens. Como posso ajudar com sua próxima viagem hoje?",
            ),
            storageBucket=StorageBucketConfigSchema(
                provider=setting.storage_provider or "aws_s3",
                enabled=bool(setting.storage_enabled),
                bucketName=setting.storage_bucket_name or "",
                region=setting.storage_region or "sa-east-1",
                accessKeyId=_mask_secret(setting.storage_access_key_id),
                secretAccessKey=_mask_secret(setting.storage_secret_access_key),
                endpointUrl=setting.storage_endpoint_url or "",
                publicUrlPrefix=setting.storage_public_url_prefix or "",
            ),
        )

    def update_settings(self, data: AgencySettingSchema) -> AgencySettingSchema:
        setting = self.repository.get_or_create_settings()
        setting.company_name = data.companyName
        setting.trading_name = data.tradingName
        setting.cnpj = data.cnpj
        setting.cadastur = data.cadastur
        setting.whatsapp = data.whatsapp
        setting.whatsapp_message = data.whatsappMessage
        setting.email = data.email
        setting.phone = data.phone
        setting.instagram = data.instagram
        setting.linkedin = data.linkedin
        setting.address = data.address
        setting.terms_and_conditions = data.termsAndConditions
        setting.privacy_policy = data.privacyPolicy

        setting.resend_api_key = _keep_secret(data.resendApiKey, setting.resend_api_key)
        setting.whatsapp_api_provider = data.whatsappApi.provider
        setting.whatsapp_api_enabled = data.whatsappApi.enabled
        setting.whatsapp_api_token = _keep_secret(data.whatsappApi.apiToken, setting.whatsapp_api_token)
        setting.whatsapp_phone_number_id = data.whatsappApi.phoneNumberId
        setting.whatsapp_business_account_id = data.whatsappApi.businessAccountId
        setting.whatsapp_api_url = data.whatsappApi.apiUrl

        setting.payment_gateway_provider = data.paymentGateway.provider
        setting.payment_environment = data.paymentGateway.environment
        setting.payment_public_key = data.paymentGateway.publicKey
        setting.payment_secret_key = _keep_secret(data.paymentGateway.secretKey, setting.payment_secret_key)
        setting.payment_pix_key = data.paymentGateway.pixKey
        setting.payment_webhook_secret = _keep_secret(data.paymentGateway.webhookSecret, setting.payment_webhook_secret)
        setting.payment_active_credit_card = data.paymentGateway.activeMethods.creditCard
        setting.payment_active_pix = data.paymentGateway.activeMethods.pix
        setting.payment_active_boleto = data.paymentGateway.activeMethods.boleto

        setting.ai_chat_enabled = data.aiChat.enabled
        setting.ai_chat_provider = data.aiChat.provider
        setting.ai_chat_api_key = _keep_secret(data.aiChat.apiKey, setting.ai_chat_api_key)
        setting.ai_chat_model = data.aiChat.model
        setting.ai_chat_system_prompt = data.aiChat.systemPrompt
        setting.ai_chat_welcome_message = data.aiChat.welcomeMessage

        setting.storage_provider = data.storageBucket.provider
        setting.storage_enabled = data.storageBucket.enabled
        setting.storage_bucket_name = data.storageBucket.bucketName
        setting.storage_region = data.storageBucket.region
        setting.storage_access_key_id = _keep_secret(data.storageBucket.accessKeyId, setting.storage_access_key_id)
        setting.storage_secret_access_key = _keep_secret(data.storageBucket.secretAccessKey, setting.storage_secret_access_key)
        setting.storage_endpoint_url = data.storageBucket.endpointUrl
        setting.storage_public_url_prefix = data.storageBucket.publicUrlPrefix

        self.db.commit()
        self.db.refresh(setting)
        return data

    def get_hero_config(self) -> HeroConfigSchema:
        hero = self.repository.get_or_create_hero()
        return HeroConfigSchema(
            titlePrefix=hero.title_prefix or "",
            titleHighlight=hero.title_highlight or "",
            titleSuffix=hero.title_suffix or "",
            subtitle=hero.subtitle or "",
            bgType=hero.bg_type or "video",
            bgImageUrl=hero.bg_image_url,
            bgVideoUrl=hero.bg_video_url,
            ctaText=hero.cta_text or "Falar com um Especialista",
            ctaLink=hero.cta_link or "whatsapp",
        )

    def update_hero_config(self, data: HeroConfigSchema) -> HeroConfigSchema:
        hero = self.repository.get_or_create_hero()
        hero.title_prefix = data.titlePrefix
        hero.title_highlight = data.titleHighlight
        hero.title_suffix = data.titleSuffix
        hero.subtitle = data.subtitle
        hero.bg_type = data.bgType
        hero.bg_image_url = data.bgImageUrl
        hero.bg_video_url = data.bgVideoUrl
        hero.cta_text = data.ctaText
        hero.cta_link = data.ctaLink

        self.db.commit()
        return data

    def get_dashboard_metrics(self) -> DashboardMetrics:
        bookings = self.db.query(Booking).all()
        total_revenue = sum(float(b.final_amount or 0.0) for b in bookings)
        total_bookings = len(bookings)
        pending_bookings = sum(1 for b in bookings if b.status == "pendente_pagamento")
        confirmed_bookings = sum(1 for b in bookings if b.status == "confirmada")

        active_promos = self.db.query(Promotion).filter(Promotion.active == True).count()
        hotels_count = self.db.query(Hotel).filter(Hotel.is_active == True).count()
        flights_count = self.db.query(Flight).filter(Flight.is_active == True).count()
        inquiries_count = self.db.query(ContactInquiry).count()

        return DashboardMetrics(
            totalRevenue=total_revenue,
            totalBookings=total_bookings,
            activePromotions=active_promos,
            totalProducts=hotels_count + flights_count,
            pendingBookings=pending_bookings,
            confirmedBookings=confirmed_bookings,
            totalInquiries=inquiries_count,
        )
