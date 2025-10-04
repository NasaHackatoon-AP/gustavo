# AstroAPI
Aplicação backend desenvolvida em Python com FastAPI para resolver desafios relacionados a dados espaciais, como parte do projeto Nasa Space Apps.

## Descrição
AstroAPI é uma aplicação que utiliza a framework FastAPI para criar uma API robusta e eficiente. O objetivo é processar, analisar e disponibilizar dados espaciais de forma acessível e escalável. Este projeto faz parte do desafio Nasa Space Apps, promovendo soluções inovadoras para problemas relacionados ao espaço.


## Instalação do Python
Certifique-se de ter o Python 3.12 instalado no seu sistema. Para instalar, execute o comando abaixo:

```bash
sudo apt install python3.12
```

## Criação do ambiente virtual

Dentro da pasta do projeto, configure o ambiente virtual com os seguintes comandos:

```bash
python3.12 -m venv venv
source venv/bin/activate
```

## Instalação das Dependências
Com o ambiente virtual ativado, instale as dependências do projeto:

```bash
pip install -r requirements.txt
```

## Executando a Aplicação

Para iniciar o servidor FastAPI, execute o seguinte comando:

```bash
uvicorn main:app --reload
```
Acesse a documentação interativa da API em:

Swagger UI: http://127.0.0.1:8000/docs
ReDoc: http://127.0.0.1:8000/redoc


## Usando Docker

### 1. Construindo a Imagem Docker
Certifique-se de que o Docker está instalado no seu sistema. Para construir a imagem Docker, execute o seguinte comando na raiz do projeto:

```bash
docker build -t astroapi .
```

### 2. Executando o Container
Após construir a imagem, execute o container com o comando:

```bash
docker run -p 8000:8000 astroapi
```

A aplicação estará disponível em [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Usando Docker Compose

### 1. Subindo os Serviços
Se você configurou o arquivo [`docker-compose.yml`](), pode subir os serviços (aplicação e banco de dados) com o comando:

```bash
docker-compose up --build
```

### 2. Acessando a Aplicação
A aplicação estará disponível em [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Testes
Para rodar os testes do projeto, utilize o comando:

```bash
pytest
```







