# Use a imagem base do Python 3.11.4
FROM python:3.11.4

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo requirements.txt para o diretório de trabalho
COPY requirements.txt .

# Instala as dependências listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código-fonte para o diretório de trabalho
COPY . .

# Define o comando padrão para iniciar o servidor
CMD ["uvicorn", "workout_api.main:app", "--reload"]
