# 🌌 AstroAPI

Backend application developed in **Python** with **FastAPI**, designed to solve challenges related to **space data** as part of the **NASA Space Apps Challenge**.

## 🛰️ Description

**AstroAPI** is a backend application built with the **FastAPI** framework to create a robust and efficient REST API.
Its goal is to process, analyze, and provide access to **space-related data** in a scalable and user-friendly way.
This project was developed for the **NASA Space Apps Challenge**, promoting **innovative solutions** for problems related to **space and Earth observation**.

---

## 🧩 Python Installation

Make sure **Python 3.12** is installed on your system.
To install it, run:

```bash
sudo apt install python3.12
```

---

## 🧱 Virtual Environment Setup

Inside the project folder, create and activate a virtual environment:

```bash
python3.12 -m venv venv
source venv/bin/activate
```

---

## 📦 Installing Dependencies

With the virtual environment activated, install the project dependencies:

```bash
pip install -r requirements.txt
```

---

## 🚀 Running the Application

To start the **FastAPI** server, run:

```bash
uvicorn main:app --reload
```

Then access the interactive API documentation at:

* **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🐳 Using Docker

### 1. Build the Docker Image

Ensure that **Docker** is installed on your system.
To build the image, run from the project root:

```bash
docker build -t astroapi .
```

### 2. Run the Container

After building the image, run the container:

```bash
docker run -p 8000:8000 astroapi
```

The application will be available at
👉 [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## ⚙️ Using Docker Compose

### 1. Start the Services

If you have a [`docker-compose.yml`](docker-compose.yml) file configured, start all services (application and database) with:

```bash
docker-compose up --build
```

### 2. Access the Application

Once started, the API will be available at
👉 [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🧪 Testing

To run the project tests, use:

```bash
pytest
```
---

**Developed for the NASA Space Apps Challenge 2024 — Team AstroAPI 🚀**
