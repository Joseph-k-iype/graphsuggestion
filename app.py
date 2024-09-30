from flask import Flask, request, jsonify, render_template
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS
import pandas as pd
import math

app = Flask(__name__)

# Initialize the RDF graph
g = Graph()
EX = Namespace("http://example.org/")
g.bind("ex", EX)

# Load the datasets
company_metadata = pd.read_csv('company_metadata.csv')
esg_data = pd.read_csv('esg.csv')
governance_data = pd.read_csv('governance.csv')
market_data = pd.read_csv('market_data.csv')

# Helper function to normalize values to a scale of 0–100
def normalize(value, min_value, max_value):
    return ((value - min_value) / (max_value - min_value)) * 100

# Function to replace NaN values with a default value (e.g., 0)
def clean_data(value):
    if pd.isna(value):
        return 0  # Replace NaN with a default value (can be adjusted)
    return value

# Function to calculate a weighted Euclidean distance with penalties for higher values
def calculate_distance(affected_company_scores, comparison_company_scores):
    distance = 0
    for factor, affected_score in affected_company_scores.items():
        comparison_score = comparison_company_scores[factor]

        # Penalize higher values with a larger distance, prefer similar or slightly lower values
        if comparison_score > affected_score:
            distance += (comparison_score - affected_score) ** 2  # Penalty for higher values
        else:
            distance += (affected_score - comparison_score) ** 1.5  # Slightly lesser penalty for lower values

    return math.sqrt(distance)

# Function to normalize the data and find companies closest to the affected company
def get_closest_companies(company_data, affected_company, selected_factors):
    affected_company_data = None
    normalized_data = []

    # Normalize each factor for all companies
    for row in company_data:
        normalized_stock_price = normalize(clean_data(row['StockPrice2021']), 0, 2000)
        normalized_esg_score = normalize(clean_data(row['ESGScore_x']), 0, 100)
        normalized_governance = normalize(clean_data(row['GovernanceScore']), 0, 100)
        normalized_risk = 100 if clean_data(row['RiskLevel']) == 'Low' else 50  # Low = 100, Medium = 50, High = 0
        normalized_market_cap = normalize(clean_data(row['MarketCap (T)']), 0, 5)

        # Create a dictionary of normalized scores
        normalized_scores = {
            'stockPrice': normalized_stock_price,
            'ESGScore': normalized_esg_score,
            'GovernanceScore': normalized_governance,
            'RiskLevel': normalized_risk,
            'MarketCap': normalized_market_cap
        }

        if row['CompanyName'] == affected_company:
            affected_company_data = normalized_scores  # Save the affected company's data
        else:
            normalized_data.append({
                'company': row['CompanyName'],
                'normalized_scores': normalized_scores,
                'original_data': row  # Save original data for selected factors
            })

    # Calculate distances for each company compared to the affected company
    for company in normalized_data:
        company['distance'] = calculate_distance(
            {factor: affected_company_data[factor] for factor in selected_factors},
            {factor: company['normalized_scores'][factor] for factor in selected_factors}
        )

    # Sort companies by their distance to the affected company (closest first)
    normalized_data.sort(key=lambda x: x['distance'])

    return normalized_data

# Populating the RDF graph with data from the datasets
def populate_graph():
    # Combine all relevant data into one dataframe
    company_data = company_metadata.merge(esg_data, on="CompanyID", how="left") \
                                   .merge(governance_data, on="CompanyID", how="left") \
                                   .merge(market_data, on="CompanyID", how="left")

    for _, row in company_data.iterrows():
        company_uri = URIRef(f"http://example.org/company/{row['CompanyName']}")
        g.add((company_uri, RDF.type, EX.Company))
        g.add((company_uri, EX.hasStockPrice, Literal(row['StockPrice2021'])))
        g.add((company_uri, EX.hasESGScore, Literal(row['ESGScore_x'])))  # ESGScore from merged data
        g.add((company_uri, EX.hasGovernanceRating, Literal(row['GovernanceRating'])))
        g.add((company_uri, EX.hasRiskLevel, Literal(row['RiskLevel'])))
        g.add((company_uri, EX.isInSector, Literal(row['Sector'])))
        g.add((company_uri, EX.hasMarketCap, Literal(row['MarketCap (T)'])))
        g.add((company_uri, EX.hasDividendYield, Literal(row['DividendYield (%)'])))

populate_graph()

# Route for the main page
@app.route('/')
def index():
    return render_template('index.html')

# Endpoint to get available companies and factors
@app.route('/get_factors', methods=['GET'])
def get_factors():
    companies = company_metadata['CompanyName'].tolist()
    factors = ['stockPrice', 'ESGScore', 'GovernanceScore', 'RiskLevel', 'MarketCap']
    factor_info = {
        'stockPrice': 'Stock Price (2021)',
        'ESGScore': 'ESG Score',
        'GovernanceScore': 'Governance Score (0-100)',
        'RiskLevel': '0/50/100',
        'MarketCap': 'Market Cap (in trillions)'
    }
    return jsonify({
        'companies': companies,
        'factors': factors,
        'factor_info': factor_info
    })

# Dynamic route to handle recommendations based on selected factors
@app.route('/suggest_partners_dynamic', methods=['POST'])
def suggest_partners_dynamic():
    data = request.json
    affected_company = data['company']
    factors = data['factors']

    # Combine all relevant data into one dataframe
    companies = company_metadata.merge(esg_data, on="CompanyID", how="left") \
                                .merge(governance_data, on="CompanyID", how="left") \
                                .merge(market_data, on="CompanyID", how="left")

    # Get the closest companies based on selected factors
    closest_companies = get_closest_companies(companies.to_dict('records'), affected_company, factors)

    # Create nodes and edges for Cytoscape visualization
    nodes = [{'data': {'id': affected_company, 'label': affected_company}}]  # Add affected company node
    nodes.extend([{'data': {'id': company['company'], 'label': company['company']}} for company in closest_companies])

    # Add distances as edge labels to show in the graph
    edges = [{'data': {'source': affected_company, 'target': company['company'], 
                       'label': f'Distance: {round(company["distance"], 2)}'}}
             for company in closest_companies]

    # Build recommendations
    recommendations = [
        {
            'company': company['company'],
            'Stock Price': clean_data(company['original_data']['StockPrice2021']),
            'ESG Score': clean_data(company['original_data']['ESGScore_x']),
            'Governance Score': clean_data(company['original_data']['GovernanceScore']),
            'Risk Level': clean_data(company['original_data']['RiskLevel']),
            'Market Cap': clean_data(company['original_data']['MarketCap (T)']),
            'Total Score': round(company['distance'], 2)  # Lower distance means closer match
        }
        for company in closest_companies
    ]

    return jsonify({
        'nodes': nodes,  # All nodes including the affected company
        'edges': edges,  # Edges representing relationships and distances
        'recommendations': recommendations  # Detailed recommendations with factor values
    })

if __name__ == '__main__':
    app.run(debug=True)
