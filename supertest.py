import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import pycountry
import plotly.express as px
import gunicorn

app = dash.Dash(__name__)
server = app.server

data = pd.read_csv("https://oliverwkim.com/assets/mountain_to_climb/pwt_10.csv")


country_flags = {}
for country in pycountry.countries:
    country_flags[country.name] = country.alpha_2


def get_flag_emoji(country_name):
    country_code = country_flags.get(country_name)
    if country_code:
        flag = chr(ord(country_code[0]) + 127397) + chr(ord(country_code[1]) + 127397)
        return flag
    else:
        return ''


country_options = [{'label': f"{get_flag_emoji(country)} {country}", 'value': country} for country in data['country'].unique()]

# Growth rates
GermanMiracle = 0.057242325  # 1950-1973
ChineseMiracle = 0.067037168  # 1978-2012
JapaneseMiracle = 0.079924659  # 1950-1973
IrishMiracle = 0.069506166  # Irish Miracle growth rate
SouthKoreanMiracle = 0.082610882  # South Korean Miracle growth rate
TaiwaneseMiracle = 0.051376746  # Taiwanese Miracle growth rate

#Calcs and formatting
def calculateRate(start, end, years):
    return (end / start) ** (1 / years) - 1

def calculateYears(start, end, rate):
    return np.log(end / start) / np.log(1 + rate)

def numberWithCommas(num):
    return "{:,}".format(num)

def updateProjection(lastGDP, lastGDPCatchup, yearsCatchup):
    if yearsCatchup < 0 and lastGDP < lastGDPCatchup:
        return "☠️ Never."
    elif lastGDP > lastGDPCatchup:
        return "🤑 Already richer."
    elif lastGDP == lastGDPCatchup:
        return "🗿 Already there."
    else:
        return f"⏰ In {round(yearsCatchup)} years."

#Layout
app.layout = html.Div(style={'backgroundColor': '#f2f2f2', 'padding': '20px', 'font-family': 'Helvetica'}, children=[
    html.H1("MOUNTAIN TO CLIMB 2", style={'color': '#333333', 'text-transform': 'uppercase', 'margin-bottom': '20px'}),
    
    html.Div([
        dcc.Dropdown(
            id='country-dropdown',
            options=country_options,
            value=country_options[0]['value'],  # Initialize
            placeholder="Select a Country",
            style={'width': '50%', 'margin-bottom': '10px'}
        ),
        dcc.Dropdown(
            id='catchup-country-dropdown',
            options=country_options,
            value=country_options[1]['value'],  # Initialize 
            placeholder="Select a Country to Compare",
            style={'width': '50%', 'margin-bottom': '10px'}
        ),
        dcc.Dropdown(
            id='growth-rate-dropdown',
            options=[
                {'label': 'Recent 10-year growth rates', 'value': '10-year'},
                {'label': 'Average historical growth rates', 'value': 'historical'},
                {'label': f'{get_flag_emoji("Germany")} German miracle rates (1950-73)', 'value': 'German-miracle'},
                {'label': f'{get_flag_emoji("China")} Chinese miracle rates (1978-2012)', 'value': 'Chinese-miracle'},
                {'label': f'{get_flag_emoji("Japan")} Japanese miracle rates (1950-73)', 'value': 'Japanese-miracle'},
                {'label': f'{get_flag_emoji("Ireland")} Celtic Tiger rates (1994-2007)', 'value': 'Irish-miracle'},
                {'label': f'{get_flag_emoji("Korea, Republic of")} Han River miracle rates (1962-1980)', 'value': 'SouthKorean-miracle'},
                {'label': f'{get_flag_emoji("Taiwan, Province of China")} Taiwanese miracle rates (1951-2019)', 'value': 'Taiwanese-miracle'}
            ],
            value='10-year',  # Initialize 
            placeholder="Select a Growth Rate",
            style={'width': '50%', 'margin-bottom': '10px'}
        ),
    ]),
    
    html.Div(id='projection', style={'margin-top': '20px', 'font-size': '30px', 'color': '#666666', 'text-align': 'left'}),
    
    dcc.Graph(id='gdp-graph', style={'margin-top': '20px'}),
    
    #Bottom text
    html.Div([
        html.P("*Note: Add GDP, MVA", style={'font-size': '16px', 'color': '#666666'})
    ], style={'margin-top': '16px', 'text-align': 'left'})
])


#It's all callback, man
@app.callback(
    Output('gdp-graph', 'figure'),
    Output('projection', 'children'),
    Input('country-dropdown', 'value'),
    Input('catchup-country-dropdown', 'value'),
    Input('growth-rate-dropdown', 'value')
)
def update_graph(selectedCountry, catchupCountry, growthRate):
    selectedCountryGDP = data[data['country'] == selectedCountry]
    catchupCountryGDP = data[data['country'] == catchupCountry]

    GDPlast = selectedCountryGDP.iloc[-1]['rgdpe_pc']
    lastGDPCatchup = catchupCountryGDP.iloc[-1]['rgdpe_pc']

    if growthRate == '10-year':
        GDP10yr = selectedCountryGDP.iloc[-11]['rgdpe_pc']
        growthRate = calculateRate(GDP10yr, GDPlast, 10)
    elif growthRate == 'historical':
        GDPstart = selectedCountryGDP.iloc[0]['rgdpe_pc']
        growthRate = calculateRate(GDPstart, GDPlast, len(selectedCountryGDP) - 1)
    elif growthRate == 'German-miracle':
        growthRate = GermanMiracle
    elif growthRate == 'Chinese-miracle':
        growthRate = ChineseMiracle
    elif growthRate == 'Japanese-miracle':
        growthRate = JapaneseMiracle
    elif growthRate == 'Irish-miracle':
        growthRate = IrishMiracle
    elif growthRate == 'SouthKorean-miracle':
        growthRate = SouthKoreanMiracle
    elif growthRate == 'Taiwanese-miracle':
        growthRate = TaiwaneseMiracle

    yearsCatchup = calculateYears(GDPlast, lastGDPCatchup, growthRate)

    # Plot what? Plot what?
    projection_text = f" {updateProjection(GDPlast, lastGDPCatchup, yearsCatchup)}" #removed 'Projection:'
    fig = go.Figure()

    #Traces braces, to the races
    fig.add_trace(go.Scatter(x=selectedCountryGDP['year'], y=selectedCountryGDP['rgdpe_pc'],
                             mode='lines+markers',
                             name=selectedCountry,
                             line=dict(color='#4682B4', width=2),
                             marker=dict(size=8, color='#4682B4', symbol='circle'))
                 )
    fig.add_trace(go.Scatter(x=catchupCountryGDP['year'], y=catchupCountryGDP['rgdpe_pc'],
                             mode='lines+markers',
                             name=catchupCountry,
                             line=dict(color='#FF6347', width=2),
                             marker=dict(size=8, color='#FF6347', symbol='circle'))
                 )

    #Projected line
    projection_years = pd.concat([selectedCountryGDP['year'], pd.Series(range(selectedCountryGDP['year'].max() + 1, selectedCountryGDP['year'].max() + int(np.ceil(yearsCatchup)) + 1))])
    projected_GDP = selectedCountryGDP['rgdpe_pc'].tolist() + [GDPlast * (1 + growthRate) ** i for i in range(1, int(np.ceil(yearsCatchup)) + 1)]
    fig.add_trace(go.Scatter(x=projection_years, y=projected_GDP,
                             mode='lines',
                             name=f'{selectedCountry} Projection',
                             line=dict(color='#32CD32', width=2, dash='dash'))
                 )

    #Da trend line
    fig.add_trace(go.Scatter(x=[selectedCountryGDP['year'].min(), selectedCountryGDP['year'].max()],
                             y=[selectedCountryGDP['rgdpe_pc'].min(), GDPlast],
                             mode='lines',
                             name='Trendline',
                             line=dict(color='#808080', width=2, dash='dot'))
                 )

    # Update layout
    fig.update_layout(
        xaxis=dict(title='Year', range=[selectedCountryGDP['year'].min(), projection_years.max()], gridcolor='#ffffff'),  # Update gridcolor for x-axis
        yaxis=dict(title='GDP per capita, 2017 US$', gridcolor='#ffffff'),  
        legend=dict(x=0, y=1),
        margin=dict(l=40, r=40, t=40, b=30),  
        hovermode='closest',
        plot_bgcolor='#f2f2f2',  
        paper_bgcolor='#f2f2f2',  
        font=dict(family="Helvetica", size=12, color="#333333"), 
        template='plotly_white'  
    )

    projection = f"Projection: {updateProjection(GDPlast, lastGDPCatchup, yearsCatchup)}"
    return fig, projection_text

# Run da jewels

