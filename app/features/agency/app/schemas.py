from typing import Optional
from pydantic import BaseModel


class HeroConfigSchema(BaseModel):
    titlePrefix: Optional[str] = ""
    titleHighlight: Optional[str] = ""
    titleSuffix: Optional[str] = ""
    subtitle: Optional[str] = ""
    bgType: str = "video"
    bgImageUrl: Optional[str] = None
    bgVideoUrl: Optional[str] = "/hero.mp4"
    ctaText: Optional[str] = "Falar com um Especialista"
    ctaLink: Optional[str] = "whatsapp"


class WhatsAppApiConfigSchema(BaseModel):
    provider: str = "meta_cloud"  # 'meta_cloud', 'evolution_api', 'z_api', 'other'
    enabled: bool = False
    apiToken: Optional[str] = ""
    phoneNumberId: Optional[str] = ""
    businessAccountId: Optional[str] = ""
    apiUrl: str = "https://graph.facebook.com/v19.0"


class PaymentActiveMethodsSchema(BaseModel):
    creditCard: bool = True
    pix: bool = True
    boleto: bool = True


class PaymentGatewayConfigSchema(BaseModel):
    provider: str = "mercadopago"  # 'mercadopago', 'asaas', 'pagarme', 'stripe', 'efi'
    environment: str = "sandbox"   # 'sandbox', 'production'
    publicKey: Optional[str] = ""
    secretKey: Optional[str] = ""
    pixKey: Optional[str] = ""
    webhookSecret: Optional[str] = ""
    activeMethods: PaymentActiveMethodsSchema = PaymentActiveMethodsSchema()


class AiChatConfigSchema(BaseModel):
    enabled: bool = True
    provider: str = "openai"       # 'openai', 'gemini', 'groq', 'anthropic', 'other'
    apiKey: Optional[str] = ""
    model: str = "gpt-4o-mini"
    systemPrompt: str = (
        "Você é o Concierge Virtual da Zarpou Viagens e Turismo. Atenda com calor humano, sofisticação e objetividade. "
        "Recomende os melhores destinos, hospedagens e passagens aéreas da Zarpou, sempre destacando parcelamento em até 12x sem juros e atendimento humanizado."
    )
    welcomeMessage: str = (
        "Olá! 👋 Sou o Concierge Virtual da Zarpou Viagens. Como posso ajudar com sua próxima viagem hoje?"
    )


class StorageBucketConfigSchema(BaseModel):
    provider: str = "aws_s3"  # 'aws_s3', 'supabase', 'cloudflare_r2', 'local'
    enabled: bool = True
    bucketName: str = ""
    region: str = "sa-east-1"
    accessKeyId: Optional[str] = ""
    secretAccessKey: Optional[str] = ""
    endpointUrl: Optional[str] = ""
    publicUrlPrefix: Optional[str] = ""


class AgencySettingSchema(BaseModel):
    companyName: str = "Zarpou Viagens e Turismo Ltda"
    tradingName: str = "Zarpou Viagens"
    cnpj: str = "55.849.201/0001-38"
    cadastur: str = "34.120.948/0001-90"
    whatsapp: str = "5531984210000"
    whatsappMessage: Optional[str] = "Olá! Gostaria de planejar minha próxima viagem com a Zarpou."
    email: str = "contato@zarpouviagens.com.br"
    phone: str = "(31) 3245-8900"
    instagram: Optional[str] = "zarpouviagens"
    linkedin: Optional[str] = "zarpouviagens"
    address: Optional[str] = "Belo Horizonte - MG, Brasil"
    termsAndConditions: Optional[str] = None
    privacyPolicy: Optional[str] = None

    # Integrações dinâmicas gerenciadas pelo frontend
    whatsappApi: WhatsAppApiConfigSchema = WhatsAppApiConfigSchema()
    paymentGateway: PaymentGatewayConfigSchema = PaymentGatewayConfigSchema()
    resendApiKey: Optional[str] = ""
    aiChat: AiChatConfigSchema = AiChatConfigSchema()
    storageBucket: StorageBucketConfigSchema = StorageBucketConfigSchema()


class DashboardMetrics(BaseModel):
    totalRevenue: float
    totalBookings: int
    activePromotions: int
    totalProducts: int
    pendingBookings: int
    confirmedBookings: int
    totalInquiries: int
