from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Text
from app.core.database import Base


class AgencySetting(Base):
    __tablename__ = "agency_settings"

    id = Column(String(50), primary_key=True, default="default")
    company_name = Column(String(255), nullable=False, default="Zarpou Viagens e Turismo Ltda")
    trading_name = Column(String(255), nullable=False, default="Zarpou Viagens")
    cnpj = Column(String(30), nullable=False, default="55.849.201/0001-38")
    cadastur = Column(String(30), nullable=False, default="34.120.948/0001-90")
    whatsapp = Column(String(30), nullable=False, default="5531984210000")
    whatsapp_message = Column(
        Text,
        nullable=True,
        default="Olá! Gostaria de falar com um especialista da Zarpou Viagens."
    )
    email = Column(String(255), nullable=False, default="contato@zarpou.com.br")
    phone = Column(String(30), nullable=False, default="(31) 3344-5500")
    instagram = Column(String(255), nullable=True, default="https://instagram.com/zarpouviagens")
    linkedin = Column(String(255), nullable=True, default="https://linkedin.com/company/zarpouviagens")
    address = Column(
        Text,
        nullable=True,
        default="Av. do Contorno, 6500 - Savassi, Belo Horizonte - MG, 30110-044"
    )
    terms_and_conditions = Column(Text, nullable=True)
    privacy_policy = Column(Text, nullable=True)
    resend_api_key = Column(String(255), nullable=True)

    # WhatsApp API
    whatsapp_api_provider = Column(String(50), nullable=False, default="meta_cloud")
    whatsapp_api_enabled = Column(Boolean, nullable=False, default=False)
    whatsapp_api_token = Column(Text, nullable=True)
    whatsapp_phone_number_id = Column(String(100), nullable=True)
    whatsapp_business_account_id = Column(String(100), nullable=True)
    whatsapp_api_url = Column(String(255), nullable=False, default="https://graph.facebook.com/v19.0")

    # Gateway Pagamentos
    payment_gateway_provider = Column(String(50), nullable=False, default="mercadopago")
    payment_environment = Column(String(20), nullable=False, default="sandbox")
    payment_public_key = Column(Text, nullable=True)
    payment_secret_key = Column(Text, nullable=True)
    payment_pix_key = Column(String(100), nullable=True)
    payment_webhook_secret = Column(Text, nullable=True)
    payment_active_credit_card = Column(Boolean, nullable=False, default=True)
    payment_active_pix = Column(Boolean, nullable=False, default=True)
    payment_active_boleto = Column(Boolean, nullable=False, default=True)

    # IA Concierge Virtual
    ai_chat_enabled = Column(Boolean, nullable=False, default=True)
    ai_chat_provider = Column(String(50), nullable=False, default="openai")
    ai_chat_api_key = Column(Text, nullable=True)
    ai_chat_model = Column(String(100), nullable=False, default="gpt-4o-mini")
    ai_chat_system_prompt = Column(
        Text,
        nullable=True,
        default="Você é o Concierge Virtual da Zarpou Viagens e Turismo. Atenda com calor humano, sofisticação e objetividade."
    )
    ai_chat_welcome_message = Column(
        Text,
        nullable=True,
        default="Olá! Sou o Concierge Virtual da Zarpou Viagens. Como posso ajudar com sua próxima viagem hoje?"
    )

    # Storage Bucket (AWS S3 / Supabase / R2)
    storage_provider = Column(String(50), nullable=False, default="aws_s3")
    storage_enabled = Column(Boolean, nullable=False, default=True)
    storage_bucket_name = Column(String(255), nullable=True, default="")
    storage_region = Column(String(100), nullable=True, default="sa-east-1")
    storage_access_key_id = Column(Text, nullable=True)
    storage_secret_access_key = Column(Text, nullable=True)
    storage_endpoint_url = Column(Text, nullable=True)
    storage_public_url_prefix = Column(Text, nullable=True)

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class HeroConfig(Base):
    __tablename__ = "hero_configs"

    id = Column(String(50), primary_key=True, default="default")
    title_prefix = Column(String(100), nullable=True, default="Seu")
    title_highlight = Column(String(100), nullable=True, default="sonho")
    title_suffix = Column(String(255), nullable=True, default="de viajar bem, agora é realidade")
    subtitle = Column(
        Text,
        nullable=True,
        default="Reserve hotéis, passagens aéreas e pacotes com pagamento em até 12x sem juros e atendimento humano especializado."
    )
    bg_type = Column(String(20), nullable=False, default="video")  # 'image' ou 'video'
    bg_image_url = Column(Text, nullable=True)
    bg_video_url = Column(Text, nullable=True)
    cta_text = Column(String(100), nullable=False, default="Falar com um Especialista")
    cta_link = Column(String(255), nullable=False, default="whatsapp")
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
