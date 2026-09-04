# Alpaca AI Hackathon - Local Setup Guide for Judges

Welcome to our project for the Alpaca AI Hackathon! Due to the heavy processing and memory requirements of our multi-agent AI architecture, the backend exceeds the limits of standard free-tier cloud platforms. 

To evaluate our project, please run it locally on your machine following the steps below.

## Prerequisites
1. Python 3.9+
2. Node.js (for the frontend UI)
3. API Keys for Alpaca and Serper

## 1. Environment Setup

First, clone the repository to your local machine. In the root directory, create a `.env` file by copying the provided `.env.example`:

```bash
cp .env.example .env
```

Open the `.env` file and insert your credentials:

- `ALPACA_API_KEY`: Your Alpaca Paper Trading API Key
- `ALPACA_SECRET_KEY`: Your Alpaca Paper Trading Secret Key
- `SERPER_API_KEY`: Your Serper (Google Search API) Key
- `FEATHERLESS_API_KEY`: (Optional) Your Featherless API Key if evaluating LLM generation alternatives.

## 2. Install Dependencies

Install the required Python backend dependencies:
```bash
pip install -r requirements.txt
```

Install the frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

## 3. Run the Application

We have created a single orchestration script to start both the Python AI Backend and the Next.js Frontend simultaneously. 

From the root directory, simply run:
```bash
python start_server.py
```

- The **Python Backend** will launch on `http://localhost:8000`
- The **Next.js Frontend** will automatically build and launch on `http://localhost:3000`

## 4. View the App

Open your browser and navigate to:
👉 **http://localhost:3000/dashboard**

The frontend is pre-configured to communicate with the local backend automatically. You do not need to use ngrok, Vercel, or set up any external network tunnels to test the core features of this application.

Enjoy testing the terminal!
