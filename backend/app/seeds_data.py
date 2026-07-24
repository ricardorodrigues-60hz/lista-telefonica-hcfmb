"""Dados de inicialização (seeds / mock data) do banco de dados do HCFMB.

Armazena as contas padrão de desenvolvimento e os registros iniciais de contatos.
"""

# Contas padrão de desenvolvimento.
# ATENÇÃO: desative essas senhas antes de qualquer deploy em produção.
CONTAS_SEED = [
    {
        'nome': 'Gestor HCFMB',
        'email': 'gestor@hcfmb.unesp.br',
        'senha': 'gestor123',
        'papel': 'GESTOR',
    },
    {
        'nome': 'Consultor HCFMB',
        'email': 'consultor@hcfmb.unesp.br',
        'senha': 'consultor123',
        'papel': 'CONSULTOR',
    },
]

# Registros mock data de contatos do Hospital das Clínicas de Botucatu (HCFMB)
CONTATOS_MOCK = [
    {
        'nome': 'Portaria Principal',
        'telefone': '(14) 3811-1500',
        'email': 'portaria@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'PABX / Central Telefônica',
        'telefone': '(14) 3811-1000',
        'email': 'pabx@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'Pronto Socorro Adulto - Recepção',
        'telefone': '(14) 3811-1600',
        'email': 'ps.adulto@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'Pronto Socorro Infantil - Recepção',
        'telefone': '(14) 3811-1610',
        'email': 'ps.infantil@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'UTI Adulto I - Enfermagem',
        'telefone': '(14) 3811-1801',
        'email': 'uti.adulto1@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'UTI Adulto II - Enfermagem',
        'telefone': '(14) 3811-1802',
        'email': 'uti.adulto2@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'UTI Neonatal e Pediátrica',
        'telefone': '(14) 3811-1810',
        'email': 'uti.neo@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Central de Agendamento de Consultas',
        'telefone': '(14) 3811-1700',
        'email': 'agendamento@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'Ambulatório de Especialidades',
        'telefone': '(14) 3811-1710',
        'email': 'ambulatorio@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'Hemocentro / Banco de Sangue',
        'telefone': '(14) 3811-1900',
        'email': 'hemocentro@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'Laboratório de Análises Clínicas',
        'telefone': '(14) 3811-2000',
        'email': 'laboratorio@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Serviço de Radiologia e Tomografia',
        'telefone': '(14) 3811-2100',
        'email': 'radiologia@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Farmácia Central HCFMB',
        'telefone': '(14) 3811-2200',
        'email': 'farmacia.central@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Farmácia Ambulatorial (Alto Custo)',
        'telefone': '(14) 3811-2210',
        'email': 'farmacia.altocusto@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'Serviço de Nutrição e Dietética',
        'telefone': '(14) 3811-2300',
        'email': 'nutricao@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Serviço Social - Atendimento',
        'telefone': '(14) 3811-2400',
        'email': 'servicosocial@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'Ouvidoria HCFMB',
        'telefone': '(14) 3811-2500',
        'email': 'ouvidoria@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'Gestão de Recursos Humanos (RH)',
        'telefone': '(14) 3811-2600',
        'email': 'rh@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Tecnologia da Informação (TI)',
        'telefone': '(14) 3811-2700',
        'email': 'ti@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Engenharia Clínica e Manutenção',
        'telefone': '(14) 3811-2800',
        'email': 'manutencao@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Centro Cirúrgico - Secretária',
        'telefone': '(14) 3811-2900',
        'email': 'centrocirurgico@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Central de Material e Esterilização (CME)',
        'telefone': '(14) 3811-2950',
        'email': 'cme@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Maternidade e Sala de Parto',
        'telefone': '(14) 3811-3000',
        'email': 'maternidade@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Controle de Infecção Hospitalar (CCIH)',
        'telefone': '(14) 3811-3100',
        'email': 'ccih@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Ambulatório de Oncologia / Quimioterapia',
        'telefone': '(14) 3811-3200',
        'email': 'oncologia@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'Hemodinâmica e Cardiologia',
        'telefone': '(14) 3811-3300',
        'email': 'hemodinamica@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Fisioterapia e Reabilitação',
        'telefone': '(14) 3811-3400',
        'email': 'fisioterapia@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'Medicina do Trabalho / SESMT',
        'telefone': '(14) 3811-3500',
        'email': 'sesmt@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Diretoria Clínica HCFMB',
        'telefone': '(14) 3811-3600',
        'email': 'dir.clinica@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Superintendência HCFMB',
        'telefone': '(14) 3811-3700',
        'email': 'superintendencia@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Assessoria de Comunicação / Imprensa',
        'telefone': '(14) 3811-3800',
        'email': 'comunicacao@hcfmb.unesp.br',
        'tipo_numero': 'publico',
    },
    {
        'nome': 'Arquivo Médico e Prontuários (SAME)',
        'telefone': '(14) 3811-3900',
        'email': 'same@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Serviço de Transporte e Ambulâncias',
        'telefone': '(14) 3811-4000',
        'email': 'transporte@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Necratério e Anatomia Patológica',
        'telefone': '(14) 3811-4100',
        'email': 'patologia@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
    {
        'nome': 'Almoxarifado Central',
        'telefone': '(14) 3811-4200',
        'email': 'almoxarifado@hcfmb.unesp.br',
        'tipo_numero': 'institucional',
    },
]
