# 1. Imagem base oficial do Python optimizada (slim)
FROM python:3.11-slim

# 2. Define o diretório de trabalho dentro do container
WORKDIR /app

# 3. Evita que o Python escreva arquivos .pyc e garante logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. Copia apenas o arquivo de dependências primeiro (otimização de cache do Docker)
COPY requirements.txt /app/

# 5. Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copia o restante do código do backend para o container
COPY . /app/

# 7. Expõe a porta que o FastAPI vai rodar
EXPOSE 8085

# 8. Comando para iniciar a API (host 0.0.0.0 é obrigatório para aceitar conexões externas ao container)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8085"]