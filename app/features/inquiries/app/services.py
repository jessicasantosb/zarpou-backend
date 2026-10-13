from datetime import date
import re
from typing import List, Optional
import httpx
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.features.agency.infra.models import AgencySetting
from app.features.inquiries.infra.models import ContactInquiry
from app.features.inquiries.infra.repositories import ContactInquiryRepository
from app.features.inquiries.app.schemas import InquiryCreate, InquiryStatusUpdate


async def send_inquiry_resend_notification(api_key: str, recipient_email: str, inquiry: ContactInquiry):
    if not api_key:
        return
    try:
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
            <h2 style="color: #002B49; border-bottom: 2px solid #F5A623; padding-bottom: 8px;">
                Nova Solicitação de Consultoria - Zarpou Viagens
            </h2>
            <p><strong>Nome:</strong> {inquiry.name}</p>
            <p><strong>E-mail:</strong> {inquiry.email}</p>
            <p><strong>Telefone:</strong> {inquiry.phone}</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 16px 0;" />
            <h3>Detalhes da Viagem</h3>
            <p><strong>Destino Desejado:</strong> {inquiry.destination}</p>
            <p><strong>Período:</strong> {inquiry.start_date} até {inquiry.end_date}</p>
            <p><strong>Viajantes:</strong> {inquiry.number_of_adults} Adulto(s), {inquiry.number_of_children} Criança(s)</p>
            <p><strong>Tipo de Viagem:</strong> {inquiry.travel_type}</p>
            <p><strong>Preferência de Hospedagem:</strong> {inquiry.accommodation_preference} ({inquiry.room_type})</p>
            <p><strong>Regime Alimentar:</strong> {inquiry.meal_plan}</p>
            <p><strong>Transporte:</strong> {inquiry.transportation} / Local: {inquiry.internal_transportation}</p>
            <p><strong>Orçamento Estimado:</strong> R$ {inquiry.estimated_budget:.2f}</p>
            {f'<p><strong>Restrições / Necessidades:</strong> {inquiry.dietary_restrictions} / {inquiry.other_special_needs}</p>' if (inquiry.dietary_restrictions or inquiry.other_special_needs) else ''}
            {f'<p><strong>Informações Adicionais:</strong> {inquiry.additional_info}</p>' if inquiry.additional_info else ''}
        </div>
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": "Zarpou Viagens <lazer@zarpouviagens.com.br>",
                    "to": [recipient_email or "lazer@zarpouviagens.com.br"],
                    "subject": f"Nova Consultoria de Viagem: {inquiry.name} - {inquiry.destination}",
                    "html": html_content,
                },
            )
    except Exception as e:
        print("Erro ao enviar e-mail via Resend:", e)


class InquiryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ContactInquiryRepository(db)

    def create(self, inquiry_in: InquiryCreate, background_tasks: BackgroundTasks) -> ContactInquiry:
        try:
            s_date = date.fromisoformat(inquiry_in.startDate)
        except Exception:
            s_date = date.today()

        try:
            e_date = date.fromisoformat(inquiry_in.endDate)
        except Exception:
            e_date = date.today()

        try:
            adults = int(inquiry_in.numberOfAdults)
        except Exception:
            adults = 1

        try:
            children = int(inquiry_in.numberOfChildren or 0)
        except Exception:
            children = 0

        budget_digits = re.sub(r"\D", "", inquiry_in.estimatedBudget or "0")
        budget = float(budget_digits) if budget_digits else 0.0

        inquiry = ContactInquiry(
            name=inquiry_in.name,
            email=inquiry_in.email.lower(),
            phone=inquiry_in.phone,
            destination=inquiry_in.destination,
            start_date=s_date,
            end_date=e_date,
            number_of_adults=adults,
            number_of_children=children,
            travel_type=inquiry_in.travelType or "leisure",
            accommodation_preference=inquiry_in.accommodationPreference or "hotel",
            room_type=inquiry_in.roomType or "standard",
            meal_plan=inquiry_in.mealPlan or "cafe_manha",
            transportation=inquiry_in.transportation or "aereo",
            internal_transportation=inquiry_in.internalTransportation or "nenhum",
            estimated_budget=budget,
            dietary_restrictions=inquiry_in.dietaryRestrictions,
            other_special_needs=inquiry_in.otherSpecialNeeds,
            additional_info=inquiry_in.additionalInfo,
            status="novo",
        )
        created = self.repo.create(inquiry)

        agency_cfg = self.db.query(AgencySetting).filter(AgencySetting.id == "default").first()
        if agency_cfg and agency_cfg.resend_api_key:
            background_tasks.add_task(
                send_inquiry_resend_notification,
                agency_cfg.resend_api_key,
                agency_cfg.email,
                created
            )

        return created

    def list(self, status: Optional[str] = None) -> List[ContactInquiry]:
        return self.repo.list(status=status)

    def update_status(self, inquiry_id: str, status_in: InquiryStatusUpdate) -> ContactInquiry:
        inquiry = self.repo.get_by_id(inquiry_id)
        if not inquiry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitação não encontrada."
            )

        inquiry.status = status_in.status
        if status_in.admin_notes is not None:
            inquiry.admin_notes = status_in.admin_notes

        return self.repo.update(inquiry)
