import json
from datetime import date
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.user import User
from app.models.destination import Destination
from app.models.hero import HeroConfig
from app.models.hotel import Hotel, Room
from app.models.flight import Flight, FlightSegment
from app.models.promotion import Promotion
from app.models.addon import Addon
from app.models.agency import AgencySetting
from app.models.company import Company, CompanyEmployee, CompanyInvoice


def run_seeds(db: Session = None):
    close_db = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        close_db = True

    try:
        # 1. Usuários Administradores & Equipe
        admin_email = "admin@zarpou.com.br"
        all_screens_json = json.dumps([
            "dashboard", "hero", "promocoes", "hospedagens", "passagens",
            "destinos", "reservas", "usuarios", "administradores", "configuracoes"
        ])
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            admin = User(
                id="adm-1",
                name="Administrador Zarpou",
                email=admin_email,
                password_hash=get_password_hash("admin123"),
                role="admin",
                allowed_screens=all_screens_json,
                is_active=True,
            )
            db.add(admin)
        elif not admin_user.allowed_screens:
            admin_user.allowed_screens = all_screens_json

        juliana = db.query(User).filter((User.id == "adm-2") | (User.email == "juliana.costa@zarpou.com.br")).first()
        gestor_screens_json = json.dumps([
            "dashboard", "hero", "promocoes", "hospedagens", "passagens", "destinos", "reservas"
        ])
        if not juliana:
            db.add(User(
                id="adm-2",
                name="Juliana Costa",
                email="juliana.costa@zarpou.com.br",
                password_hash=get_password_hash("admin123"),
                role="gestor",
                allowed_screens=gestor_screens_json,
                is_active=True,
            ))
        elif not juliana.allowed_screens:
            juliana.allowed_screens = gestor_screens_json

        rodrigo = db.query(User).filter((User.id == "adm-3") | (User.email == "rodrigo.silveira@zarpou.com.br")).first()
        atendente_screens_json = json.dumps([
            "dashboard", "reservas", "usuarios"
        ])
        if not rodrigo:
            db.add(User(
                id="adm-3",
                name="Rodrigo Silveira",
                email="rodrigo.silveira@zarpou.com.br",
                password_hash=get_password_hash("admin123"),
                role="atendente",
                allowed_screens=atendente_screens_json,
                is_active=True,
            ))
        elif not rodrigo.allowed_screens:
            rodrigo.allowed_screens = atendente_screens_json

        # 1.1 Empresa B2B de Demonstração (Zarpou Empresas)
        comp_cnpj = "12.345.678/0001-90"
        if not db.query(Company).filter(Company.cnpj == comp_cnpj).first():
            demo_company = Company(
                id="comp-inova",
                cnpj=comp_cnpj,
                razao_social="Inovação e Tecnologia Brasil S/A",
                nome_fantasia="InovaTech",
                corporate_email="viagens@inovatech.com.br",
                phone="(11) 3210-9000",
                manager_name="Renato Fonseca",
                manager_cpf="111.222.333-44",
                password_hash=get_password_hash("admin123"),
                status="aprovada",
                corporate_discount_percent=10.00,
                credit_limit=30000.00,
                credit_used=0.00,
                payment_terms="faturado_30d",
            )
            db.add(demo_company)
            db.flush()

            demo_emp = CompanyEmployee(
                id="emp-inova-1",
                company_id=demo_company.id,
                full_name="Carlos Eduardo Mendes",
                cpf="123.456.789-10",
                email="carlos@inovatech.com.br",
                phone="(11) 98765-4321",
                cost_center="Tecnologia & Inovação",
                department="Engenharia de Software",
                is_active=True,
            )
            db.add(demo_emp)

        # 2. Configurações da Agência
        if not db.query(AgencySetting).filter(AgencySetting.id == "default").first():
            setting = AgencySetting(
                id="default",
                company_name="Zarpou Viagens e Turismo Ltda",
                trading_name="Zarpou Viagens",
                cnpj="55.849.201/0001-38",
                cadastur="34.120.948/0001-90",
                whatsapp="5531984210000",
                email="contato@zarpou.com.br",
                phone="(31) 3344-5500",
                address="Av. do Contorno, 6500 - Savassi, Belo Horizonte - MG, 30110-044",
            )
            db.add(setting)

        # 3. Banner Hero
        if not db.query(HeroConfig).filter(HeroConfig.id == "default").first():
            hero = HeroConfig(
                id="default",
                title_prefix="Seu",
                title_highlight="sonho",
                title_suffix="de viajar bem, agora é realidade",
                subtitle="Reserve hotéis, passagens aéreas e pacotes com pagamento em até 12x sem juros e atendimento humano especializado.",
                bg_type="video",
                bg_image_url="https://images.pexels.com/photos/12039523/pexels-photo-12039523.jpeg",
                bg_video_url="/hero.mp4",
                cta_text="Falar com um Especialista",
                cta_link="whatsapp",
            )
            db.add(hero)

        # 4. Destinos
        destinations_data = [
            {
                "id": "dest-dubai",
                "title": "Dubai",
                "country": "Emirados Árabes",
                "flag": "🇦🇪",
                "category": "international",
                "tag": "Luxo & Futurismo",
                "description": "Arranha-céus icônicos, safáris no deserto, ilhas artificiais e o auge da sofisticação mundial.",
                "starting_price": 1650.00,
                "accommodations_count": 140,
                "link": "/hospedagens?city=Dubai",
                "image_url": "https://images.pexels.com/photos/3769312/pexels-photo-3769312.jpeg",
                "display_order": 1,
            },
            {
                "id": "dest-buzios",
                "title": "Armação dos Búzios",
                "country": "Brasil",
                "flag": "🇧🇷",
                "category": "national",
                "tag": "Praias Paradisíacas",
                "description": "Mais de 20 praias de águas cristalinas, alta gastronomia na Rua das Pedras e pousadas de charme.",
                "starting_price": 520.00,
                "accommodations_count": 95,
                "link": "/hospedagens?city=Armação%20dos%20Búzios",
                "image_url": "https://images.pexels.com/photos/12039523/pexels-photo-12039523.jpeg",
                "display_order": 2,
            },
            {
                "id": "dest-santiago",
                "title": "Santiago",
                "country": "Chile",
                "flag": "🇨🇱",
                "category": "international",
                "tag": "Andes & Vinhedos",
                "description": "A imponência da Cordilheira dos Andes, vinícolas renomadas mundialmente e rica herança cultural.",
                "starting_price": 720.00,
                "accommodations_count": 115,
                "link": "/hospedagens?city=Santiago",
                "image_url": "https://images.pexels.com/photos/2017747/pexels-photo-2017747.jpeg",
                "display_order": 3,
            },
            {
                "id": "dest-rio",
                "title": "Rio de Janeiro",
                "country": "Brasil",
                "flag": "🇧🇷",
                "category": "national",
                "tag": "Cidade Maravilhosa",
                "description": "Copacabana, Ipanema, Cristo Redentor e uma atmosfera vibrante que encanta viajantes de todo o planeta.",
                "starting_price": 850.00,
                "accommodations_count": 260,
                "link": "/hospedagens?city=Rio%20de%20Janeiro",
                "image_url": "https://images.pexels.com/photos/720300/pexels-photo-720300.jpeg",
                "display_order": 4,
            },
        ]
        for d in destinations_data:
            if not db.query(Destination).filter(Destination.id == d["id"]).first():
                db.add(Destination(**d))

        # 5. Adicionais de Checkout (Addons)
        addons_data = [
            {
                "id": "addon-insurance",
                "title": "Seguro Viagem Zarpou Proteção Total",
                "description": "Cobertura médica hospitalar de até R$ 150.000, extravio de bagagem e cancelamento involuntário.",
                "price": 68.0,
                "category": "seguro",
                "is_active": True,
            },
            {
                "id": "addon-baggage",
                "title": "Bagagem Despachada Extra 23kg",
                "description": "Garanta espaço extra para suas compras e lembranças de viagem com tarifa promocional.",
                "price": 110.0,
                "category": "bagagem",
                "is_active": True,
            },
            {
                "id": "addon-transfer",
                "title": "Transfer Executivo Aeroporto / Hotel",
                "description": "Recepção privativa com motorista credenciado e veículo climatizado na chegada e partida.",
                "price": 140.0,
                "category": "traslado",
                "is_active": True,
            },
        ]
        for a in addons_data:
            if not db.query(Addon).filter(Addon.id == a["id"]).first():
                db.add(Addon(**a))

        # 6. Promoções
        promos_data = [
            {
                "id": "promo-1",
                "title": "Temporada Nordeste dos Sonhos",
                "subtitle": "Resorts pé na areia em Porto Seguro, Maceió e Natal com condições exclusivas.",
                "badge": "OFERTA RELÂMPAGO",
                "discount_text": "Até 35% OFF",
                "image_url": "https://images.pexels.com/photos/12039523/pexels-photo-12039523.jpeg",
                "link": "/hospedagens?city=Búzios",
                "button_text": "Aproveitar Oferta",
                "active": True,
                "display_order": 1,
            },
            {
                "id": "promo-2",
                "title": "Viva a Magia do Rio de Janeiro",
                "subtitle": "Hotéis selecionados com vista para o mar e cancelamento grátis em até 12x sem juros.",
                "badge": "MAIS BUSCADO",
                "discount_text": "Em até 12x s/ juros",
                "image_url": "https://images.pexels.com/photos/720300/pexels-photo-720300.jpeg",
                "link": "/hospedagens?city=Rio%20de%20Janeiro",
                "button_text": "Ver Hotéis no Rio",
                "active": True,
                "display_order": 2,
            },
            {
                "id": "promo-3",
                "title": "Passagens Internacionais com Preço Especial",
                "subtitle": "Miami, Santiago, Roma e Madri com saídas de Belo Horizonte e São Paulo.",
                "badge": "INTERNACIONAL",
                "discount_text": "A partir de R$ 1.890",
                "image_url": "https://images.pexels.com/photos/3834331/pexels-photo-3834331.jpeg",
                "link": "/passagens?to=MIA",
                "button_text": "Buscar Passagens",
                "active": True,
                "display_order": 3,
            },
        ]
        for p in promos_data:
            if not db.query(Promotion).filter(Promotion.id == p["id"]).first():
                db.add(Promotion(**p))

        # 7. Hotéis e Quartos
        hotels_data = [
            {
                "id": "hotel-rio-copacabana",
                "name": "Copacabana Palace Grand Luxury",
                "city": "Rio de Janeiro",
                "state": "RJ",
                "country": "Brasil",
                "stars": 5,
                "rating": 9.4,
                "review_count": 1420,
                "review_label": "Excelente",
                "address": "Av. Atlântica, 1702 - Copacabana",
                "neighborhood": "Copacabana",
                "description": "Ícone da hotelaria mundial de frente para a praia de Copacabana. Desfrute de serviços exclusivos, piscina semiolímpica, spa internacional e gastronomia premiada.",
                "image_url": "https://images.pexels.com/photos/720300/pexels-photo-720300.jpeg",
                "gallery": [
                    "https://images.pexels.com/photos/720300/pexels-photo-720300.jpeg",
                    "https://images.pexels.com/photos/271624/pexels-photo-271624.jpeg",
                    "https://images.pexels.com/photos/164595/pexels-photo-164595.jpeg",
                ],
                "amenities": ["Piscina", "Wi-Fi Grátis", "Café da Manhã Incluso", "Academia", "Frente à Praia", "Spa", "Restaurante", "Ar-condicionado"],
                "base_price_per_night": 850.0,
                "original_price_per_night": 1100.0,
                "discount_percent": 22,
                "max_installments": 12,
                "badges": ["Recomendado", "Oferta Zarpou"],
                "featured": True,
                "rooms": [
                    {
                        "id": "room-copa-standard",
                        "name": "Apartamento Superior Vista Cidade",
                        "description": "Cama Queen Size, enxoval de algodão egípcio, banheiro em mármore e isolamento acústico.",
                        "max_adults": 2,
                        "max_children": 1,
                        "beds": "1 Cama Queen ou 2 Camas de Solteiro",
                        "size_m2": 32,
                        "price_per_night": 850.0,
                        "original_price_per_night": 1100.0,
                        "free_cancellation": True,
                        "breakfast_included": True,
                        "available_rooms": 4,
                        "amenities": ["Wi-Fi rápido", "TV 50'", "Ar-condicionado", "Frigobar"],
                    },
                    {
                        "id": "room-copa-ocean",
                        "name": "Suíte Luxo Frente Mar",
                        "description": "Varanda privativa com vista panorâmica para o oceano, banheira de imersão e serviço de mordomo.",
                        "max_adults": 2,
                        "max_children": 2,
                        "beds": "1 Cama King Size",
                        "size_m2": 55,
                        "price_per_night": 1450.0,
                        "original_price_per_night": 1750.0,
                        "free_cancellation": True,
                        "breakfast_included": True,
                        "available_rooms": 2,
                        "amenities": ["Vista Mar", "Varanda", "Banheira", "Wi-Fi rápido"],
                    },
                ],
            },
            {
                "id": "hotel-buzios-resort",
                "name": "Búzios Beach & Spa Resort",
                "city": "Armação dos Búzios",
                "state": "RJ",
                "country": "Brasil",
                "stars": 4,
                "rating": 8.9,
                "review_count": 890,
                "review_label": "Fabuloso",
                "address": "Rua das Pedras, 450 - Centro",
                "neighborhood": "Ferradura",
                "description": "Charme, exclusividade e contato direto com as praias mais desejadas de Búzios. Ambiente aconchegante com piscina aquecida e alta gastronomia.",
                "image_url": "https://images.pexels.com/photos/12039523/pexels-photo-12039523.jpeg",
                "gallery": [
                    "https://images.pexels.com/photos/12039523/pexels-photo-12039523.jpeg",
                    "https://images.pexels.com/photos/258154/pexels-photo-258154.jpeg",
                ],
                "amenities": ["Piscina", "Wi-Fi Grátis", "Café da Manhã", "Estacionamento", "Bar Molhado"],
                "base_price_per_night": 520.0,
                "original_price_per_night": 650.0,
                "discount_percent": 20,
                "max_installments": 10,
                "badges": ["Mais Vendido"],
                "featured": True,
                "rooms": [
                    {
                        "id": "room-buzios-std",
                        "name": "Bangalô Jardim Confort",
                        "description": "Rodeado por jardins tropicais, com rede na varanda e decoração praiana sofisticada.",
                        "max_adults": 2,
                        "max_children": 1,
                        "beds": "1 Cama Queen",
                        "size_m2": 28,
                        "price_per_night": 520.0,
                        "original_price_per_night": 650.0,
                        "free_cancellation": True,
                        "breakfast_included": True,
                        "available_rooms": 5,
                        "amenities": ["Varanda c/ rede", "Ar-condicionado", "Smart TV"],
                    }
                ],
            },
            {
                "id": "hotel-dubai-royal",
                "name": "The Royal Mirage Dubai",
                "city": "Dubai",
                "state": "Dubai",
                "country": "Emirados Árabes Unidos",
                "stars": 5,
                "rating": 9.6,
                "review_count": 2100,
                "review_label": "Excelente",
                "address": "King Salman Bin Abdulaziz Al Saud St - Al Sufouh",
                "neighborhood": "Jumeirah Beach",
                "description": "Palácio espetacular com praia privativa, quilômetros de jardins deslumbrantes e a mais sofisticada experiência de luxo árabe.",
                "image_url": "https://images.pexels.com/photos/3769312/pexels-photo-3769312.jpeg",
                "gallery": [
                    "https://images.pexels.com/photos/3769312/pexels-photo-3769312.jpeg",
                ],
                "amenities": ["Praia Privativa", "8 Restaurantes de Luxo", "Spa Oriental", "Piscina Infinita"],
                "base_price_per_night": 1650.0,
                "original_price_per_night": 2100.0,
                "discount_percent": 21,
                "max_installments": 12,
                "badges": ["Internacional de Luxo", "Top Avaliação"],
                "featured": True,
                "rooms": [
                    {
                        "id": "room-dubai-deluxe",
                        "name": "Arabian Court Deluxe Room",
                        "description": "Arquitetura árabe refinada com varanda privativa com vista para os jardins e golfo.",
                        "max_adults": 2,
                        "max_children": 1,
                        "beds": "1 Cama King",
                        "size_m2": 50,
                        "price_per_night": 1650.0,
                        "original_price_per_night": 2100.0,
                        "free_cancellation": True,
                        "breakfast_included": True,
                        "available_rooms": 3,
                        "amenities": ["Varanda", "Banheiro em mármore", "Wi-Fi premium"],
                    }
                ],
            },
        ]
        for h_data in hotels_data:
            rooms_list = h_data.pop("rooms", [])
            hotel = db.query(Hotel).filter(Hotel.id == h_data["id"]).first()
            if not hotel:
                hotel = Hotel(**h_data)
                db.add(hotel)
                db.flush()
                for r_data in rooms_list:
                    room = Room(hotel_id=hotel.id, **r_data)
                    db.add(room)

        # 8. Voos
        flights_data = [
            {
                "id": "flight-bh-miami",
                "price": 3450.0,
                "original_price": 4200.0,
                "discount_percent": 18,
                "max_installments": 12,
                "featured": True,
                "country": "Estados Unidos",
                "flag": "🇺🇸",
                "region": "usa",
                "image_url": "https://images.pexels.com/photos/3834331/pexels-photo-3834331.jpeg",
                "highlights": ["Praias de South Beach", "Compras & Gastronomia"],
                "is_round_trip": True,
                "outbound": {
                    "segment_type": "outbound",
                    "flight_number": "ZP-8412",
                    "airline": "LATAM Airlines",
                    "airline_code": "LA",
                    "origin_iata": "CNF",
                    "origin_city": "Belo Horizonte",
                    "origin_airport": "Aeroporto Internacional de Confins",
                    "destination_iata": "MIA",
                    "destination_city": "Miami",
                    "destination_airport": "Miami International Airport",
                    "departure_date": date(2026, 11, 20),
                    "departure_time": "10:15",
                    "arrival_date": date(2026, 11, 20),
                    "arrival_time": "18:40",
                    "duration": "9h 25m",
                    "stops": 1,
                    "stop_city": "São Paulo (GRU)",
                    "cabin_class": "Econômica",
                    "baggage_included": True,
                    "hand_baggage_included": True,
                },
                "return_flight": {
                    "segment_type": "return",
                    "flight_number": "ZP-8413",
                    "airline": "LATAM Airlines",
                    "airline_code": "LA",
                    "origin_iata": "MIA",
                    "origin_city": "Miami",
                    "origin_airport": "Miami International Airport",
                    "destination_iata": "CNF",
                    "destination_city": "Belo Horizonte",
                    "destination_airport": "Aeroporto Internacional de Confins",
                    "departure_date": date(2026, 11, 27),
                    "departure_time": "21:00",
                    "arrival_date": date(2026, 11, 28),
                    "arrival_time": "07:10",
                    "duration": "9h 10m",
                    "stops": 1,
                    "stop_city": "São Paulo (GRU)",
                    "cabin_class": "Econômica",
                    "baggage_included": True,
                    "hand_baggage_included": True,
                },
            },
            {
                "id": "flight-sp-roma",
                "price": 4890.0,
                "original_price": 5800.0,
                "discount_percent": 15,
                "max_installments": 12,
                "featured": True,
                "country": "Itália",
                "flag": "🇮🇹",
                "region": "europe",
                "image_url": "https://images.pexels.com/photos/6318793/pexels-photo-6318793.jpeg",
                "highlights": ["Coliseu & Vaticano", "Voo Noturno Direto"],
                "is_round_trip": True,
                "outbound": {
                    "segment_type": "outbound",
                    "flight_number": "ZP-7701",
                    "airline": "ITA Airways",
                    "airline_code": "AZ",
                    "origin_iata": "GRU",
                    "origin_city": "São Paulo",
                    "origin_airport": "Aeroporto de Guarulhos",
                    "destination_iata": "FCO",
                    "destination_city": "Roma",
                    "destination_airport": "Aeroporto Fiumicino",
                    "departure_date": date(2026, 11, 15),
                    "departure_time": "14:30",
                    "arrival_date": date(2026, 11, 16),
                    "arrival_time": "07:00",
                    "duration": "11h 30m",
                    "stops": 0,
                    "cabin_class": "Econômica",
                    "baggage_included": True,
                    "hand_baggage_included": True,
                },
            },
        ]
        for f_data in flights_data:
            out_seg_data = f_data.pop("outbound", None)
            ret_seg_data = f_data.pop("return_flight", None)
            flight = db.query(Flight).filter(Flight.id == f_data["id"]).first()
            if not flight:
                flight = Flight(**f_data)
                db.add(flight)
                db.flush()
                if out_seg_data:
                    out_seg = FlightSegment(
                        id=f"seg-{flight.id}-out",
                        flight_id=flight.id,
                        **out_seg_data
                    )
                    db.add(out_seg)
                if ret_seg_data:
                    ret_seg = FlightSegment(
                        id=f"seg-{flight.id}-ret",
                        flight_id=flight.id,
                        **ret_seg_data
                    )
                    db.add(ret_seg)

        db.commit()
        print("Carga inicial de dados (seeds) executada com sucesso!")
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    run_seeds()
