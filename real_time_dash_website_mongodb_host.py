import streamlit as st
import pandas as pd
import numpy as np
import datetime
from pymongo import MongoClient
import plotly.graph_objs as go
from streamlit_autorefresh import st_autorefresh
import requests
import os
from pymongo import MongoClient

def get_mongo_collection():
    connection_string = os.getenv("MONGO_CONNECTION_STRING")
    client = MongoClient(connection_string)
    db = client["real_time_data"]
    collection = db["generated_data"]
    return collection

# Coinbase API Endpoint
COINBASE_URL = "https://api.coinbase.com/v2/exchange-rates"

# Maksymalna liczba punktów na wykresie
MAX_POINTS = 20

# Funkcja do generowania losowych danych
def generate_random_data():
    current_time = datetime.datetime.now()
    return pd.DataFrame({
        'Time': [current_time],
        'Value': [round(np.random.uniform(0, 100), 2)]
    })

# Funkcja do zapisywania danych do MongoDB
def save_data_to_mongo(data):
    collection = get_mongo_collection()
    records = data.to_dict("records")  # Konwersja DataFrame na listę słowników
    collection.insert_many(records)

# Funkcja do pobierania danych z MongoDB
def fetch_data_from_mongo():
    collection = get_mongo_collection()
    data = pd.DataFrame(list(collection.find()))
    if "_id" in data.columns:
        data.drop("_id", axis=1, inplace=True)  # Usunięcie pola `_id`
    return data

# Funkcja do pobierania ceny Bitcoina w euro
def get_bitcoin_price_in_euro():
    params = {"currency": "BTC"}
    response = requests.get(COINBASE_URL, params=params)
    data = response.json()
    return float(data["data"]["rates"].get("EUR", None))  # Zwraca cenę w EUR lub None, jeśli brak danych

# Funkcja do inicjalizacji danych
def initialize_session_state():
    if "data_generated" not in st.session_state:
        st.session_state["data_generated"] = pd.DataFrame(columns=['Time', 'Value'])
    if "data_stock" not in st.session_state:
        st.session_state["data_stock"] = pd.DataFrame(columns=['Time', 'Value'])

# Inicjalizacja danych
initialize_session_state()

st.title("Real-Time Data Dashboard")

# Sekcja: Generated Data
generated_container = st.container()
with generated_container:
    st.header("Generated Data")

    # Generowanie nowych danych
    new_generated_row = generate_random_data()
    st.session_state["data_generated"] = pd.concat(
        [st.session_state["data_generated"], new_generated_row],
        ignore_index=True
    )

    # Utrzymanie ograniczonej liczby punktów
    if len(st.session_state["data_generated"]) > MAX_POINTS:
        st.session_state["data_generated"] = st.session_state["data_generated"].tail(MAX_POINTS)

    # Zapis nowych danych do bazy
    save_data_to_mongo(new_generated_row)

    # Rysowanie wykresu
    fig_generated = go.Figure()
    fig_generated.add_trace(go.Scatter(
        x=st.session_state["data_generated"]['Time'],
        y=st.session_state["data_generated"]['Value'],
        mode='lines+markers',
        name='Generated Data'
    ))
    fig_generated.update_layout(
        title="Generated Data Visualization",
        xaxis_title="Time",
        yaxis_title="Value"
    )
    st.plotly_chart(fig_generated)

# Sekcja: Database Data
database_container = st.container()
with database_container:
    st.header("Database Data")

    data_db = fetch_data_from_mongo()
    if len(data_db) > MAX_POINTS:
        data_db = data_db.tail(MAX_POINTS)

    fig_db = go.Figure()
    fig_db.add_trace(go.Scatter(
        x=data_db['Time'],
        y=data_db['Value'],
        mode='lines+markers',
        name='Database Data'
    ))
    fig_db.update_layout(
        title="Database Data Visualization",
        xaxis_title="Time",
        yaxis_title="Value"
    )
    st.plotly_chart(fig_db)

# Sekcja: Bitcoin Price Data
stock_container = st.container()
with stock_container:
    st.header("Bitcoin Price in EUR (API)")

    current_time = datetime.datetime.now()
    price_in_euro = get_bitcoin_price_in_euro()

    # Jeśli brak danych z API, bierzemy ostatnią dostępną wartość
    if price_in_euro == 0 and len(st.session_state["data_stock"]) > 0:
        price_in_euro = st.session_state["data_stock"]["Value"].iloc[-1]

    # Dodajemy nowy rekord z kursem
    new_stock_row = pd.DataFrame({
        'Time': [current_time],
        'Value': [price_in_euro]
    })
    st.session_state["data_stock"] = pd.concat(
        [st.session_state["data_stock"], new_stock_row],
        ignore_index=True
    )

    # Utrzymanie ograniczonej liczby punktów
    if len(st.session_state["data_stock"]) > MAX_POINTS:
        st.session_state["data_stock"] = st.session_state["data_stock"].tail(MAX_POINTS)

    # Rysowanie wykresu
    fig_stock = go.Figure()
    fig_stock.add_trace(go.Scatter(
        x=st.session_state["data_stock"]['Time'],
        y=st.session_state["data_stock"]['Value'],
        mode='lines+markers',
        name='Bitcoin Price'
    ))
    fig_stock.update_layout(
        title="Bitcoin Price Visualization",
        xaxis_title="Time",
        yaxis_title="Price (EUR)"
    )
    st.plotly_chart(fig_stock)

# Automatyczne odświeżanie w tle
st_autorefresh(interval=1000, limit=None, key="data_refresh")
