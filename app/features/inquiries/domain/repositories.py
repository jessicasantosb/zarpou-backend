from typing import List, Optional, Protocol
from app.features.inquiries.domain.entities import ContactInquiryEntity


class IContactInquiryRepository(Protocol):
    def list(self, status: Optional[str] = None) -> List[ContactInquiryEntity]:
        ...

    def get_by_id(self, inquiry_id: str) -> Optional[ContactInquiryEntity]:
        ...

    def save(self, inquiry: ContactInquiryEntity) -> ContactInquiryEntity:
        ...
