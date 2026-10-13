from typing import Any, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.features.agency.infra.models import AgencySetting
from app.features.chat.infra.models import ChatLog
from app.features.chat.infra.repositories import ChatLogRepository
from app.features.chat.app.schemas import ChatRequest, ChatResponse, SuggestedAction


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ChatLogRepository(db)

    def get_history(self, session_id: str) -> List[ChatLog]:
        return self.repo.get_history(session_id)

    async def chat(self, req: ChatRequest, customer_id: Optional[str]) -> ChatResponse:
        agency_cfg = self.db.query(AgencySetting).filter(AgencySetting.id == "default").first()
        wa_num = (agency_cfg.phone if agency_cfg and agency_cfg.phone else "31984210000").replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        wa_link = f"https://wa.me/55{wa_num}" if not wa_num.startswith("55") else f"https://wa.me/{wa_num}"

        api_key = (
            (req.config and req.config.apiKey)
            or (agency_cfg and agency_cfg.ai_chat_api_key)
            or settings.AI_API_KEY
            or settings.OPENAI_API_KEY
            or settings.GROQ_API_KEY
        )
        provider = (req.config and req.config.provider) or (agency_cfg and agency_cfg.ai_chat_provider) or "openai"
        model = (req.config and req.config.model) or (agency_cfg and agency_cfg.ai_chat_model) or "gpt-4o-mini"
        system_prompt = (
            (req.config and req.config.systemPrompt)
            or (agency_cfg and agency_cfg.ai_chat_system_prompt)
            or (
                "Você é o Concierge Virtual da Zarpou Viagens e Turismo. Atenda com calor humano, sofisticação e objetividade. "
                "Recomende os melhores destinos, hospedagens e passagens aéreas da Zarpou, sempre destacando parcelamento em até 12x sem juros e atendimento humanizado.\n"
                "REGRAS DE NAVEGAÇÃO: Ao citar links internos no site, utilize EXCLUSIVAMENTE as seguintes rotas reais da Zarpou:\n"
                "- Hospedagens / Hotéis: /hospedagens (nunca utilize /hoteis)\n"
                "- Passagens Aéreas / Voos: /passagens (nunca utilize /voos)\n"
                "- Pacotes Turísticos: /pacotes\n"
                "- Destinos em Alta: /#destinos\n"
                "- Minhas Reservas e Vouchers: /minhas-viagens\n"
                "- Falar com Consultor Humano: /contato\n"
                "Nunca invente URLs inexistentes como /hoteis ou /voos."
            )
        )

        if api_key:
            try:
                reply = None
                if provider == "gemini":
                    gemini_model = model if model and "gemini" in model.lower() else "gemini-1.5-flash"
                    if gemini_model.startswith("models/"):
                        gemini_model = gemini_model.replace("models/", "")
                    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}"

                    raw_contents = []
                    if req.history:
                        for h in req.history[-8:]:
                            role = "model" if h.role == "assistant" else "user"
                            if h.content:
                                raw_contents.append({"role": role, "parts": [{"text": h.content}]})

                    while raw_contents and raw_contents[0]["role"] != "user":
                        raw_contents.pop(0)

                    raw_contents.append({"role": "user", "parts": [{"text": req.message}]})

                    contents = []
                    for item in raw_contents:
                        if contents and contents[-1]["role"] == item["role"]:
                            contents[-1]["parts"][0]["text"] += f"\n\n{item['parts'][0]['text']}"
                        else:
                            contents.append(item)

                    payload = {
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": contents,
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 600,
                        },
                    }

                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.post(endpoint, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts:
                                    reply = parts[0].get("text")

                elif provider in ["openai", "groq"]:
                    endpoint = (
                        "https://api.groq.com/openai/v1/chat/completions"
                        if provider == "groq"
                        else "https://api.openai.com/v1/chat/completions"
                    )
                    model_to_use = "llama-3.3-70b-versatile" if provider == "groq" and model == "gpt-4o-mini" else model

                    messages = [{"role": "system", "content": system_prompt}]
                    if req.history:
                        for h in req.history[-8:]:
                            messages.append({"role": h.role, "content": h.content})
                    messages.append({"role": "user", "content": req.message})

                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.post(
                            endpoint,
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {api_key}",
                            },
                            json={
                                "model": model_to_use,
                                "messages": messages,
                                "temperature": 0.7,
                                "max_tokens": 500,
                            },
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            reply = data.get("choices", [{}])[0].get("message", {}).get("content")

                if reply:
                    self.repo.save_messages(req.sessionId or "default", customer_id, req.message, reply)
                    actions = [
                        SuggestedAction(label="Explorar Destinos", url="/#destinos"),
                        SuggestedAction(label="Ver Hospedagens", url="/hospedagens"),
                        SuggestedAction(label="Passagens Aéreas", url="/passagens"),
                        SuggestedAction(label="Falar com Consultor", url=wa_link),
                    ]
                    return ChatResponse(reply=reply, suggestedActions=actions)
            except Exception as e:
                print("Erro ao consultar provedor externo de IA:", e)

        # Fallback de Alta Resiliência
        lower = req.message.lower()
        if any(k in lower for k in ["hotel", "hoté", "hotei", "hosped", "resort", "pousad", "estadia", "quarto"]):
            reply = (
                "🏨 **Hospedagens em Destaque na Zarpou:**\n\n"
                "Temos uma curadoria exclusiva com cancelamento grátis e café da manhã incluso:\n\n"
                "1. **Copacabana Palace Grand Luxury (Rio de Janeiro)** — 5 estrelas em frente ao mar, a partir de **R$ 850/noite**.\n"
                "2. **Búzios Beach & Spa Resort (Armação dos Búzios)** — Piscina aquecida e alta gastronomia por **R$ 520/noite**.\n"
                "3. **The Royal Mirage (Dubai)** — Luxo árabe com praia privativa por **R$ 1.650/noite**.\n"
                "4. **Santiago Andes View & Spa (Chile)** — Vista panorâmica para a Cordilheira por **R$ 720/noite**.\n\n"
                "Todas as estadias podem ser parceladas em **até 12x sem juros**. Deseja consultar disponibilidade para uma data específica?"
            )
            actions = [
                SuggestedAction(label="Ver Hospedagens", url="/hospedagens"),
                SuggestedAction(label="Resorts & Hotéis", url="/hospedagens"),
                SuggestedAction(label="Chamar Especialista", url=f"{wa_link}?text=Olá,%20gostaria%20de%20ajuda%20com%20hotéis"),
            ]
        elif any(k in lower for k in ["voo", "passag", "aéreo", "aereo"]):
            reply = (
                "✈️ **Tarifas Aéreas Internacionais em Promoção:**\n\n"
                "A Zarpou negociou tarifas especiais com taxas de embarque inclusas:\n\n"
                "• **Belo Horizonte (CNF) ⇄ Miami (MIA)**: Ida e volta a partir de **R$ 3.450** (12x de R$ 287,50).\n"
                "• **São Paulo (GRU) ⇄ Roma (FCO)**: Voo direto ITA Airways por **R$ 4.890** (12x de R$ 407,50).\n"
                "• **Belo Horizonte (CNF) ⇄ Madri (MAD)**: Iberia com bagagem inclusa por **R$ 4.350**.\n"
                "• **Curitiba (CWB) ⇄ Nova York (JFK)**: American Airlines por **R$ 4.190**.\n\n"
                "Todas as passagens incluem suporte em português antes e durante o voo!"
            )
            actions = [
                SuggestedAction(label="Pesquisar Passagens", url="/passagens"),
                SuggestedAction(label="Voos Nacionais & Internacionais", url="/passagens"),
                SuggestedAction(label="Cotação Personalizada", url=f"{wa_link}?text=Olá,%20quero%20cotar%20uma%20passagem"),
            ]
        elif any(k in lower for k in ["pacote", "promoç", "promoc", "oferta", "desconto"]):
            reply = (
                "🌴 **Pacotes & Promoções Especiais Zarpou:**\n\n"
                "Combinando voo + hospedagem você economiza até **25%** no valor final da viagem!\n\n"
                "• **Semana Santa & Feriados**: Pacotes para o Nordeste e praias paradisíacas com pensão completa.\n"
                "• **Destinos Andinos**: Roteiros para o Chile e Argentina com vinhedos inclusos.\n"
                "• **Condições:** 5% de desconto imediato via Pix ou até **12x sem juros no cartão de crédito**."
            )
            actions = [
                SuggestedAction(label="Ver Pacotes em Promoção", url="/pacotes"),
                SuggestedAction(label="Explorar Destinos", url="/#destinos"),
                SuggestedAction(label="Falar no WhatsApp", url=wa_link),
            ]
        elif any(k in lower for k in ["humano", "atendente", "whatsapp", "contato", "telefone"]):
            reply = (
                "💬 **Atendimento Humanizado Zarpou:**\n\n"
                "Nossos consultores especialistas estão prontos para atender você no WhatsApp oficial da agência!\n\n"
                f"Basta clicar no botão abaixo ou pelo número {agency_cfg.phone if agency_cfg and agency_cfg.phone else '(31) 98421-0000'} para tirar dúvidas sobre vistos, roteiros personalizados e emissão de passagens."
            )
            actions = [
                SuggestedAction(label="Iniciar Conversa no WhatsApp", url=wa_link),
                SuggestedAction(label="Enviar Solicitação de Roteiro", url="/contato"),
            ]
        elif any(k in lower for k in ["cancel", "reembolso", "voucher", "reserva"]):
            reply = (
                "🛡️ **Segurança e Flexibilidade Zarpou:**\n\n"
                "• **Cancelamento:** Grande parte das nossas tarifas de hotéis contam com cancelamento 100% grátis até 48h antes do check-in.\n"
                "• **Vouchers:** São gerados automaticamente após a aprovação do pagamento e disponibilizados na aba **Minhas Viagens** e enviados por e-mail e WhatsApp.\n"
                "• **Segurança:** Todas as transações são protegidas por criptografia SSL 256-bit e em total conformidade com a LGPD."
            )
            actions = [
                SuggestedAction(label="Consultar Minhas Viagens", url="/minhas-viagens"),
                SuggestedAction(label="Falar com o Suporte", url=f"{wa_link}?text=Olá,%20preciso%20de%20suporte%20com%20minha%20reserva"),
            ]
        else:
            reply = (
                "Olá! ✈️ Que bom conversar com você!\n\n"
                "Como seu **Concierge Virtual Zarpou**, posso te ajudar a planejar a viagem perfeita:\n\n"
                "• 🏨 **Encontrar hotéis e resorts** com as melhores avaliações.\n"
                "• ✈️ **Cotar passagens aéreas** nacionais e internacionais com taxas inclusas.\n"
                "• 🌴 **Montar pacotes completos** com aéreo + hotel em até 12x sem juros.\n"
                "• 📍 **Descobrir lugares imperdíveis** no Brasil e no mundo.\n\n"
                "Qual destino você tem em mente para suas próximas férias?"
            )
            actions = [
                SuggestedAction(label="Ver Hospedagens", url="/hospedagens"),
                SuggestedAction(label="Ver Passagens", url="/passagens"),
                SuggestedAction(label="Ver Pacotes", url="/pacotes"),
                SuggestedAction(label="Falar no WhatsApp", url=wa_link),
            ]

        self.repo.save_messages(req.sessionId or "default", customer_id, req.message, reply)
        return ChatResponse(reply=reply, suggestedActions=actions)
