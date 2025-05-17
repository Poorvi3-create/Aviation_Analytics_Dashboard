import pandas as pd
import sqlite3
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Flight Data Dashboard")
st.title("Aviation Analytics Dashboard")

DATA_PATH = r'data.csv'
df_raw = pd.read_csv(DATA_PATH)

conn = sqlite3.connect(':memory:')
df_raw.to_sql('flights', conn, if_exists='replace', index=False)

query_cleaned = """
SELECT *,
       CAST(REPLACE([Flight Price], ',', '') AS FLOAT) AS Price_Float,
       CASE 
           WHEN [Duration Time] LIKE '%h %m' THEN 
               CAST(SUBSTR([Duration Time], 1, INSTR([Duration Time], 'h') - 1) AS INT) * 60 +
               CAST(SUBSTR([Duration Time], INSTR([Duration Time], 'h') + 2, LENGTH([Duration Time])) AS INT)
           WHEN [Duration Time] LIKE '%h' THEN 
               CAST(SUBSTR([Duration Time], 1, INSTR([Duration Time], 'h') - 1) AS INT) * 60
           ELSE 
               CAST(REPLACE([Duration Time], 'm', '') AS INT)
       END AS Duration_Minutes,
       DATE(SUBSTR([Date], 7, 4) || '-' || SUBSTR([Date], 4, 2) || '-' || SUBSTR([Date], 1, 2)) AS Travel_Date,
       SUBSTR([Departure Time], 1, 2) AS Departure_Hour
FROM flights
"""
df_cleaned = pd.read_sql_query(query_cleaned, conn)

st.sidebar.header("Filter Options")

all_airlines = sorted(df_cleaned['Company'].dropna().unique())
selected_airlines = st.sidebar.multiselect("Select Airline(s)", all_airlines, default=all_airlines)

all_classes = sorted(df_cleaned['Cabin Class'].dropna().unique())
if len(all_classes) > 1:
    selected_classes = st.sidebar.multiselect("Select Cabin Class(es)", all_classes, default=all_classes)
else:
    st.sidebar.info(f"Only one cabin class available: {all_classes[0]}")
    selected_classes = all_classes

all_origins = sorted(df_cleaned['Origin'].dropna().unique())
selected_origins = st.sidebar.multiselect("Select Origin Airport(s)", all_origins, default=all_origins)

all_destinations = sorted(df_cleaned['Destination'].dropna().unique())
selected_destinations = st.sidebar.multiselect("Select Destination Airport(s)", all_destinations, default=all_destinations)

min_hour = int(df_cleaned['Departure_Hour'].min())
max_hour = int(df_cleaned['Departure_Hour'].max())
departure_hour_range = st.sidebar.slider("Departure Hour Range", min_value=0, max_value=23, value=(min_hour, max_hour))

min_price = int(df_cleaned['Price_Float'].min())
max_price = int(df_cleaned['Price_Float'].max())
price_range = st.sidebar.slider("Price Range", min_value=min_price, max_value=max_price, value=(min_price, max_price))

min_duration = int(df_cleaned['Duration_Minutes'].min())
max_duration = int(df_cleaned['Duration_Minutes'].max())
duration_range = st.sidebar.slider("Flight Duration (minutes)", min_value=min_duration, max_value=max_duration, value=(min_duration, max_duration))

df_filtered = df_cleaned[
    (df_cleaned['Company'].isin(selected_airlines)) &
    (df_cleaned['Cabin Class'].isin(selected_classes)) &
    (df_cleaned['Origin'].isin(selected_origins)) &
    (df_cleaned['Destination'].isin(selected_destinations)) &
    (df_cleaned['Departure_Hour'].astype(int) >= departure_hour_range[0]) &
    (df_cleaned['Departure_Hour'].astype(int) <= departure_hour_range[1]) &
    (df_cleaned['Price_Float'] >= price_range[0]) &
    (df_cleaned['Price_Float'] <= price_range[1]) &
    (df_cleaned['Duration_Minutes'] >= duration_range[0]) &
    (df_cleaned['Duration_Minutes'] <= duration_range[1])
]

df_filtered.to_sql('flights_clean_filtered', conn, if_exists='replace', index=False)

unique_airlines = sorted(df_filtered['Company'].unique())
color_palette = px.colors.qualitative.Plotly
airline_color_map = {airline: color_palette[i % len(color_palette)] for i, airline in enumerate(unique_airlines)}

queries = {
    "Average Price per Airline": """
        SELECT Company, ROUND(AVG(Price_Float), 2) AS Average_Price
        FROM flights_clean_filtered
        GROUP BY Company
        ORDER BY Average_Price DESC
    """,
    "Flight Count per Route": """
        SELECT Origin || ' → ' || Destination AS Route, COUNT(*) AS Total_Flights
        FROM flights_clean_filtered
        GROUP BY Route
        ORDER BY Total_Flights DESC
    """,
    "Average Duration per Route": """
        SELECT Origin || ' → ' || Destination AS Route, ROUND(AVG(Duration_Minutes), 2) AS Avg_Duration_Min
        FROM flights_clean_filtered
        GROUP BY Route
        ORDER BY Avg_Duration_Min DESC
    """,
    "Cabin Class Share": """
        SELECT [Cabin Class], COUNT(*) AS Count
        FROM flights_clean_filtered
        GROUP BY [Cabin Class]
    """,
    "Flights per Airline": """
        SELECT Company, COUNT(*) AS Flights
        FROM flights_clean_filtered
        GROUP BY Company
        ORDER BY Flights DESC
    """,
    "Price Trends Over Time": """
        SELECT Travel_Date, ROUND(AVG(Price_Float), 2) AS Daily_Avg_Price
        FROM flights_clean_filtered
        GROUP BY Travel_Date
        ORDER BY Travel_Date
    """,
    "Departure Hour Popularity": """
        SELECT Departure_Hour || ':00' AS Hour, COUNT(*) AS Flight_Count
        FROM flights_clean_filtered
        GROUP BY Hour
        ORDER BY Flight_Count DESC
    """,
    "Cabin Class per Airline": """
        SELECT Company, [Cabin Class], COUNT(*) AS Count
        FROM flights_clean_filtered
        GROUP BY Company, [Cabin Class]
        ORDER BY Company, Count DESC
    """,
    "Price Distribution by Airline": """
        SELECT Company, Price_Float
        FROM flights_clean_filtered
    """,
    "Busiest Airports (Top 15)": """
        SELECT Origin,
               COUNT(*) AS Departure_Count,
               ROUND(AVG(Price_Float), 2) AS Avg_Price
        FROM flights_clean_filtered
        GROUP BY Origin
        ORDER BY Departure_Count DESC
        LIMIT 15
    """,
    "Price vs Duration Scatter Plot": """
        SELECT Price_Float, Duration_Minutes, Company
        FROM flights_clean_filtered
    """,
    
}

def run_query(query):
    return pd.read_sql_query(query, conn)

st.sidebar.markdown("---")
st.sidebar.subheader("Choose Insight")
chart_option = st.sidebar.selectbox("Select Analysis", list(queries.keys()))

df_viz = run_query(queries[chart_option])

chart_titles = {
    "Average Price per Airline": "Average Flight Price by Airline",
    "Flight Count per Route": "Most Popular Routes by Flight Count",
    "Average Duration per Route": "Average Flight Duration by Route",
    "Cabin Class Share": "Distribution of Cabin Classes",
    "Flights per Airline": "Total Flights by Airline",
    "Price Trends Over Time": "Daily Average Price Over Time",
    "Departure Hour Popularity": "Departure Time Popularity",
    "Cabin Class per Airline": "Airline-wise Cabin Class Breakdown",
    "Price Distribution by Airline": "Price Distribution & Outliers by Airline",
    "Busiest Airports (Top 15)": "Top 15 Busiest Departure Airports & Their Avg Price",
    "Price vs Duration Scatter Plot": "Price vs Duration Scatter Plot by Airline",
    "Monthly Flight Volume": "Monthly Flight Volume & Average Price Trend",
}

if chart_option == "Average Price per Airline":
    fig = px.bar(df_viz, x='Company', y='Average_Price', title=chart_titles[chart_option], color='Company', color_discrete_map=airline_color_map)

elif chart_option == "Flight Count per Route":
    fig = px.bar(df_viz, x='Route', y='Total_Flights', title=chart_titles[chart_option], color='Total_Flights', color_continuous_scale=px.colors.sequential.Plasma)

elif chart_option == "Average Duration per Route":
    fig = px.bar(df_viz, x='Route', y='Avg_Duration_Min', title=chart_titles[chart_option], color='Avg_Duration_Min', color_continuous_scale=px.colors.sequential.Viridis)

elif chart_option == "Cabin Class Share":
    fig = px.pie(df_viz, names='Cabin Class', values='Count', title=chart_titles[chart_option], color_discrete_sequence=px.colors.qualitative.Safe)

elif chart_option == "Flights per Airline":
    fig = px.bar(df_viz, x='Company', y='Flights', title=chart_titles[chart_option], color='Company', color_discrete_map=airline_color_map)

elif chart_option == "Price Trends Over Time":
    fig = px.line(df_viz, x='Travel_Date', y='Daily_Avg_Price', title=chart_titles[chart_option], markers=True, color_discrete_sequence=['crimson'])

elif chart_option == "Departure Hour Popularity":
    fig = px.bar(df_viz, x='Hour', y='Flight_Count', title=chart_titles[chart_option], color='Flight_Count', color_continuous_scale=px.colors.sequential.Cividis)

elif chart_option == "Cabin Class per Airline":
    fig = px.bar(df_viz, x='Company', y='Count', color='Cabin Class', title=chart_titles[chart_option], barmode='stack', color_discrete_sequence=px.colors.qualitative.Pastel, category_orders={'Company': unique_airlines})

elif chart_option == "Price Distribution by Airline":
    fig = px.box(df_viz, x='Company', y='Price_Float', color='Company', title=chart_titles[chart_option], color_discrete_map=airline_color_map, points="all")

elif chart_option == "Busiest Airports (Top 15)":
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_viz['Origin'],
        y=df_viz['Departure_Count'],
        name='Departure Count',
        marker_color='steelblue',
        yaxis='y1'
    ))

    fig.add_trace(go.Scatter(
        x=df_viz['Origin'],
        y=df_viz['Avg_Price'],
        name='Average Price',
        mode='lines+markers',
        marker_color='orange',
        yaxis='y2'
    ))

    fig.update_layout(
        title=chart_titles[chart_option],
        yaxis=dict(title='Departure Count'),
        yaxis2=dict(title='Average Price (₹)', overlaying='y', side='right'),
        xaxis=dict(title='Origin Airport'),
        legend=dict(x=0.5, y=1.1, orientation='h'),
        margin=dict(l=40, r=40, t=80, b=40)
    )

elif chart_option == "Price vs Duration Scatter Plot":
    fig = px.scatter(df_viz, x='Duration_Minutes', y='Price_Float', color='Company', title=chart_titles[chart_option], color_discrete_map=airline_color_map, labels={"Duration_Minutes": "Duration (minutes)", "Price_Float": "Price"}, hover_data=['Company'])
    fig_trend = px.scatter(df_viz, x='Duration_Minutes', y='Price_Float', trendline='ols', trendline_scope='overall')
    trendline_trace = fig_trend.data[1]
    trendline_trace.name = 'Trendline'
    fig.add_trace(trendline_trace)

else:
    fig = go.Figure()
    fig.add_annotation(text="Chart type not implemented yet.", showarrow=False)

st.plotly_chart(fig, use_container_width=True)

with st.expander("Show filtered data preview"):
    st.write(df_filtered.head(20))
