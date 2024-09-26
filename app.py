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

# Helper function to normalize values to a scale of 0–100
def normalize(value, min_value, max_value):
    return ((value - min_value) / (max_value - min_value)) * 100

# Function to convert governance rating to numeric scale
def governance_to_score(rating):
    scale = {
        "A+": 90,
        "A": 80,
        "B+": 70,
        "B": 60,
        "C+": 50,
        "C": 40,
    }
    return scale.get(rating, 50)  # Default to 50 if rating not found

# Function to calculate the Euclidean distance between two companies based on selected factors
def calculate_distance(affected_company_scores, comparison_company_scores):
    distance = 0
    for factor, affected_score in affected_company_scores.items():
        comparison_score = comparison_company_scores[factor]
        distance += (affected_score - comparison_score) ** 2
    return math.sqrt(distance)

# Function to normalize the data and find companies closest to the affected company
def get_closest_companies(company_data, affected_company, selected_factors):
    affected_company_data = None
    normalized_data = []

    # Normalize each factor for all companies
    for row in company_data:
        normalized_stock_price = normalize(row['stockPrice'], 0, 2000)
        normalized_esg_score = normalize(row['ESGScore'], 0, 100)
        normalized_governance = governance_to_score(row['GovernanceRating'])
        normalized_risk = 100 if row['RiskLevel'] == 'Low' else 50  # Low = 100, Medium = 50, High = 0

        # Create a dictionary of normalized scores
        normalized_scores = {
            'stockPrice': normalized_stock_price,
            'ESGScore': normalized_esg_score,
            'GovernanceRating': normalized_governance,
            'RiskLevel': normalized_risk
        }

        if row['company'] == affected_company:
            affected_company_data = normalized_scores  # Save the affected company's data
        else:
            normalized_data.append({
                'company': row['company'],
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

# Populating the graph with mock data
def populate_graph():
    companies = pd.DataFrame({
        'CompanyID': [1, 2, 3],
        'CompanyName': ['Samsung', 'Apple', 'Microsoft'],
        'Sector': ['Technology', 'Technology', 'Technology'],
        'StockPrice': [800, 1200, 900],
        'ESGScore': [75, 90, 85],
        'GovernanceRating': ['A', 'A+', 'B+'],
        'RiskLevel': ['Low', 'Medium', 'High'],
        'SectorInfluence': [85, 90, 80]
    })

    for index, row in companies.iterrows():
        company_uri = URIRef(f"http://example.org/company/{row['CompanyName']}")
        g.add((company_uri, RDF.type, EX.Company))
        g.add((company_uri, EX.hasStockPrice, Literal(row['StockPrice'])))
        g.add((company_uri, EX.hasESGScore, Literal(row['ESGScore'])))
        g.add((company_uri, EX.hasGovernanceRating, Literal(row['GovernanceRating'])))
        g.add((company_uri, EX.hasRiskLevel, Literal(row['RiskLevel'])))
        g.add((company_uri, EX.isInSector, Literal(row['Sector'])))

populate_graph()

# Route for the main page
@app.route('/')
def index():
    return render_template('index.html')

# Endpoint to get available companies and factors
@app.route('/get_factors', methods=['GET'])
def get_factors():
    companies = ['Samsung', 'Apple', 'Microsoft']  # Fetch dynamically in real scenarios
    factors = ['stockPrice', 'ESGScore', 'GovernanceRating', 'RiskLevel']
    factor_info = {
        'stockPrice': 'Stock Price',
        'ESGScore': 'ESG Score',
        'GovernanceRating': 'Governance Rating (0-100)',
        'RiskLevel': 'Low/Medium Risk'
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

    # Fetch the companies' data from the graph (simulating with mock data)
    companies = pd.DataFrame({
        'company': ['Samsung', 'Apple', 'Microsoft'],
        'stockPrice': [800, 1200, 900],
        'ESGScore': [75, 90, 85],
        'GovernanceRating': ['A', 'A+', 'B+'],
        'RiskLevel': ['Low', 'Medium', 'High']
    })

    # Get the closest companies based on selected factors
    closest_companies = get_closest_companies(companies.to_dict('records'), affected_company, factors)

    # Create a set of all nodes (including the affected company) to ensure all nodes exist
    nodes = [{'data': {'id': affected_company, 'label': affected_company}}]  # Add affected company node
    nodes.extend([{'data': {'id': company['company'], 'label': company['company']}} for company in closest_companies])

    # Create edges for the graph
    edges = []
    for company in closest_companies:
        for factor in factors:
            edges.append({
                'source': affected_company,
                'target': company['company'],
                'label': factor
            })

    # Build recommendations to return the original (non-normalized) data for the selected factors
    recommendations = [
        {
            'company': company['company'],
            'Stock Price': company['original_data']['stockPrice'],
            'ESG Score': company['original_data']['ESGScore'],
            'Governance Rating': company['original_data']['GovernanceRating'],
            'Risk Level': company['original_data']['RiskLevel'],
            'Total Score': round(company['distance'], 2)  # Lower distance means closer match
        }
        for company in closest_companies
    ]

    # Return the nodes, edges, and recommendation data
    return jsonify({
        'nodes': nodes,  # Send all nodes including the affected company
        'edges': [{'data': {'source': edge['source'], 'target': edge['target'], 'label': edge['label']}} for edge in edges],
        'recommendations': recommendations  # Include detailed recommendations with factor values
    })

if __name__ == '__main__':
    app.run(debug=True)
