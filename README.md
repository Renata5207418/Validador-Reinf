# Validador de Eventos EFD-Reinf

Este projeto contém validadores em Python para os eventos **R2010**, **R4010** e **R4020** da EFD-Reinf, permitindo:

- Checar campos obrigatórios e formatos de identificação (CNPJ/CNO/CPF);  
- Aplicar lógica de bases e retenções;  
- Verificar tabelas de natureza de rendimentos;  
- Persistir somente os eventos 100 % válidos no MongoDB, cada um em sua coleção e com `_id` composto.

---

## ⚙️ Pré-requisitos

- Python 3.10+  
- pipenv (ou `venv` + `pip`)  
- MongoDB rodando em `mongodb://localhost:27017/` (ou ajuste `MONGO_URI`)  
- Windows, macOS ou Linux  

---

## 🚀 Instalação

1.Clone o repositório e entre na pasta:
   ```bash
   git clone https://seu-repositorio.git
   cd Validador_eventos
   ```

2.Crie e ative o ambiente virtual:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3.Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

---

## 📁 Estrutura do Projeto

```
Validador_eventos/
│
├── dicionarios/
│   ├── tp_servico.py       # Códigos de tipo de serviço (R2010)
│   ├── nat_rend_pf.py      # Natureza de rendimentos PF (R4010)
│   └── nat_rend_pj.py      # Natureza de rendimentos PJ (R4020)
│
├── utils/
│   └── validadores_em_comum.py   # Validações genéricas (CNPJ/CNO/CPF)
│
├── eventos/
│   ├── validador_2010.py       # Pydantic model e validações R2010
│   ├── validador_4010.py       # Pydantic model e validações R4010
│   └── validador_4020.py       # Pydantic model e validações R4020
│
├── database.py             # Conexão ao MongoDB e lógica de _id/data-driven
├── main.py                 # FastAPI + endpoint `/validar` + integração DB
├── requirements.txt        # Dependências
└── README.md               # Este arquivo
```

---

## 📝 Como Usar

### 1. Validar localmente cada evento

Cada arquivo `validador_XXXX.py` possui um exemplo no final que você pode executar diretamente:

```bash
python eventos/validador_2010.py
python eventos/validador_4010.py
python eventos/validador_4020.py
```

Eles imprimem o resultado do `model.dump()` em caso de sucesso ou lançam erro em caso de falha.

### 2. Rodar a API

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- **GET** `/health` → `{ "status": "ok" }`  
- **POST** `/validar`  
  - Envie JSON com `"TpEvento"` (`"R2010"`, `"R4010"` ou `"R4020"`) e demais campos;  
  - Recebe `{ "evento": "...", "status": "valido", "mensagem": "..." }` ou erro 4xx/422;  
  - Eventos validados são inseridos no MongoDB, cada um em sua coleção (`R2010`, `R4010`, `R4020`) com `_id` customizado.

---

## 🔗 database.py & _id data-driven

Em `database.py` há um dicionário único que você mantém para cada evento:

```python
EVENT_CONFIG = {
    "R2010": {
        "id_field":      "numDocto",
        "pessoa_fields": ["cnpjPrestador"],
    },
    "R4010": {
        "id_field":      "NumDoc",
        "pessoa_fields": ["cpfBenef", "cnpjBenef"],
    },
    "R4020": {
        "id_field":      "NumDoc",
        "pessoa_fields": ["cpfBenef", "cnpjBenef"],
    },
    # → para futuros eventos, basta:
    # "RXXXX": {"id_field": "campoNum", "pessoa_fields": ["campoA","campoB"]},
}
```

A função `build_id(payload)` faz:

1. Lê `payload["TpEvento"]` e busca `cfg = EVENT_CONFIG[tipo]`.  
2. Lê o valor de `payload[cfg["id_field"]]` → **número do documento**.  
3. Usa `payload["nrInscEstab"]` → **CNPJ principal**.  
4. Varre `cfg["pessoa_fields"]` e usa o primeiro campo presente no payload → **CNPJ/CPF**.  
5. Faz lookup do **cliente (escritório)** via `CLIENTS_MAP[nrInscEstab]`.  
6. Retorna `_id = "<numdoc>-<cgc>-<pessoa>-<cliente>"`.  

Dessa forma, para cada novo evento basta adicionar uma entrada em `EVENT_CONFIG` — **nunca** alterar a lógica de `build_id`.

---

## 📦 Pacotes e Funções Principais

- **`dicionarios/*`**: constantes e tabelas de referência.  
- **`utils/validadores_em_comum.py`**:  
  - `validar_cnpj(cnpj: str)`, `validar_cno(cno: str)`, `validar_cpf(cpf: str)`;  
  - `limpar_numeros(s: str) -> str`.  
- **`eventos/validador_XXXX.py`**: modelos Pydantic com `field_validator` e `model_validator`.  
- **`database.py`**: conexão ao MongoDB, `EVENT_CONFIG`, `build_id()` e `save_if_valid()`.  
- **`main.py`**: FastAPI → endpoint `/validar` → chama `validador`, depois `save_if_valid()`.

---

## ✔️ Boas Práticas

- Mantenha **constantes** em `dicionarios/`, sem lógica.  
- Coloque **validações genéricas** em `utils/`.  
- Use **model validators** para interdependências de campos.  
- Deixe **EVENT_CONFIG** e `CLIENTS_MAP` como único ponto de ajuste para novo evento ou escritório.

---

## 🧪 Testes

1. Instale o pytest:
   ```bash
   pip install pytest
   ```
2. Crie `tests/` com casos válidos e inválidos dos eventos.  
3. Execute:
   ```bash
   pytest --maxfail=1 --disable-warnings -q
   ```