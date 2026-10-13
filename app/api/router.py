from fastapi import APIRouter
from app.features.auth.router import router as auth_router
from app.features.users.router import router as users_router
from app.features.customers.router import router as customers_router
from app.features.destinations.router import router as destinations_router
from app.features.hotels.router import router as hotels_router
from app.features.flights.router import router as flights_router
from app.features.packages.router import router as packages_router
from app.features.promotions.router import router as promotions_router
from app.features.addons.router import router as addons_router
from app.features.bookings.router import router as bookings_router
from app.features.inquiries.router import router as inquiries_router
from app.features.agency.router import router as agency_router
from app.features.chat.router import router as chat_router
from app.features.companies.router import router as companies_router
from app.features.storage.router import router as storage_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Autenticação"])
api_router.include_router(users_router, prefix="/users", tags=["Administradores & Equipe"])
api_router.include_router(customers_router, prefix="/customers", tags=["Usuários & Clientes"])
api_router.include_router(destinations_router, prefix="/destinations", tags=["Destinos"])
api_router.include_router(hotels_router, prefix="/hotels", tags=["Hotéis & Hospedagens"])
api_router.include_router(flights_router, prefix="/flights", tags=["Passagens Aéreas"])
api_router.include_router(packages_router, prefix="/packages", tags=["Pacotes Turísticos"])
api_router.include_router(promotions_router, prefix="/promotions", tags=["Promoções"])
api_router.include_router(addons_router, prefix="/addons", tags=["Adicionais & Serviços"])
api_router.include_router(bookings_router, prefix="/bookings", tags=["Reservas & Vouchers"])
api_router.include_router(inquiries_router, prefix="/inquiries", tags=["Consultoria & Contato"])
api_router.include_router(agency_router, prefix="/agency", tags=["Configurações & Painel"])
api_router.include_router(chat_router, prefix="/chat", tags=["Concierge Virtual (IA)"])
api_router.include_router(companies_router, prefix="/companies", tags=["Zarpou Empresas (B2B)"])
api_router.include_router(storage_router, prefix="/storage", tags=["Armazenamento & Uploads"])

