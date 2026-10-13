-- ==============================================================================
-- MODELAGEM DE DADOS ZARPOU VIAGENS E TURISMO
-- Sistema Completo de Agência de Viagens (Hotéis, Passagens, Pacotes, Reservas, B2B e CMS)
-- Compatível com PostgreSQL, MySQL e SQLite (tipos ANSI SQL padrão)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. TABELA DE USUÁRIOS ADMINISTRATIVOS (Gestores e Agentes da Agência)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'admin', -- 'admin' (acesso total) ou 'personalizado' (definido por allowed_screens)
    allowed_screens TEXT DEFAULT '[]', -- JSON serializado com os IDs das telas autorizadas (ex: ["dashboard", "reservas"])
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ------------------------------------------------------------------------------
-- 2. TABELA DE CLIENTES B2C (Viajantes cadastrados na plataforma)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    phone VARCHAR(30),
    cpf VARCHAR(20),
    birth_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    notification_whatsapp_promotions BOOLEAN NOT NULL DEFAULT TRUE,
    notification_email_promotions BOOLEAN NOT NULL DEFAULT TRUE,
    notification_updated_at TIMESTAMP WITH TIME ZONE,
    two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    two_factor_method VARCHAR(20) DEFAULT 'email',
    two_factor_secret VARCHAR(255),
    two_factor_backup_codes TEXT,
    two_factor_confirmed_at TIMESTAMP WITH TIME ZONE,
    two_factor_temp_code VARCHAR(10),
    two_factor_temp_code_expires_at TIMESTAMP WITH TIME ZONE,
    accepted_privacy_policy BOOLEAN NOT NULL DEFAULT FALSE,
    accepted_terms_of_use BOOLEAN NOT NULL DEFAULT FALSE,
    consent_version VARCHAR(20),
    consent_at TIMESTAMP WITH TIME ZONE,
    consent_ip VARCHAR(64),
    anonymized_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_cpf ON customers(cpf);
CREATE INDEX IF NOT EXISTS idx_customers_promo_email ON customers(notification_email_promotions);
CREATE INDEX IF NOT EXISTS idx_customers_promo_wa ON customers(notification_whatsapp_promotions);

-- ------------------------------------------------------------------------------
-- 3. TABELA DE EMPRESAS CONVENIADAS (Zarpou Empresas - B2B Corporativo)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR(50) PRIMARY KEY,
    cnpj VARCHAR(30) NOT NULL UNIQUE,
    razao_social VARCHAR(255) NOT NULL,
    nome_fantasia VARCHAR(255) NOT NULL,
    corporate_email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(30) NOT NULL,
    manager_name VARCHAR(255) NOT NULL,
    manager_cpf VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pendente', -- 'pendente', 'aprovada', 'bloqueada'
    corporate_discount_percent NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    credit_limit NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    credit_used NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    payment_terms VARCHAR(30) NOT NULL DEFAULT 'faturado_30d', -- 'faturado_15d', 'faturado_30d', 'cartao_corporativo'
    estimated_monthly_spend NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_companies_cnpj ON companies(cnpj);
CREATE INDEX IF NOT EXISTS idx_companies_email ON companies(corporate_email);
CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status);

-- ------------------------------------------------------------------------------
-- 4. TABELA DE COLABORADORES DA EMPRESA (Passageiros Corporativos)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company_employees (
    id VARCHAR(50) PRIMARY KEY,
    company_id VARCHAR(50) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    cpf VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(30),
    cost_center VARCHAR(100),
    department VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_employees_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_employees_company_id ON company_employees(company_id);
CREATE INDEX IF NOT EXISTS idx_employees_cpf ON company_employees(cpf);

-- ------------------------------------------------------------------------------
-- 5. TABELA DE FATURAS CORPORATIVAS A PRAZO (Company Invoices / Boletos PJ)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company_invoices (
    id VARCHAR(50) PRIMARY KEY,
    company_id VARCHAR(50) NOT NULL,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    due_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'aberta', -- 'aberta', 'fechada', 'paga', 'vencida'
    boleto_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invoices_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_invoices_company_id ON company_invoices(company_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON company_invoices(status);

-- ------------------------------------------------------------------------------
-- 6. TABELA DE DESTINOS POPULARES & CURADORIA (Home e Catálogo)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS destinations (
    id VARCHAR(50) PRIMARY KEY, -- ex: 'dest-dubai', 'dest-buzios'
    title VARCHAR(255) NOT NULL,
    country VARCHAR(100) NOT NULL,
    flag VARCHAR(20),
    category VARCHAR(50) NOT NULL DEFAULT 'all', -- 'all', 'national', 'international'
    tag VARCHAR(100),
    description TEXT,
    starting_price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    accommodations_count INT NOT NULL DEFAULT 0,
    link VARCHAR(255),
    image_url TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_destinations_category ON destinations(category);
CREATE INDEX IF NOT EXISTS idx_destinations_order ON destinations(display_order);

-- ------------------------------------------------------------------------------
-- 7. TABELA DE CONFIGURAÇÃO DO BANNER HERO (Página Inicial)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hero_configs (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'default',
    title_prefix VARCHAR(100) NOT NULL DEFAULT 'Seu',
    title_highlight VARCHAR(100) NOT NULL DEFAULT 'sonho',
    title_suffix VARCHAR(255) NOT NULL DEFAULT 'de viajar bem, agora é realidade',
    subtitle TEXT NOT NULL DEFAULT 'Reserve hotéis, passagens aéreas e pacotes com pagamento em até 12x sem juros e atendimento humano especializado.',
    bg_type VARCHAR(20) NOT NULL DEFAULT 'video', -- 'image' ou 'video'
    bg_image_url TEXT,
    bg_video_url TEXT,
    cta_text VARCHAR(100) NOT NULL DEFAULT 'Falar com um Especialista',
    cta_link VARCHAR(255) NOT NULL DEFAULT 'whatsapp',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------------------------
-- 8. TABELA DE HOTÉIS & HOSPEDAGENS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hotels (
    id VARCHAR(50) PRIMARY KEY, -- ex: 'hotel-rio-copacabana'
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50),
    country VARCHAR(100) NOT NULL DEFAULT 'Brasil',
    stars INT NOT NULL DEFAULT 4,
    rating NUMERIC(3, 1) NOT NULL DEFAULT 9.0,
    review_count INT NOT NULL DEFAULT 0,
    review_label VARCHAR(50) NOT NULL DEFAULT 'Excelente',
    address VARCHAR(255),
    neighborhood VARCHAR(100),
    description TEXT,
    image_url TEXT NOT NULL,
    gallery JSON,
    amenities JSON,
    base_price_per_night NUMERIC(10, 2) NOT NULL,
    original_price_per_night NUMERIC(10, 2),
    discount_percent INT DEFAULT 0,
    max_installments INT NOT NULL DEFAULT 12,
    badges JSON,
    featured BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hotels_city ON hotels(city);
CREATE INDEX IF NOT EXISTS idx_hotels_stars ON hotels(stars);
CREATE INDEX IF NOT EXISTS idx_hotels_featured ON hotels(featured);

-- ------------------------------------------------------------------------------
-- 9. TABELA DE QUARTOS DE HOTÉIS (Room Types / Disponibilidade)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rooms (
    id VARCHAR(50) PRIMARY KEY, -- ex: 'room-copa-standard'
    hotel_id VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    max_adults INT NOT NULL DEFAULT 2,
    max_children INT NOT NULL DEFAULT 0,
    beds VARCHAR(150),
    size_m2 INT,
    price_per_night NUMERIC(10, 2) NOT NULL,
    original_price_per_night NUMERIC(10, 2),
    free_cancellation BOOLEAN NOT NULL DEFAULT TRUE,
    breakfast_included BOOLEAN NOT NULL DEFAULT TRUE,
    available_rooms INT NOT NULL DEFAULT 5,
    image_url TEXT,
    amenities JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_rooms_hotel FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rooms_hotel_id ON rooms(hotel_id);

-- ------------------------------------------------------------------------------
-- 10. TABELA DE PASSAGENS AÉREAS (Ofertas e Voos)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS flights (
    id VARCHAR(50) PRIMARY KEY, -- ex: 'flight-bh-miami'
    price NUMERIC(10, 2) NOT NULL,
    original_price NUMERIC(10, 2),
    discount_percent INT DEFAULT 0,
    max_installments INT NOT NULL DEFAULT 12,
    is_round_trip BOOLEAN NOT NULL DEFAULT TRUE,
    featured BOOLEAN NOT NULL DEFAULT FALSE,
    country VARCHAR(100),
    flag VARCHAR(20),
    region VARCHAR(50) NOT NULL DEFAULT 'all', -- 'all', 'usa', 'europe', 'south-america', 'other'
    image_url TEXT,
    highlights JSON,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_flights_region ON flights(region);
CREATE INDEX IF NOT EXISTS idx_flights_featured ON flights(featured);

-- ------------------------------------------------------------------------------
-- 11. TABELA DE SEGMENTOS DE VOO (Ida e Volta)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS flight_segments (
    id VARCHAR(50) PRIMARY KEY,
    flight_id VARCHAR(50) NOT NULL,
    segment_type VARCHAR(20) NOT NULL, -- 'outbound' ou 'return'
    flight_number VARCHAR(30) NOT NULL,
    airline VARCHAR(100) NOT NULL,
    airline_code VARCHAR(10) NOT NULL,
    airline_logo TEXT,
    origin_iata VARCHAR(10) NOT NULL,
    origin_city VARCHAR(100) NOT NULL,
    origin_airport VARCHAR(255) NOT NULL,
    destination_iata VARCHAR(10) NOT NULL,
    destination_city VARCHAR(100) NOT NULL,
    destination_airport VARCHAR(255) NOT NULL,
    departure_date DATE NOT NULL,
    departure_time VARCHAR(10) NOT NULL,
    arrival_date DATE NOT NULL,
    arrival_time VARCHAR(10) NOT NULL,
    duration VARCHAR(50),
    stops INT NOT NULL DEFAULT 0,
    stop_city VARCHAR(100),
    cabin_class VARCHAR(50) NOT NULL DEFAULT 'Econômica',
    baggage_included BOOLEAN NOT NULL DEFAULT TRUE,
    hand_baggage_included BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_segments_flight FOREIGN KEY (flight_id) REFERENCES flights(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_segments_flight_id ON flight_segments(flight_id);
CREATE INDEX IF NOT EXISTS idx_segments_routes ON flight_segments(origin_iata, destination_iata);

-- ------------------------------------------------------------------------------
-- 12. TABELA DE PACOTES DE VIAGEM (Voo + Hotel Integrados)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS packages (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    destination_city VARCHAR(100) NOT NULL,
    duration_nights INT NOT NULL DEFAULT 3,
    hotel_id VARCHAR(50),
    flight_id VARCHAR(50),
    price_per_person NUMERIC(10, 2) NOT NULL,
    original_price_per_person NUMERIC(10, 2),
    discount_percent INT DEFAULT 0,
    max_installments INT NOT NULL DEFAULT 12,
    image_url TEXT NOT NULL,
    highlights JSON,
    featured BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_packages_hotel FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE SET NULL,
    CONSTRAINT fk_packages_flight FOREIGN KEY (flight_id) REFERENCES flights(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------------------------
-- 13. TABELA DE PROMOÇÕES & BANNERS (Campanhas Comerciais)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS promotions (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    subtitle TEXT,
    badge VARCHAR(100),
    discount_text VARCHAR(100),
    image_url TEXT NOT NULL,
    link VARCHAR(255) NOT NULL,
    button_text VARCHAR(100) NOT NULL DEFAULT 'Aproveitar Oferta',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    start_date DATE,
    end_date DATE,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_promotions_active ON promotions(active, display_order);

-- ------------------------------------------------------------------------------
-- 14. TABELA DE ITENS ADICIONAIS DE RESERVA (Add-ons)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS addons (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    category VARCHAR(50) NOT NULL, -- 'seguro', 'bagagem', 'traslado', 'outro'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------------------------
-- 15. TABELA DE RESERVAS (Bookings & Pedidos - B2C e B2B Corporativo)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bookings (
    id VARCHAR(50) PRIMARY KEY,
    locator_code VARCHAR(20) NOT NULL UNIQUE, -- Código PNR: 'ZRP-849201'
    customer_id VARCHAR(36),
    company_id VARCHAR(50), -- Preenchido quando for compra corporativa B2B
    cost_center VARCHAR(100), -- Centro de Custo para prestação de contas PJ
    product_type VARCHAR(20) NOT NULL, -- 'hotel', 'flight', 'package'
    status VARCHAR(30) NOT NULL DEFAULT 'pendente_pagamento', -- 'confirmada', 'pendente_pagamento', 'cancelada', 'concluida'
    
    -- Relacionamento com o produto
    hotel_id VARCHAR(50),
    room_id VARCHAR(50),
    flight_id VARCHAR(50),
    package_id VARCHAR(50),
    
    -- Datas e capacidade
    check_in_date DATE,
    check_out_date DATE,
    nights INT,
    adults_count INT NOT NULL DEFAULT 1,
    children_count INT NOT NULL DEFAULT 0,
    
    -- Forma de Pagamento e Parcelas
    payment_method VARCHAR(30) NOT NULL, -- 'credit_card', 'pix', 'boleto', 'corporate_invoice'
    installments INT NOT NULL DEFAULT 1,
    
    -- Resumo Financeiro
    base_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    taxes_and_fees NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    addons_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    discount_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    final_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    
    -- Dados de Faturamento / Pagamento Instantâneo
    pix_code TEXT,
    pix_qr_code_url TEXT,
    pix_expires_at TIMESTAMP WITH TIME ZONE,
    boleto_barcode VARCHAR(100),
    voucher_url TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_bookings_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    CONSTRAINT fk_bookings_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL,
    CONSTRAINT fk_bookings_hotel FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE SET NULL,
    CONSTRAINT fk_bookings_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL,
    CONSTRAINT fk_bookings_flight FOREIGN KEY (flight_id) REFERENCES flights(id) ON DELETE SET NULL,
    CONSTRAINT fk_bookings_package FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_bookings_locator ON bookings(locator_code);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_customer ON bookings(customer_id);
CREATE INDEX IF NOT EXISTS idx_bookings_company ON bookings(company_id);

-- ------------------------------------------------------------------------------
-- 16. TABELA DE VIAJANTES / PASSAGEIROS DA RESERVA
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS booking_travelers (
    id VARCHAR(50) PRIMARY KEY,
    booking_id VARCHAR(50) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(20) NOT NULL DEFAULT 'CPF',
    document_number VARCHAR(50) NOT NULL,
    birth_date DATE NOT NULL,
    gender VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_travelers_booking FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_travelers_booking_id ON booking_travelers(booking_id);
CREATE INDEX IF NOT EXISTS idx_travelers_email ON booking_travelers(email);

-- ------------------------------------------------------------------------------
-- 17. TABELA DE ADICIONAIS CONTRATADOS NA RESERVA
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS booking_addons (
    id VARCHAR(50) PRIMARY KEY,
    booking_id VARCHAR(50) NOT NULL,
    addon_id VARCHAR(50),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_booking_addons_booking FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    CONSTRAINT fk_booking_addons_addon FOREIGN KEY (addon_id) REFERENCES addons(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_booking_addons_booking ON booking_addons(booking_id);

-- ------------------------------------------------------------------------------
-- 18. TABELA DE TRANSAÇÕES E GATEWAYS DE PAGAMENTO
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    id VARCHAR(50) PRIMARY KEY,
    booking_id VARCHAR(50) NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    gateway_provider VARCHAR(50) NOT NULL DEFAULT 'mercadopago',
    transaction_id VARCHAR(100),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    amount NUMERIC(10, 2) NOT NULL,
    installments INT NOT NULL DEFAULT 1,
    card_last_four VARCHAR(4),
    card_brand VARCHAR(50),
    raw_response JSON,
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payments_booking FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_payments_booking ON payments(booking_id);
CREATE INDEX IF NOT EXISTS idx_payments_transaction ON payments(transaction_id);

-- ------------------------------------------------------------------------------
-- 19. TABELA DE SOLICITAÇÕES DE CONSULTORIA & CONTATO (Multi-Step Form)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contact_inquiries (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    destination VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    number_of_adults INT NOT NULL DEFAULT 1,
    number_of_children INT DEFAULT 0,
    travel_type VARCHAR(100) NOT NULL,
    accommodation_preference VARCHAR(100) NOT NULL,
    room_type VARCHAR(100) NOT NULL,
    meal_plan VARCHAR(100) NOT NULL,
    transportation VARCHAR(100) NOT NULL,
    internal_transportation VARCHAR(100) NOT NULL,
    estimated_budget NUMERIC(10, 2) NOT NULL,
    dietary_restrictions TEXT,
    other_special_needs TEXT,
    additional_info TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'novo',
    admin_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inquiries_email ON contact_inquiries(email);
CREATE INDEX IF NOT EXISTS idx_inquiries_status ON contact_inquiries(status);

-- ------------------------------------------------------------------------------
-- 20. TABELA DE CONFIGURAÇÕES GERAIS DA AGÊNCIA (CMS & Integrações)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agency_settings (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'default',
    company_name VARCHAR(255) NOT NULL DEFAULT 'Zarpou Viagens e Turismo Ltda',
    trading_name VARCHAR(255) NOT NULL DEFAULT 'Zarpou Viagens',
    cnpj VARCHAR(30) NOT NULL DEFAULT '55.849.201/0001-38',
    cadastur VARCHAR(30) NOT NULL DEFAULT '34.120.948/0001-90',
    whatsapp VARCHAR(30) NOT NULL DEFAULT '5531984210000',
    whatsapp_message TEXT DEFAULT 'Olá! Gostaria de falar com um especialista da Zarpou Viagens.',
    email VARCHAR(255) NOT NULL DEFAULT 'contato@zarpou.com.br',
    phone VARCHAR(30) NOT NULL DEFAULT '(31) 3344-5500',
    instagram VARCHAR(255) DEFAULT 'https://instagram.com/zarpouviagens',
    linkedin VARCHAR(255) DEFAULT 'https://linkedin.com/company/zarpouviagens',
    address TEXT DEFAULT 'Av. do Contorno, 6500 - Savassi, Belo Horizonte - MG, 30110-044',
    terms_and_conditions TEXT,
    privacy_policy TEXT,
    resend_api_key VARCHAR(255),
    whatsapp_api_provider VARCHAR(50) NOT NULL DEFAULT 'meta_cloud',
    whatsapp_api_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    whatsapp_api_token TEXT,
    whatsapp_phone_number_id VARCHAR(100),
    whatsapp_business_account_id VARCHAR(100),
    whatsapp_api_url VARCHAR(255) DEFAULT 'https://graph.facebook.com/v19.0',
    payment_gateway_provider VARCHAR(50) NOT NULL DEFAULT 'mercadopago',
    payment_environment VARCHAR(20) NOT NULL DEFAULT 'sandbox',
    payment_public_key TEXT,
    payment_secret_key TEXT,
    payment_pix_key VARCHAR(100),
    payment_webhook_secret TEXT,
    payment_active_credit_card BOOLEAN NOT NULL DEFAULT TRUE,
    payment_active_pix BOOLEAN NOT NULL DEFAULT TRUE,
    payment_active_boleto BOOLEAN NOT NULL DEFAULT TRUE,
    ai_chat_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    ai_chat_provider VARCHAR(50) NOT NULL DEFAULT 'openai',
    ai_chat_api_key TEXT,
    ai_chat_model VARCHAR(100) DEFAULT 'gpt-4o-mini',
    ai_chat_system_prompt TEXT DEFAULT 'Você é o Concierge Virtual da Zarpou Viagens e Turismo. Atenda com calor humano, sofisticação e objetividade.',
    ai_chat_welcome_message TEXT DEFAULT 'Olá! Sou o Concierge Virtual da Zarpou Viagens. Como posso ajudar com sua próxima viagem hoje?',
    storage_provider VARCHAR(50) NOT NULL DEFAULT 'aws_s3',
    storage_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    storage_bucket_name VARCHAR(255) DEFAULT '',
    storage_region VARCHAR(100) DEFAULT 'sa-east-1',
    storage_access_key_id TEXT,
    storage_secret_access_key TEXT,
    storage_endpoint_url TEXT,
    storage_public_url_prefix TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------------------------
-- 21. TABELA DE HISTÓRICO DE MENSAGENS DO CONCIERGE VIRTUAL (AI Chat Logs)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_logs (
    id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(36),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chat_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_logs(session_id);


-- ==============================================================================
-- CARGA INICIAL DE DADOS (SEEDS DO FRONTEND ZARPOU)
-- ==============================================================================

-- 1. Usuários Administradores & Equipe (senha: admin123)
INSERT INTO users (id, name, email, password_hash, role, allowed_screens, is_active)
VALUES 
(
    'adm-1',
    'Administrador Zarpou',
    'admin@zarpou.com.br',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'admin',
    '["dashboard","hero","promocoes","hospedagens","passagens","destinos","reservas","usuarios","administradores","configuracoes"]',
    TRUE
),
(
    'adm-2',
    'Juliana Costa',
    'juliana.costa@zarpou.com.br',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'personalizado',
    '["dashboard","hero","promocoes","hospedagens","passagens","destinos","reservas"]',
    TRUE
),
(
    'adm-3',
    'Rodrigo Silveira',
    'rodrigo.silveira@zarpou.com.br',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'personalizado',
    '["dashboard","reservas","usuarios"]',
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- 2. Empresa Conveniada de Demonstração (Zarpou Empresas)
INSERT INTO companies (
    id, cnpj, razao_social, nome_fantasia, corporate_email, phone, manager_name, manager_cpf, password_hash, status, corporate_discount_percent, credit_limit, credit_used, payment_terms
) VALUES (
    'comp-inova',
    '12.345.678/0001-90',
    'Inovação e Tecnologia Brasil S/A',
    'InovaTech',
    'viagens@inovatech.com.br',
    '(11) 3210-9000',
    'Renato Fonseca',
    '111.222.333-44',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- senha: admin123
    'aprovada',
    10.00,
    30000.00,
    0.00,
    'faturado_30d'
) ON CONFLICT (cnpj) DO NOTHING;

-- 3. Colaborador Corporativo de Exemplo
INSERT INTO company_employees (
    id, company_id, full_name, cpf, email, phone, cost_center, department, is_active
) VALUES (
    'emp-inova-1',
    'comp-inova',
    'Carlos Eduardo Mendes',
    '123.456.789-10',
    'carlos@inovatech.com.br',
    '(11) 98765-4321',
    'Tecnologia & Inovação',
    'Engenharia de Software',
    TRUE
) ON CONFLICT (id) DO NOTHING;

-- 4. Configuração Padrão da Agência
INSERT INTO agency_settings (
    id, company_name, trading_name, cnpj, cadastur, whatsapp, email, phone, address,
    storage_provider, storage_enabled, storage_bucket_name, storage_region
) VALUES (
    'default',
    'Zarpou Viagens e Turismo Ltda',
    'Zarpou Viagens',
    '55.849.201/0001-38',
    '34.120.948/0001-90',
    '5531984210000',
    'contato@zarpou.com.br',
    '(31) 3344-5500',
    'Av. do Contorno, 6500 - Savassi, Belo Horizonte - MG, 30110-044',
    'aws_s3',
    TRUE,
    '',
    'sa-east-1'
) ON CONFLICT (id) DO NOTHING;

-- 5. Destinos em Destaque
INSERT INTO destinations (id, title, country, flag, category, tag, description, starting_price, accommodations_count, link, image_url, display_order)
VALUES
('dest-dubai', 'Dubai', 'Emirados Árabes', '🇦🇪', 'international', 'Luxo & Futurismo', 'Arranha-céus icônicos, safáris no deserto, ilhas artificiais e o auge da sofisticação mundial.', 1650.00, 140, '/hospedagens?city=Dubai', 'https://images.pexels.com/photos/3769312/pexels-photo-3769312.jpeg', 1),
('dest-buzios', 'Armação dos Búzios', 'Brasil', '🇧🇷', 'national', 'Praias Paradisíacas', 'Mais de 20 praias de águas cristalinas, alta gastronomia na Rua das Pedras e pousadas de charme.', 520.00, 95, '/hospedagens?city=Armação%20dos%20Búzios', 'https://images.pexels.com/photos/12039523/pexels-photo-12039523.jpeg', 2),
('dest-santiago', 'Santiago', 'Chile', '🇨🇱', 'international', 'Andes & Vinhedos', 'A imponência da Cordilheira dos Andes, vinícolas renomadas mundialmente e rica herança cultural.', 720.00, 115, '/hospedagens?city=Santiago', 'https://images.pexels.com/photos/2017747/pexels-photo-2017747.jpeg', 3),
('dest-rio', 'Rio de Janeiro', 'Brasil', '🇧🇷', 'national', 'Cidade Maravilhosa', 'Copacabana, Ipanema, Cristo Redentor e uma atmosfera vibrante que encanta viajantes de todo o planeta.', 850.00, 260, '/hospedagens?city=Rio%20de%20Janeiro', 'https://images.pexels.com/photos/720300/pexels-photo-720300.jpeg', 4)
ON CONFLICT (id) DO NOTHING;

-- 6. Adicionais de Reserva (Addons)
INSERT INTO addons (id, title, description, price, category, is_active)
VALUES
('addon-insurance', 'Seguro Viagem Zarpou Proteção Total', 'Cobertura médica hospitalar de até R$ 150.000, extravio de bagagem e cancelamento involuntário.', 68.00, 'seguro', TRUE),
('addon-baggage', 'Bagagem Despachada Extra 23kg', 'Garanta espaço extra para suas compras e lembranças de viagem com tarifa promocional.', 110.00, 'bagagem', TRUE),
('addon-transfer', 'Transfer Executivo Aeroporto / Hotel', 'Recepção privativa com motorista credenciado e veículo climatizado na chegada e partida.', 140.00, 'traslado', TRUE)
ON CONFLICT (id) DO NOTHING;

-- 7. Promoções Ativas
INSERT INTO promotions (id, title, subtitle, badge, discount_text, image_url, link, button_text, active, display_order)
VALUES
('promo-1', 'Temporada Nordeste dos Sonhos', 'Resorts pé na areia em Porto Seguro, Maceió e Natal com condições exclusivas.', 'OFERTA RELÂMPAGO', 'Até 35% OFF', 'https://images.pexels.com/photos/12039523/pexels-photo-12039523.jpeg', '/hospedagens?city=Búzios', 'Aproveitar Oferta', TRUE, 1),
('promo-2', 'Viva a Magia do Rio de Janeiro', 'Hotéis selecionados com vista para o mar e cancelamento grátis em até 12x sem juros.', 'MAIS BUSCADO', 'Em até 12x s/ juros', 'https://images.pexels.com/photos/720300/pexels-photo-720300.jpeg', '/hospedagens?city=Rio%20de%20Janeiro', 'Ver Hotéis no Rio', TRUE, 2),
('promo-3', 'Passagens Internacionais com Preço Especial', 'Miami, Santiago, Roma e Madri com saídas de Belo Horizonte e São Paulo.', 'INTERNACIONAL', 'A partir de R$ 1.890', 'https://images.pexels.com/photos/3834331/pexels-photo-3834331.jpeg', '/passagens?to=MIA', 'Buscar Passagens', TRUE, 3)
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 8. TABELA DE REVOGAÇÃO DE TOKENS (Blacklist / Logout Imediato - OWASP A07)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS revoked_tokens (
    jti VARCHAR(64) PRIMARY KEY,
    subject VARCHAR(100),
    token_type VARCHAR(20) NOT NULL DEFAULT 'access',
    revoked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires_at ON revoked_tokens(expires_at);

