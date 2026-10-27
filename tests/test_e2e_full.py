import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_01_health_and_root():
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json()["status"] == "online"

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"


def test_02_public_catalog():
    # Destinos
    res_dest = client.get("/api/v1/destinations")
    assert res_dest.status_code == 200
    destinations = res_dest.json()
    assert len(destinations) >= 4
    assert any(d["title"] == "Dubai" for d in destinations)

    # Hero
    res_hero = client.get("/api/v1/agency/hero")
    assert res_hero.status_code == 200
    assert "titleHighlight" in res_hero.json()

    # Hotéis
    res_hotels = client.get("/api/v1/hotels")
    assert res_hotels.status_code == 200
    hotels = res_hotels.json()
    assert len(hotels) >= 3
    hotel_id = hotels[0]["id"]
    res_h = client.get(f"/api/v1/hotels/{hotel_id}")
    assert res_h.status_code == 200
    assert res_h.json()["name"] == hotels[0]["name"]

    # Voos
    res_flights = client.get("/api/v1/flights")
    assert res_flights.status_code == 200
    flights = res_flights.json()
    assert len(flights) >= 2

    # Addons
    res_addons = client.get("/api/v1/addons")
    assert res_addons.status_code == 200
    assert len(res_addons.json()) >= 3

    # Promoções
    res_promos = client.get("/api/v1/promotions")
    assert res_promos.status_code == 200
    assert len(res_promos.json()) >= 3


def test_03_authentication_flows():
    # 1. Login Admin Padrão (JSON)
    login_adm = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@zarpou.com.br", "password": "admin123"},
    )
    assert login_adm.status_code == 200
    adm_token = login_adm.json()["access_token"]
    assert adm_token

    # Admin Me
    me_adm = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {adm_token}"})
    assert me_adm.status_code == 200
    assert me_adm.json()["role"] == "admin"

    # 2. Cadastro de Cliente B2C
    cust_data = {
        "fullName": "Mariana Souza",
        "email": "mariana.souza@exemplo.com",
        "password": "senhaSegura123",
        "cpf": "52998224725",
        "phone": "(11) 99887-6655",
    }
    res_reg = client.post("/api/v1/auth/customer/register", json=cust_data)
    assert res_reg.status_code in [201, 400]  # Se já cadastrado em teste anterior, 400

    # 3. Login Cliente B2C
    res_cust_login = client.post(
        "/api/v1/auth/customer/login",
        json={"email": cust_data["email"], "password": cust_data["password"]},
    )
    assert res_cust_login.status_code == 200
    cust_token = res_cust_login.json()["access_token"]
    assert cust_token

    # Cliente Me
    me_cust = client.get("/api/v1/auth/customer/me", headers={"Authorization": f"Bearer {cust_token}"})
    assert me_cust.status_code == 200
    assert me_cust.json()["fullName"] == "Mariana Souza"


def test_04_b2b_corporate_portal():
    # Obter token de Admin
    login_adm = client.post("/api/v1/auth/login", json={"email": "admin@zarpou.com.br", "password": "admin123"})
    adm_token = login_adm.json()["access_token"]
    adm_headers = {"Authorization": f"Bearer {adm_token}"}

    # 1. Cadastro B2B
    comp_data = {
        "cnpj": "99.888.777/0001-66",
        "razaoSocial": "Global Logistics Brasil S/A",
        "nomeFantasia": "GlobalLog",
        "corporateEmail": "financeiro@globallog.com.br",
        "phone": "(11) 4004-1234",
        "managerName": "Roberto Albuquerque",
        "managerCpf": "999.888.777-66",
        "password": "empresaSenha123",
        "estimatedMonthlySpend": 25000.00,
        "paymentTerms": "faturado_30d",
    }
    reg_comp = client.post("/api/v1/companies/register", json=comp_data)
    if reg_comp.status_code == 201:
        comp_id = reg_comp.json()["id"]
    else:
        clean_cnpj = "".join(filter(str.isdigit, comp_data["cnpj"]))
        comp_list = client.get("/api/v1/companies/admin", headers=adm_headers).json()
        comp_id = next(c["id"] for c in comp_list if "".join(filter(str.isdigit, c["cnpj"])) == clean_cnpj)

    # 2. Backoffice Admin aprova empresa e define crédito
    approval = client.put(
        f"/api/v1/companies/{comp_id}/approval",
        headers=adm_headers,
        json={
            "status": "aprovada",
            "creditLimit": 40000.00,
            "corporateDiscountPercent": 12.00,
            "paymentTerms": "faturado_30d",
        },
    )
    assert approval.status_code == 200
    assert approval.json()["status"] == "aprovada"
    assert approval.json()["creditLimit"] == 40000.00

    # 3. Login Corporativo
    comp_login = client.post(
        "/api/v1/companies/login",
        json={"login": "financeiro@globallog.com.br", "password": "empresaSenha123"},
    )
    assert comp_login.status_code == 200
    comp_token = comp_login.json()["access_token"]
    comp_headers = {"Authorization": f"Bearer {comp_token}"}

    # 4. Adicionar colaborador corporativo
    emp_res = client.post(
        "/api/v1/companies/me/employees",
        headers=comp_headers,
        json={
            "fullName": "Juliana Paes Logística",
            "cpf": "555.444.333-22",
            "email": "juliana@globallog.com.br",
            "phone": "(11) 91234-5678",
            "costCenter": "Operações Sul",
            "department": "Transportes",
        },
    )
    assert emp_res.status_code in [201, 200]

    # Listar colaboradores da empresa
    emp_list = client.get("/api/v1/companies/me/employees", headers=comp_headers)
    assert emp_list.status_code == 200
    assert len(emp_list.json()) >= 1


def test_05_booking_and_checkout():
    # 1. Login Cliente B2C
    login_cust = client.post(
        "/api/v1/auth/customer/login",
        json={"email": "mariana.souza@exemplo.com", "password": "senhaSegura123"},
    )
    cust_token = login_cust.json()["access_token"]
    cust_headers = {"Authorization": f"Bearer {cust_token}"}

    # Obter um hotel e quarto
    hotels = client.get("/api/v1/hotels").json()
    hotel = hotels[0]
    room = hotel["rooms"][0]

    # Checkout B2C via Pix
    booking_payload = {
        "productType": "hotel",
        "hotelId": hotel["id"],
        "selectedRoomId": room["id"],
        "checkInDate": "2026-11-20",
        "checkOutDate": "2026-11-25",
        "nights": 5,
        "adults": 2,
        "children": 0,
        "travelers": [
            {
                "fullName": "Mariana Souza",
                "email": "mariana.souza@exemplo.com",
                "documentType": "CPF",
                "documentNumber": "123.456.789-00",
                "phone": "(11) 99887-6655",
                "birthDate": "1992-05-15",
                "gender": "F",
                "isPrimary": True,
            }
        ],
        "addons": [],
        "paymentMethod": "pix",
        "installments": 1,
    }
    b_res = client.post("/api/v1/bookings/checkout", headers=cust_headers, json=booking_payload)
    assert b_res.status_code == 201
    b_data = b_res.json()
    assert b_data["locatorCode"].startswith("ZRP-")
    assert b_data["status"] == "pendente_pagamento"
    assert b_data["pixCode"] is not None

    # Consulta unificada por Localizador (PNR) - titular autenticado
    locator = b_data["locatorCode"]
    lookup_res = client.get(f"/api/v1/bookings/{locator}", headers=cust_headers)
    assert lookup_res.status_code == 200
    assert lookup_res.json()["locatorCode"] == locator

    # IDOR: consulta anônima sem e-mail do titular deve ser negada
    anon_res = client.get(f"/api/v1/bookings/{locator}")
    assert anon_res.status_code == 404

    # Minhas Viagens do Cliente
    my_trips = client.get("/api/v1/bookings/my-trips", headers=cust_headers)
    assert my_trips.status_code == 200
    assert len(my_trips.json()) >= 1

    # 2. Checkout B2B Faturado (Corporate Invoice) com desconto corporativo
    comp_login = client.post(
        "/api/v1/companies/login",
        json={"login": "financeiro@globallog.com.br", "password": "empresaSenha123"},
    )
    comp_token = comp_login.json()["access_token"]
    comp_headers = {"Authorization": f"Bearer {comp_token}"}

    # Perfil antes da reserva
    comp_me_before = client.get("/api/v1/companies/me", headers=comp_headers).json()
    credit_before = comp_me_before["creditAvailable"]

    corp_booking_payload = {
        "productType": "hotel",
        "hotelId": hotel["id"],
        "selectedRoomId": room["id"],
        "checkInDate": "2026-12-01",
        "checkOutDate": "2026-12-03",
        "nights": 2,
        "adults": 1,
        "children": 0,
        "travelers": [
            {
                "fullName": "Juliana Paes Logística",
                "email": "juliana@globallog.com.br",
                "documentType": "CPF",
                "documentNumber": "555.444.333-22",
                "phone": "(11) 91234-5678",
                "birthDate": "1990-08-20",
                "gender": "F",
                "isPrimary": True,
            }
        ],
        "addons": [],
        "paymentMethod": "corporate_invoice",
        "costCenter": "Operações Sul",
    }
    corp_b_res = client.post("/api/v1/bookings/checkout", headers=comp_headers, json=corp_booking_payload)
    assert corp_b_res.status_code == 201
    corp_b_data = corp_b_res.json()
    assert corp_b_data["status"] == "confirmada"
    assert corp_b_data["companyId"] == comp_me_before["id"]
    assert corp_b_data["costCenter"] == "Operações Sul"

    # Verificar que o crédito da empresa foi devidamente deduzido
    comp_me_after = client.get("/api/v1/companies/me", headers=comp_headers).json()
    assert comp_me_after["creditAvailable"] < credit_before


def test_06_inquiries_and_crm():
    inquiry_data = {
        "fullName": "Fernando Bastos",
        "email": "fernando.bastos@exemplo.com",
        "phone": "(31) 98765-4321",
        "destination": "Paris & Roma",
        "startDate": "2026-12-10",
        "endDate": "2026-12-24",
        "numberOfAdults": "2",
        "numberOfChildren": "1",
        "travelType": "luxury",
        "estimatedBudget": "35000",
        "additionalInfo": "Quartos conjugados e guia em português.",
    }
    res = client.post("/api/v1/inquiries", json=inquiry_data)
    assert res.status_code == 201
    assert res.json()["status"] == "novo"

    # Admin consulta leads
    login_adm = client.post("/api/v1/auth/login", json={"email": "admin@zarpou.com.br", "password": "admin123"})
    adm_token = login_adm.json()["access_token"]
    leads = client.get("/api/v1/inquiries", headers={"Authorization": f"Bearer {adm_token}"})
    assert leads.status_code == 200
    assert any(lead["email"] == "fernando.bastos@exemplo.com" for lead in leads.json())


def test_07_agency_settings_and_metrics():
    login_adm = client.post("/api/v1/auth/login", json={"email": "admin@zarpou.com.br", "password": "admin123"})
    adm_token = login_adm.json()["access_token"]
    adm_headers = {"Authorization": f"Bearer {adm_token}"}

    # Leitura de configurações atuais
    cfg_get = client.get("/api/v1/agency/settings")
    assert cfg_get.status_code == 200
    curr_cfg = cfg_get.json()

    # Atualização dinâmica de credenciais e parâmetros
    curr_cfg["resendApiKey"] = "re_test_987654321"
    curr_cfg["paymentGateway"]["provider"] = "mercadopago"
    curr_cfg["paymentGateway"]["secretKey"] = "APP_USR-test-secret-key"
    curr_cfg["paymentGateway"]["publicKey"] = "APP_USR-test-public-key"
    curr_cfg["aiChat"]["apiKey"] = "sk-test-ai-key-12345"

    cfg_put = client.put("/api/v1/agency/settings", headers=adm_headers, json=curr_cfg)
    assert cfg_put.status_code == 200
    saved = cfg_put.json()
    assert saved["resendApiKey"] == "re_test_987654321"
    assert saved["paymentGateway"]["secretKey"] == "APP_USR-test-secret-key"
    assert saved["aiChat"]["apiKey"] == "sk-test-ai-key-12345"

    # Métricas do Dashboard (/dashboard e /metrics)
    metrics1 = client.get("/api/v1/agency/dashboard", headers=adm_headers)
    assert metrics1.status_code == 200
    assert "totalBookings" in metrics1.json()

    metrics2 = client.get("/api/v1/agency/metrics", headers=adm_headers)
    assert metrics2.status_code == 200
    assert metrics2.json()["totalBookings"] >= 2


def test_08_ai_concierge_chat():
    session_id = "test-session-e2e-123"

    # Pergunta sobre Hotéis
    req_hotel = {
        "message": "Quais hotéis luxuosos vocês recomendam?",
        "sessionId": session_id,
    }
    chat_h = client.post("/api/v1/chat", json=req_hotel)
    assert chat_h.status_code == 200
    res_h = chat_h.json()
    assert "Copacabana Palace" in res_h["reply"]
    assert len(res_h["suggestedActions"]) > 0

    # Pergunta sobre Voos
    req_flight = {
        "message": "Vocês têm passagens para Miami saindo de BH?",
        "sessionId": session_id,
    }
    chat_f = client.post("/api/v1/chat", json=req_flight)
    assert chat_f.status_code == 200
    res_f = chat_f.json()
    assert "Miami" in res_f["reply"]

    # Histórico de Chat exige autenticação do titular (LGPD / IDOR)
    hist_anon = client.get(f"/api/v1/chat/history?sessionId={session_id}")
    assert hist_anon.status_code == 401

    # Cliente logado consulta o próprio histórico (sessão anônima não pertence a ele -> vazio)
    cust_login = client.post(
        "/api/v1/auth/customer/login",
        json={"email": "mariana.souza@exemplo.com", "password": "senhaSegura123"},
    )
    assert cust_login.status_code == 200
    cust_headers = {"Authorization": f"Bearer {cust_login.json()['access_token']}"}
    hist_res = client.get(f"/api/v1/chat/history?sessionId={session_id}", headers=cust_headers)
    assert hist_res.status_code == 200
    assert hist_res.json() == []
