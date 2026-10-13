from datetime import datetime, timedelta, timezone, date
import random
from typing import Any, Dict, List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.features.bookings.infra.models import Booking, BookingTraveler, BookingAddon
from app.features.bookings.infra.repositories import BookingRepository
from app.features.customers.infra.models import Customer
from app.features.companies.infra.models import Company
from app.features.hotels.infra.models import Room
from app.features.flights.infra.models import Flight
from app.features.packages.infra.models import Package
from app.features.bookings.app.schemas import (
    BookingCreate,
    BookingStatusUpdate,
    PriceSummarySchema,
)


class BookingService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BookingRepository(db)

    @staticmethod
    def format_booking(b: Booking) -> Dict[str, Any]:
        pricing = PriceSummarySchema(
            baseAmount=float(b.base_amount or 0.0),
            taxesAndFees=float(b.taxes_and_fees or 0.0),
            addonsAmount=float(b.addons_amount or 0.0),
            discountAmount=float(b.discount_amount or 0.0),
            finalAmount=float(b.final_amount or 0.0),
        )

        travelers = [
            {
                "id": t.id,
                "fullName": t.full_name,
                "documentType": t.document_type,
                "documentNumber": t.document_number,
                "birthDate": t.birth_date.isoformat() if t.birth_date else "",
                "gender": t.gender,
                "email": t.email,
                "phone": t.phone,
                "isPrimary": t.is_primary,
            }
            for t in b.travelers
        ]

        addons = [
            {
                "id": a.id,
                "title": a.title,
                "description": a.description,
                "price": float(a.price or 0.0),
                "category": a.category,
            }
            for a in b.addons
        ]

        return {
            "id": b.id,
            "locatorCode": b.locator_code,
            "locator": b.locator_code,
            "createdAt": b.created_at,
            "status": b.status,
            "productType": b.product_type,
            "checkInDate": b.check_in_date,
            "checkOutDate": b.check_out_date,
            "nights": b.nights,
            "paymentMethod": b.payment_method,
            "installments": b.installments,
            "companyId": b.company_id,
            "costCenter": b.cost_center,
            "pricing": pricing,
            "pixCode": b.pix_code,
            "pixQrCodeUrl": b.pix_qr_code_url,
            "pixExpiresAt": b.pix_expires_at,
            "boletoBarcode": b.boleto_barcode,
            "voucherUrl": b.voucher_url or f"/reserva/confirmada/{b.id}",
            "travelers": travelers,
            "addons": addons,
            "hotel": b.hotel,
            "selectedRoom": b.selected_room,
            "flight": b.flight,
            "packageItem": b.package_item,
        }

    def create(
        self,
        booking_in: BookingCreate,
        customer: Optional[Customer] = None,
        company: Optional[Company] = None,
    ) -> Dict[str, Any]:
        if not booking_in.travelers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe pelo menos um viajante responsável."
            )

        # Gerar PNR único: ZRP-XXXXXX
        while True:
            random_num = random.randint(100000, 999999)
            locator_code = f"ZRP-{random_num}"
            if not self.repo.get_by_locator(locator_code):
                break

        booking_id = f"booking-{int(datetime.now(timezone.utc).timestamp())}-{uuid.uuid4().hex[:6]}"

        base_amount = 0.0
        hotel = None
        room = None
        flight = None
        package_item = None

        check_in_date_parsed = None
        check_out_date_parsed = None
        nights = booking_in.nights or 1

        if booking_in.checkInDate:
            try:
                check_in_date_parsed = date.fromisoformat(booking_in.checkInDate)
            except Exception:
                pass

        if booking_in.checkOutDate:
            try:
                check_out_date_parsed = date.fromisoformat(booking_in.checkOutDate)
            except Exception:
                pass

        if booking_in.productType == "hotel" and booking_in.selectedRoomId:
            room = self.db.query(Room).filter(Room.id == booking_in.selectedRoomId).first()
            if room:
                base_amount = float(room.price_per_night) * nights
                hotel = room.hotel
        elif booking_in.productType == "flight" and booking_in.flightId:
            flight = self.db.query(Flight).filter(Flight.id == booking_in.flightId).first()
            if flight:
                num_travelers = max(1, len(booking_in.travelers))
                base_amount = float(flight.price) * num_travelers
        elif booking_in.productType == "package" and booking_in.packageId:
            package_item = self.db.query(Package).filter(Package.id == booking_in.packageId).first()
            if package_item:
                num_travelers = max(1, len(booking_in.travelers))
                base_amount = float(package_item.price_per_person) * num_travelers

        addons_amount = sum(float(a.price) for a in booking_in.addons) if booking_in.addons else 0.0
        taxes_and_fees = round(base_amount * 0.05, 2)
        discount_amount = 0.0
        status_initial = "pendente_pagamento" if booking_in.paymentMethod in ["pix", "boleto"] else "confirmada"
        company_id = None

        if booking_in.paymentMethod == "corporate_invoice":
            comp_id = booking_in.companyId or (company.id if company else None)
            if not comp_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Informe o ID da empresa para compras via faturamento a prazo PJ."
                )
            target_company = self.db.query(Company).filter(Company.id == comp_id).first()
            if not target_company or target_company.status != "aprovada":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Empresa não autorizada para faturamento a prazo ou cadastro pendente de aprovação pela Zarpou."
                )

            disc_pct = float(target_company.corporate_discount_percent or 0.0)
            discount_amount = round(base_amount * (disc_pct / 100.0), 2)
            final_amount = round(base_amount + taxes_and_fees + addons_amount - discount_amount, 2)

            if target_company.credit_available < final_amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Limite de crédito corporativo insuficiente. Disponível: R$ {target_company.credit_available:.2f}. Valor do pedido: R$ {final_amount:.2f}."
                )

            target_company.credit_used = float(target_company.credit_used or 0.0) + final_amount
            status_initial = "confirmada"
            company_id = target_company.id

        elif booking_in.paymentMethod == "pix":
            discount_amount = round((base_amount + taxes_and_fees) * 0.05, 2)
            final_amount = round(base_amount + taxes_and_fees + addons_amount - discount_amount, 2)
        else:
            final_amount = round(base_amount + taxes_and_fees + addons_amount, 2)

        pix_code = None
        pix_expires_at = None
        if booking_in.paymentMethod == "pix":
            pix_code = f"00020126580014br.gov.bcb.pix0136{locator_code}-zarpou-pagamentos520400005303986540{final_amount:.2f}5802BR5922Zarpou Viagens Ltda6014Belo Horizonte62070503***6304"
            pix_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        primary_traveler = next((t for t in booking_in.travelers if t.isPrimary), booking_in.travelers[0])
        customer_id = customer.id if customer else None

        if not customer_id and not company_id:
            existing_cust = self.db.query(Customer).filter(Customer.email == primary_traveler.email.lower()).first()
            if existing_cust:
                customer_id = existing_cust.id
            else:
                new_cust = Customer(
                    id=f"cust-{int(datetime.now(timezone.utc).timestamp())}",
                    name=primary_traveler.fullName,
                    email=primary_traveler.email.lower(),
                    phone=primary_traveler.phone,
                    cpf=primary_traveler.documentNumber if primary_traveler.documentType == "CPF" else None,
                )
                self.db.add(new_cust)
                self.db.flush()
                customer_id = new_cust.id

        booking = Booking(
            id=booking_id,
            locator_code=locator_code,
            customer_id=customer_id,
            company_id=company_id,
            cost_center=booking_in.costCenter,
            product_type=booking_in.productType,
            status=status_initial,
            hotel_id=hotel.id if hotel else booking_in.hotelId,
            room_id=room.id if room else booking_in.selectedRoomId,
            flight_id=flight.id if flight else booking_in.flightId,
            package_id=package_item.id if package_item else booking_in.packageId,
            check_in_date=check_in_date_parsed,
            check_out_date=check_out_date_parsed,
            nights=nights,
            adults_count=booking_in.adults,
            children_count=booking_in.children,
            payment_method=booking_in.paymentMethod,
            installments=booking_in.installments,
            base_amount=base_amount,
            taxes_and_fees=taxes_and_fees,
            addons_amount=addons_amount,
            discount_amount=discount_amount,
            final_amount=final_amount,
            pix_code=pix_code,
            pix_expires_at=pix_expires_at,
            voucher_url=f"/reserva/confirmada/{booking_id}",
        )
        self.db.add(booking)
        self.db.flush()

        for idx, t in enumerate(booking_in.travelers):
            try:
                bdate = date.fromisoformat(t.birthDate)
            except Exception:
                bdate = date(1990, 1, 1)

            traveler = BookingTraveler(
                id=f"trav-{booking.id}-{idx + 1}",
                booking_id=booking.id,
                full_name=t.fullName,
                document_type=t.documentType,
                document_number=t.documentNumber,
                birth_date=bdate,
                gender=t.gender,
                email=t.email.lower(),
                phone=t.phone,
                is_primary=t.isPrimary or (idx == 0),
            )
            self.db.add(traveler)

        if booking_in.addons:
            for idx, a in enumerate(booking_in.addons):
                booking_addon = BookingAddon(
                    id=f"bkaddon-{booking.id}-{idx + 1}",
                    booking_id=booking.id,
                    addon_id=a.id,
                    title=a.title,
                    description=a.description,
                    price=a.price,
                    category=a.category,
                )
                self.db.add(booking_addon)

        self.db.commit()
        self.db.refresh(booking)
        return self.format_booking(booking)

    def get_my_trips(self, customer_id: str) -> List[Dict[str, Any]]:
        bookings = self.repo.list_by_customer(customer_id)
        return [self.format_booking(b) for b in bookings]

    def _can_access(self, booking, payload: Optional[dict], email: Optional[str]) -> bool:
        """
        Regra de autorização (OWASP A01 - Broken Access Control / IDOR):
        - Equipe administrativa com acesso ao módulo 'reservas' (ou superadmin);
        - Cliente B2C dono da reserva;
        - Empresa B2B dona da reserva;
        - Visitante (sem login) somente se informar o e-mail do titular/viajante.
        """
        if payload:
            role = payload.get("role")
            sub = payload.get("sub")
            if role in ("admin", "personalizado", "gestor", "atendente"):
                from app.features.users.infra.models import User
                user = self.db.query(User).filter(User.id == sub, User.is_active == True).first()
                if user and (user.role == "admin" or "reservas" in user.allowedScreens):
                    return True
            elif role == "company":
                if booking.company_id and booking.company_id == sub:
                    return True
            elif sub and booking.customer_id and booking.customer_id == sub:
                return True

        if email:
            clean_email = email.strip().lower()
            if any((t.email or "").lower() == clean_email for t in booking.travelers):
                return True
            if booking.customer and (booking.customer.email or "").lower() == clean_email:
                return True
        return False

    def get_by_locator(
        self, locator_code: str, email: Optional[str] = None, payload: Optional[dict] = None
    ) -> Dict[str, Any]:
        clean_code = locator_code.strip().upper()
        booking = self.repo.get_by_locator(clean_code)
        # Mesma resposta para "não existe" e "sem permissão" evita enumeração de PNRs
        if not booking or not self._can_access(booking, payload, email):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reserva não localizada para este código localizador e e-mail.",
            )
        return self.format_booking(booking)

    def list_all(self, status: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        bookings = self.repo.list_all(status=status, search=search)
        return [self.format_booking(b) for b in bookings]

    def get_unified(
        self, id_or_locator: str, email: Optional[str] = None, payload: Optional[dict] = None
    ) -> Dict[str, Any]:
        clean_q = id_or_locator.strip()
        booking = self.repo.get_by_id_or_locator(clean_q)
        if not booking or not self._can_access(booking, payload, email):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reserva não encontrada."
            )
        return self.format_booking(booking)

    def update_status(self, booking_id: str, status_in: BookingStatusUpdate) -> Dict[str, Any]:
        booking = self.repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reserva não encontrada."
            )

        booking.status = status_in.status
        updated = self.repo.update(booking)
        return self.format_booking(updated)
