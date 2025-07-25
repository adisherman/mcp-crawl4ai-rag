#!/usr/bin/env python3
"""Test Neo4j connection and contents"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def test_neo4j_connection():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    print(f"Connecting to Neo4j at {uri} as {user}")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            # Test connection
            result = session.run("RETURN 1 as test")
            print("Connection successful!")
            
            # Count nodes by type
            node_types = ["Component", "Hook", "Function", "Module", "Interface", "Type"]
            for node_type in node_types:
                result = session.run(f"MATCH (n:{node_type}) RETURN count(n) as count")
                count = result.single()["count"]
                print(f"{node_type} nodes: {count}")
            
            # Check for specific components
            print("\nChecking for specific components:")
            components = ["FormInput", "FormSlider", "Button", "AdvancedDatePicker"]
            for comp in components:
                result = session.run("MATCH (c:Component {name: $name}) RETURN c", name=comp)
                exists = result.single() is not None
                print(f"  {comp}: {'exists' if exists else 'NOT FOUND'}")
            
            # Check for specific hooks
            print("\nChecking for specific hooks:")
            hooks = ["useState", "useFormAnimation", "useValidationEngine", "useTheme"]
            for hook in hooks:
                result = session.run("MATCH (h:Hook {name: $name}) RETURN h", name=hook)
                exists = result.single() is not None
                print(f"  {hook}: {'exists' if exists else 'NOT FOUND'}")
                
        driver.close()
        
    except Exception as e:
        print(f"Error: {e}")
        print(f"Make sure Neo4j is running and credentials are correct")

if __name__ == "__main__":
    test_neo4j_connection()