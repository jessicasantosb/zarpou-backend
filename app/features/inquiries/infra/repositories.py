from typing import List, Optional
from sqlalchemy.orm import Session
from app.features.inquiries.infra.models import ContactInquiry


class ContactInquiryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, status: Optional[str] = None) -> List[ContactInquiry]:
        query = self.db.query(ContactInquiry)
        if status:
            query = query.filter(ContactInquiry.status == status)
        return query.order_by(ContactInquiry.created_at.desc()).all()

    def get_by_id(self, inquiry_id: str) -> Optional[ContactInquiry]:
        return self.db.query(ContactInquiry).filter(ContactInquiry.id == inquiry_id).first()

    def create(self, inquiry: ContactInquiry) -> ContactInquiry:
        self.db.add(inquiry)
        self.db.commit()
        self.db.refresh(inquiry)
        return inquiry

    def update(self, inquiry: ContactInquiry) -> ContactInquiry:
        self.db.commit()
        self.db.refresh(inquiry)
        return inquiry
