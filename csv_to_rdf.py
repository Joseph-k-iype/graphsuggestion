import pandas as pd
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, XSD

# Define RDF graph and namespaces
g = Graph()
EX = Namespace("http://example.org/ns#")
g.bind("ex", EX)

# Load datasets
company_df = pd.read_csv("company.csv")
esg_df = pd.read_csv("esg.csv")
governance_df = pd.read_csv("governance.csv")
product_df = pd.read_csv("product.csv")
stock_df = pd.read_csv("stock.csv")

# Convert Company data to RDF
def convert_company_data(df):
    for index, row in df.iterrows():
        company_uri = URIRef(f"http://example.org/company/{row['CompanyID']}")
        g.add((company_uri, RDF.type, EX.Company))
        g.add((company_uri, EX.hasCompanyName, Literal(row['CompanyName'], datatype=XSD.string)))
        g.add((company_uri, EX.hasMarketCap, Literal(row['MarketCap'], datatype=XSD.float)))
        g.add((company_uri, EX.hasRevenue, Literal(row['Revenue'], datatype=XSD.float)))

# Convert ESG data to RDF
def convert_esg_data(df):
    for index, row in df.iterrows():
        company_uri = URIRef(f"http://example.org/company/{row['CompanyID']}")
        esg_uri = URIRef(f"http://example.org/esg/{row['ESGID']}")
        g.add((esg_uri, RDF.type, EX.ESG))
        g.add((esg_uri, EX.hasESGScore, Literal(row['ESGScore'], datatype=XSD.float)))
        g.add((company_uri, EX.hasESG, esg_uri))

# Convert Governance data to RDF
def convert_governance_data(df):
    for index, row in df.iterrows():
        company_uri = URIRef(f"http://example.org/company/{row['CompanyID']}")
        governance_uri = URIRef(f"http://example.org/governance/{row['GovernanceID']}")
        g.add((governance_uri, RDF.type, EX.Governance))
        g.add((governance_uri, EX.hasGovernanceScore, Literal(row['GovernanceScore'], datatype=XSD.float)))
        g.add((company_uri, EX.hasGovernance, governance_uri))

# Convert Product data to RDF
def convert_product_data(df):
    for index, row in df.iterrows():
        company_uri = URIRef(f"http://example.org/company/{row['CompanyID']}")
        product_uri = URIRef(f"http://example.org/product/{row['ProductID']}")
        g.add((product_uri, RDF.type, EX.Product))
        g.add((product_uri, EX.producesProduct, Literal(row['ProductName'], datatype=XSD.string)))
        g.add((company_uri, EX.produces, product_uri))

# Convert Stock data to RDF
def convert_stock_data(df):
    for index, row in df.iterrows():
        company_uri = URIRef(f"http://example.org/company/{row['CompanyID']}")
        stock_uri = URIRef(f"http://example.org/stock/{row['StockID']}")
        g.add((stock_uri, RDF.type, EX.Stock))
        g.add((stock_uri, EX.hasStockPrice, Literal(row['StockPrice'], datatype=XSD.float)))
        g.add((company_uri, EX.hasStock, stock_uri))

# Convert all datasets to RDF
convert_company_data(company_df)
convert_esg_data(esg_df)
convert_governance_data(governance_df)
convert_product_data(product_df)
convert_stock_data(stock_df)

# Save RDF to Turtle format
g.serialize(destination="company_data.ttl", format="turtle")
print("RDF data has been saved to company_data.ttl")
