#!/usr/bin/env python3
"""
Generate synthetic database schemas using LLM.

This creates realistic, production-quality schemas for various domains
to expand our SQL question generation library to 500+ schemas.
"""
import json
import random
import hashlib
from typing import Dict, List, Any
from datetime import date, timedelta

# ─── Sample data generators ───────────────────────────────────────────────────

FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Emma", "Frank", "Grace", "Henry", "Iris", "Jack"]
LAST_NAMES  = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Wilson", "Moore"]
CITIES      = ["New York", "London", "Paris", "Tokyo", "Sydney", "Berlin", "Toronto", "Dubai", "Singapore", "Mumbai"]
COUNTRIES   = ["USA", "UK", "France", "Japan", "Australia", "Germany", "Canada", "UAE", "Singapore", "India"]
STATUSES    = ["active", "inactive", "pending", "completed", "cancelled"]
CATEGORIES  = ["Electronics", "Clothing", "Food", "Books", "Sports", "Home", "Beauty", "Toys", "Automotive", "Health"]


def _rand_date(start_year=2022, end_year=2024) -> str:
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    delta = (end - start).days
    return str(start + timedelta(days=random.randint(0, delta)))


def generate_sample_rows(table_name: str, columns: list, n: int = 5) -> list:
    """Generate n realistic sample rows for a table based on column names/types."""
    rows = []
    for i in range(1, n + 1):
        row = {}
        for col in columns:
            name = col["name"].lower()
            typ  = col["type"].upper()

            # ID columns
            if name.endswith("_id") or name == "id":
                row[col["name"]] = i

            # Account / reference numbers
            elif "account_number" in name or "reference" in name or "invoice_number" in name:
                row[col["name"]] = f"ACC-{1000+i:04d}"
            elif "order_number" in name or "ticket_number" in name:
                row[col["name"]] = f"ORD-{2000+i:04d}"

            # Name / title columns
            elif "first_name" in name:
                row[col["name"]] = random.choice(FIRST_NAMES)
            elif "last_name" in name or "surname" in name:
                row[col["name"]] = random.choice(LAST_NAMES)
            elif name in ("username",):
                row[col["name"]] = f"{random.choice(FIRST_NAMES).lower()}{i}"
            elif name == "product_name":
                products = ["Laptop Pro", "Wireless Mouse", "USB Hub", "Monitor 4K", "Keyboard", "Headphones", "Webcam", "Desk Lamp"]
                row[col["name"]] = products[(i - 1) % len(products)]
            elif name == "course_name":
                courses = ["Advanced Math", "Data Structures", "Machine Learning", "Database Systems", "Web Development"]
                row[col["name"]] = courses[(i - 1) % len(courses)]
            elif name == "company_name":
                row[col["name"]] = random.choice(["Acme Corp", "TechCorp", "GlobalTrade", "DataSystems", "CloudWorks"])
            elif name == "category_name":
                row[col["name"]] = CATEGORIES[(i - 1) % len(CATEGORIES)]
            elif name == "medication":
                row[col["name"]] = random.choice(["Amoxicillin 500mg", "Ibuprofen 400mg", "Metformin 850mg", "Lisinopril 10mg", "Atorvastatin 20mg"])
            elif "dosage" in name:
                row[col["name"]] = random.choice(["500mg twice daily", "10mg once daily", "250mg three times daily", "100mg at bedtime", "5mg as needed"])
            elif "license_number" in name:
                row[col["name"]] = f"DL-{10000+i:05d}"
            elif "contact_name" in name:
                row[col["name"]] = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            elif "contact_title" in name or "title_of_courtesy" in name:
                row[col["name"]] = random.choice(["Mr.", "Ms.", "Dr.", "Mrs."])
            elif "available" in name and "id" not in name:
                row[col["name"]] = random.choice(["Yes", "No"])
            elif "company" in name:
                row[col["name"]] = random.choice(["Acme Corp", "TechCorp", "GlobalTrade", "DataSystems", "CloudWorks", "NovaTech", "BlueStar", "PrimeCo"])
            elif "fax" in name:
                row[col["name"]] = f"+1-555-{2000+i:04d}"
            elif name in ("name", "title"):
                # For employees/staff, use job titles; otherwise domain-specific
                if "employee" in table_name or "staff" in table_name:
                    titles = ["Sales Manager", "Account Executive", "IT Specialist", "HR Manager", "Operations Lead"]
                    row[col["name"]] = titles[(i-1) % len(titles)]
                elif "service" in table_name:
                    services = ["Room Service", "Airport Transfer", "Spa Treatment", "City Tour", "Car Hire", "Meal Package", "Lounge Access", "Priority Boarding"]
                    row[col["name"]] = services[(i-1) % len(services)]
                elif "game" in table_name:
                    games = ["Shadow Quest", "Battle Arena", "Speed Racer", "Puzzle Master", "Dragon Age", "Space Wars", "City Builder", "Dungeon Run"]
                    row[col["name"]] = games[(i-1) % len(games)]
                elif "post" in table_name or "blog" in table_name:
                    posts = ["Top 10 Tips", "Getting Started Guide", "Best Practices", "How It Works", "Case Study", "Industry Trends"]
                    row[col["name"]] = posts[(i-1) % len(posts)]
                elif "assignment" in table_name:
                    assignments = ["Midterm Project", "Final Exam", "Lab Report", "Research Paper", "Group Assignment", "Quiz 1"]
                    row[col["name"]] = assignments[(i-1) % len(assignments)]
                elif "department" in table_name:
                    depts = ["Engineering", "Marketing", "Sales", "Finance", "Operations", "HR", "Legal"]
                    row[col["name"]] = depts[(i-1) % len(depts)]
                elif "menu_item" in table_name or "item" in table_name:
                    items = ["Grilled Chicken", "Caesar Salad", "Beef Burger", "Pasta Carbonara", "Veggie Pizza", "Fish Tacos", "Chocolate Cake", "Lemonade"]
                    row[col["name"]] = items[(i-1) % len(items)]
                elif "categor" in table_name:
                    row[col["name"]] = CATEGORIES[(i-1) % len(CATEGORIES)]
                else:
                    row[col["name"]] = f"{table_name.rstrip('s').title()} {i}"
            elif name in ("bio", "content", "details", "comments"):
                row[col["name"]] = f"Sample {table_name} entry {i}"

            # Contact
            elif "email" in name:
                row[col["name"]] = f"user{i}@example.com"
            elif "phone" in name:
                row[col["name"]] = f"+1-555-{1000+i:04d}"
            elif "address" in name:
                row[col["name"]] = f"{i*10} Main Street"
            elif "city" in name:
                row[col["name"]] = random.choice(CITIES)
            elif "country" in name:
                row[col["name"]] = random.choice(COUNTRIES)
            elif "state" in name or "region" in name:
                row[col["name"]] = f"Region {i}"
            elif "postal" in name or "zip" in name:
                row[col["name"]] = f"{10000 + i}"

            # Dates
            elif "date" in name or "timestamp" in name or "TIME" in typ or "DATE" in typ:
                row[col["name"]] = _rand_date()

            # Counts / integers
            elif any(k in name for k in ("quantity", "_count", "stock", "units",
                                          "credits", "points", "level", "score",
                                          "duration", "days", "hours", "bedrooms",
                                          "follower_count", "likes_count")):
                row[col["name"]] = random.randint(1, 100)

            # Money / numeric - AFTER integer checks to avoid catching interest_rate as float
            elif any(k in name for k in ("price", "amount", "total", "salary",
                                          "balance", "cost", "revenue", "fee",
                                          "discount", "budget")):
                row[col["name"]] = round(random.uniform(100, 5000), 2)
            elif "interest_rate" in name or "commission_rate" in name:
                row[col["name"]] = round(random.uniform(1, 25), 2)
            elif "weight" in name:
                row[col["name"]] = round(random.uniform(0.5, 100), 2)
            elif "rating" in name:
                row[col["name"]] = round(random.uniform(1, 5), 1)

            # Status / type / category - SPECIFIC checks first
            elif "account_type" in name:
                row[col["name"]] = random.choice(["Savings", "Checking", "Business", "Investment"])
            elif "transaction_type" in name:
                row[col["name"]] = random.choice(["deposit", "withdrawal", "transfer", "payment"])
            elif "payment_method" in name:
                row[col["name"]] = random.choice(["Credit Card", "Debit Card", "Bank Transfer", "Cash", "PayPal"])
            elif "job_title" in name:
                row[col["name"]] = random.choice(["Software Engineer", "Data Analyst", "Manager", "Designer", "Developer"])
            elif "semester" in name:
                row[col["name"]] = random.choice(["Spring 2023", "Fall 2023", "Spring 2024", "Fall 2024"])
            elif "course_name" in name:
                courses = ["Advanced Math", "Data Structures", "Machine Learning", "Database Systems", "Web Development"]
                row[col["name"]] = courses[(i - 1) % len(courses)]
            elif "subject" in name:
                row[col["name"]] = random.choice(["Mathematics", "Physics", "Computer Science", "Biology", "Chemistry"])
            elif "specialization" in name:
                row[col["name"]] = random.choice(["Cardiology", "Pediatrics", "Orthopedics", "Neurology", "General Medicine"])
            elif "genre" in name and "id" not in name:
                row[col["name"]] = random.choice(["Action", "Comedy", "Drama", "Thriller", "Sci-Fi"])
            elif "activity_type" in name:
                row[col["name"]] = random.choice(["login", "purchase", "view", "comment", "share"])
            elif "property_type" in name:
                row[col["name"]] = random.choice(["Apartment", "House", "Condo", "Villa", "Studio"])
            elif "origin" in name or "destination" in name:
                row[col["name"]] = random.choice(CITIES)
            elif "status" in name:
                row[col["name"]] = random.choice(["active", "inactive", "pending", "completed", "cancelled", "open", "closed"])
            elif "type" in name and "id" not in name:
                row[col["name"]] = random.choice(["Standard", "Premium", "Basic", "Enterprise"])
            elif "category" in name and "id" not in name:
                row[col["name"]] = random.choice(CATEGORIES)
            elif "gender" in name:
                row[col["name"]] = random.choice(["Male", "Female"])

            # Boolean-ish
            elif "is_" in name or "has_" in name:
                row[col["name"]] = random.choice([True, False])

            # Specific text fields
            elif "grade" in name and "level" not in name:
                row[col["name"]] = random.choice(["A", "B+", "B", "C+", "C"])
            elif "diagnosis" in name:
                row[col["name"]] = random.choice(["Hypertension", "Type 2 Diabetes", "Common Cold", "Migraine", "Anxiety"])
            elif "treatment" in name:
                row[col["name"]] = random.choice(["Medication prescribed", "Physical therapy", "Surgery recommended", "Rest and hydration", "Follow-up in 2 weeks"])
            elif "inspector" in name:
                row[col["name"]] = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            elif "passed" in name:
                row[col["name"]] = random.choice(["Yes", "No"])
            elif "extension" in name:
                row[col["name"]] = f"{100+i}"
            elif "photo_path" in name or "photo" in name:
                row[col["name"]] = f"/photos/{table_name}_{i}.jpg"
            elif "fax" in name:
                row[col["name"]] = f"+1-555-{2000+i:04d}"
            elif "homepage" in name:
                row[col["name"]] = f"https://www.company{i}.com"
            elif "notes" in name:
                row[col["name"]] = f"Note for record {i}"
            elif "picture" in name:
                row[col["name"]] = f"/images/{table_name}_{i}.png"
            elif "customer_desc" in name:
                row[col["name"]] = random.choice(["Premium customer", "Regular customer", "New customer", "VIP member", "Corporate account"])
            elif "ship_name" in name:
                row[col["name"]] = random.choice(["Express Shipping", "Standard Delivery", "Priority Mail", "Overnight Courier", "Economy Freight"])
            elif "territory_description" in name or "region_description" in name:
                row[col["name"]] = random.choice(["North America", "South America", "Europe", "Asia Pacific", "Middle East"])
            elif "active" in name:
                row[col["name"]] = random.choice([1, 0])
            elif "quantity_per_unit" in name:
                row[col["name"]] = random.choice(["10 boxes x 20 bags", "24 - 12 oz bottles", "12 - 550 ml bottles", "48 - 6 oz jars", "36 boxes"])
            elif "special_features" in name:
                row[col["name"]] = random.choice(["Trailers", "Commentaries", "Behind the Scenes", "Deleted Scenes", "None"])
            elif "rating" in name and "id" not in name and table_name in ("film",):
                row[col["name"]] = random.choice(["G", "PG", "PG-13", "R", "NC-17"])
            elif "dept_no" in name:
                row[col["name"]] = f"d{i:03d}"
            elif "dept_name" in name:
                row[col["name"]] = random.choice(["Engineering", "Marketing", "Sales", "Finance", "Operations"])
            elif "from_date" in name or "to_date" in name:
                row[col["name"]] = _rand_date()

            # Text / description
            elif "description" in name or "text" in name or "TEXT" in typ:
                row[col["name"]] = f"Description for {table_name} {i}"

            # Fallback
            elif "INT" in typ or "SMALLINT" in typ:
                row[col["name"]] = i
            elif "DECIMAL" in typ or "NUMERIC" in typ or "REAL" in typ or "FLOAT" in typ:
                row[col["name"]] = round(random.uniform(1, 1000), 2)
            else:
                row[col["name"]] = f"{table_name.rstrip('s').title()} {i}"

        rows.append(row)
    return rows

# Domains to generate schemas for (50+ domains for variety)
DOMAINS = [
    # E-commerce & Retail
    ("e-commerce", "online_store", "Online marketplace with products, orders, customers, reviews, payments"),
    ("e-commerce", "subscription_service", "Subscription-based service with plans, billing, renewals"),
    ("e-commerce", "marketplace", "Multi-vendor marketplace with sellers, products, transactions"),
    ("retail", "inventory_management", "Retail inventory with warehouses, stock, suppliers, transfers"),
    ("retail", "pos_system", "Point of sale system with transactions, items, discounts, receipts"),
    
    # Healthcare
    ("healthcare", "hospital", "Hospital management with patients, doctors, appointments, treatments"),
    ("healthcare", "clinic", "Medical clinic with patients, visits, prescriptions, billing"),
    ("healthcare", "pharmacy", "Pharmacy with medications, prescriptions, inventory, insurance"),
    ("healthcare", "lab", "Medical laboratory with tests, samples, results, equipment"),
    ("healthcare", "insurance", "Health insurance with policies, claims, providers, coverage"),
    
    # Finance & Banking
    ("finance", "banking", "Banking system with accounts, transactions, loans, customers"),
    ("finance", "trading", "Stock trading platform with portfolios, trades, securities, market data"),
    ("finance", "accounting", "Accounting system with ledgers, invoices, expenses, revenue"),
    ("finance", "payroll", "Payroll system with employees, salaries, deductions, tax"),
    ("finance", "lending", "Lending platform with borrowers, loans, payments, credit scores"),
    
    # Education
    ("education", "school", "School management with students, teachers, classes, grades"),
    ("education", "university", "University with courses, enrollments, departments, faculty"),
    ("education", "online_learning", "E-learning platform with courses, lessons, quizzes, progress"),
    ("education", "library", "Library system with books, members, loans, reservations"),
    ("education", "tutoring", "Tutoring service with tutors, students, sessions, subjects"),
    
    # Social Media & Communication
    ("social", "social_network", "Social network with users, posts, comments, likes, follows"),
    ("social", "messaging", "Messaging app with users, conversations, messages, attachments"),
    ("social", "forum", "Discussion forum with threads, posts, users, categories"),
    ("social", "blog", "Blogging platform with authors, posts, comments, tags"),
    ("social", "video_platform", "Video sharing platform with videos, channels, views, subscriptions"),
    
    # Logistics & Transportation
    ("logistics", "shipping", "Shipping company with shipments, tracking, routes, drivers"),
    ("logistics", "warehouse", "Warehouse management with inventory, locations, picking, packing"),
    ("logistics", "delivery", "Delivery service with orders, drivers, routes, tracking"),
    ("logistics", "fleet", "Fleet management with vehicles, maintenance, drivers, routes"),
    ("logistics", "supply_chain", "Supply chain with suppliers, orders, inventory, distribution"),
    
    # Real Estate
    ("real_estate", "property_management", "Property management with properties, tenants, leases, maintenance"),
    ("real_estate", "listings", "Real estate listings with properties, agents, buyers, viewings"),
    ("real_estate", "rental", "Rental platform with properties, tenants, payments, contracts"),
    
    # Travel & Hospitality
    ("travel", "hotel", "Hotel booking with rooms, reservations, guests, payments"),
    ("travel", "airline", "Airline reservation with flights, passengers, bookings, seats"),
    ("travel", "travel_agency", "Travel agency with packages, bookings, customers, itineraries"),
    ("travel", "car_rental", "Car rental with vehicles, reservations, customers, locations"),
    
    # Gaming
    ("gaming", "game_platform", "Gaming platform with players, games, achievements, leaderboards"),
    ("gaming", "mmo", "MMO game with players, characters, items, guilds, quests"),
    ("gaming", "esports", "Esports platform with tournaments, teams, matches, players"),
    
    # HR & Recruitment
    ("hr", "recruitment", "Recruitment system with candidates, jobs, applications, interviews"),
    ("hr", "employee_management", "Employee management with staff, departments, performance, attendance"),
    ("hr", "training", "Training management with courses, employees, certifications, schedules"),
    
    # Food & Restaurant
    ("food", "restaurant", "Restaurant management with menu, orders, tables, reservations"),
    ("food", "food_delivery", "Food delivery with restaurants, orders, drivers, customers"),
    ("food", "catering", "Catering service with events, menus, bookings, staff"),
    
    # Manufacturing & Production
    ("manufacturing", "production", "Production management with products, materials, orders, quality"),
    ("manufacturing", "quality_control", "Quality control with inspections, defects, batches, standards"),
]


def generate_schema_structure(domain: str, subdomain: str, description: str) -> Dict[str, Any]:
    """
    Generate a realistic database schema structure.
    
    This creates a deterministic schema based on the domain without calling LLM.
    We'll create 5-10 tables with proper relationships.
    """
    schema_id = f"synthetic_{domain}_{subdomain}_{hashlib.md5(description.encode()).hexdigest()[:8]}"
    
    # Define common table patterns based on domain
    tables = {}
    
    # Core entities (always present)
    if "e-commerce" in domain or "retail" in domain or "marketplace" in subdomain:
        tables["products"] = {
            "columns": [
                {"name": "product_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "name", "type": "VARCHAR(200)", "constraints": "NOT NULL"},
                {"name": "description", "type": "TEXT", "constraints": ""},
                {"name": "price", "type": "DECIMAL(10,2)", "constraints": "NOT NULL"},
                {"name": "category_id", "type": "INT", "constraints": ""},
                {"name": "stock_quantity", "type": "INT", "constraints": ""},
                {"name": "created_at", "type": "TIMESTAMP", "constraints": ""},
            ]
        }
        tables["customers"] = {
            "columns": [
                {"name": "customer_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "email", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "first_name", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "last_name", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "phone", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "address", "type": "VARCHAR(200)", "constraints": ""},
                {"name": "city", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "country", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "created_at", "type": "TIMESTAMP", "constraints": ""},
            ]
        }
        tables["orders"] = {
            "columns": [
                {"name": "order_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "customer_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "order_date", "type": "TIMESTAMP", "constraints": "NOT NULL"},
                {"name": "total_amount", "type": "DECIMAL(10,2)", "constraints": ""},
                {"name": "status", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "shipping_address", "type": "VARCHAR(200)", "constraints": ""},
            ]
        }
        tables["order_items"] = {
            "columns": [
                {"name": "order_item_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "order_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "product_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "quantity", "type": "INT", "constraints": "NOT NULL"},
                {"name": "unit_price", "type": "DECIMAL(10,2)", "constraints": ""},
            ]
        }
        tables["categories"] = {
            "columns": [
                {"name": "category_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "name", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "parent_category_id", "type": "INT", "constraints": ""},
            ]
        }
    
    elif "healthcare" in domain or "hospital" in subdomain or "clinic" in subdomain:
        tables["patients"] = {
            "columns": [
                {"name": "patient_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "first_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "last_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "date_of_birth", "type": "DATE", "constraints": ""},
                {"name": "gender", "type": "VARCHAR(10)", "constraints": ""},
                {"name": "phone", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "email", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "address", "type": "VARCHAR(200)", "constraints": ""},
                {"name": "primary_doctor_id", "type": "INT", "constraints": ""},
            ]
        }
        tables["doctors"] = {
            "columns": [
                {"name": "doctor_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "first_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "last_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "specialization", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "phone", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "email", "type": "VARCHAR(100)", "constraints": ""},
            ]
        }
        tables["appointments"] = {
            "columns": [
                {"name": "appointment_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "patient_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "doctor_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "appointment_date", "type": "TIMESTAMP", "constraints": "NOT NULL"},
                {"name": "status", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "notes", "type": "TEXT", "constraints": ""},
            ]
        }
        tables["prescriptions"] = {
            "columns": [
                {"name": "prescription_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "appointment_id", "type": "INT", "constraints": ""},
                {"name": "medication", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "dosage", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "duration_days", "type": "INT", "constraints": ""},
            ]
        }
        tables["medical_records"] = {
            "columns": [
                {"name": "record_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "patient_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "doctor_id", "type": "INT", "constraints": ""},
                {"name": "diagnosis", "type": "TEXT", "constraints": ""},
                {"name": "treatment", "type": "TEXT", "constraints": ""},
                {"name": "record_date", "type": "TIMESTAMP", "constraints": ""},
            ]
        }
    
    elif "finance" in domain or "banking" in subdomain:
        tables["accounts"] = {
            "columns": [
                {"name": "account_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "customer_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "account_number", "type": "VARCHAR(20)", "constraints": "NOT NULL"},
                {"name": "account_type", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "balance", "type": "DECIMAL(15,2)", "constraints": ""},
                {"name": "opened_date", "type": "DATE", "constraints": ""},
                {"name": "status", "type": "VARCHAR(20)", "constraints": ""},
            ]
        }
        tables["transactions"] = {
            "columns": [
                {"name": "transaction_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "account_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "transaction_date", "type": "TIMESTAMP", "constraints": "NOT NULL"},
                {"name": "amount", "type": "DECIMAL(15,2)", "constraints": "NOT NULL"},
                {"name": "transaction_type", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "description", "type": "VARCHAR(200)", "constraints": ""},
            ]
        }
        tables["customers"] = {
            "columns": [
                {"name": "customer_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "first_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "last_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "email", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "phone", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "address", "type": "VARCHAR(200)", "constraints": ""},
            ]
        }
        tables["loans"] = {
            "columns": [
                {"name": "loan_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "customer_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "loan_amount", "type": "DECIMAL(15,2)", "constraints": "NOT NULL"},
                {"name": "interest_rate", "type": "DECIMAL(5,2)", "constraints": ""},
                {"name": "start_date", "type": "DATE", "constraints": ""},
                {"name": "end_date", "type": "DATE", "constraints": ""},
                {"name": "status", "type": "VARCHAR(20)", "constraints": ""},
            ]
        }
        tables["payments"] = {
            "columns": [
                {"name": "payment_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "loan_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "payment_date", "type": "DATE", "constraints": "NOT NULL"},
                {"name": "amount", "type": "DECIMAL(15,2)", "constraints": "NOT NULL"},
                {"name": "payment_method", "type": "VARCHAR(20)", "constraints": ""},
            ]
        }
    
    elif "education" in domain or "school" in subdomain or "university" in subdomain:
        tables["students"] = {
            "columns": [
                {"name": "student_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "first_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "last_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "email", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "enrollment_date", "type": "DATE", "constraints": ""},
                {"name": "grade_level", "type": "INT", "constraints": ""},
            ]
        }
        tables["teachers"] = {
            "columns": [
                {"name": "teacher_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "first_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "last_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "email", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "subject", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "hire_date", "type": "DATE", "constraints": ""},
            ]
        }
        tables["courses"] = {
            "columns": [
                {"name": "course_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "course_name", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "teacher_id", "type": "INT", "constraints": ""},
                {"name": "credits", "type": "INT", "constraints": ""},
                {"name": "semester", "type": "VARCHAR(20)", "constraints": ""},
            ]
        }
        tables["enrollments"] = {
            "columns": [
                {"name": "enrollment_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "student_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "course_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "enrollment_date", "type": "DATE", "constraints": ""},
                {"name": "grade", "type": "VARCHAR(2)", "constraints": ""},
            ]
        }
        tables["assignments"] = {
            "columns": [
                {"name": "assignment_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "course_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "title", "type": "VARCHAR(200)", "constraints": "NOT NULL"},
                {"name": "due_date", "type": "DATE", "constraints": ""},
                {"name": "max_points", "type": "INT", "constraints": ""},
            ]
        }
    
    else:
        # Domain-specific tables for social, logistics, travel, gaming, hr, food, real_estate, manufacturing
        if "social" in domain or "messaging" in subdomain or "forum" in subdomain or "blog" in subdomain or "video" in subdomain:
            tables["users"] = {"columns": [
                {"name": "user_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "username", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "email", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "bio", "type": "TEXT", "constraints": ""},
                {"name": "follower_count", "type": "INT", "constraints": ""},
                {"name": "created_at", "type": "TIMESTAMP", "constraints": ""},
            ]}
            tables["posts"] = {"columns": [
                {"name": "post_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "user_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "title", "type": "VARCHAR(200)", "constraints": ""},
                {"name": "content", "type": "TEXT", "constraints": ""},
                {"name": "likes_count", "type": "INT", "constraints": ""},
                {"name": "created_at", "type": "TIMESTAMP", "constraints": ""},
            ]}
            tables["comments"] = {"columns": [
                {"name": "comment_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "post_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "user_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "content", "type": "TEXT", "constraints": ""},
                {"name": "created_at", "type": "TIMESTAMP", "constraints": ""},
            ]}

        elif "logistics" in domain or "shipping" in subdomain or "warehouse" in subdomain or "delivery" in subdomain or "fleet" in subdomain or "supply" in subdomain:
            tables["shipments"] = {"columns": [
                {"name": "shipment_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "customer_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "driver_id", "type": "INT", "constraints": ""},
                {"name": "origin", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "destination", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "weight_kg", "type": "DECIMAL(8,2)", "constraints": ""},
                {"name": "status", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "shipped_date", "type": "DATE", "constraints": ""},
                {"name": "delivered_date", "type": "DATE", "constraints": ""},
            ]}
            tables["customers"] = {"columns": [
                {"name": "customer_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "company_name", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "contact_name", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "email", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "phone", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "city", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "country", "type": "VARCHAR(50)", "constraints": ""},
            ]}
            tables["drivers"] = {"columns": [
                {"name": "driver_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "first_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "last_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "license_number", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "phone", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "hire_date", "type": "DATE", "constraints": ""},
            ]}

        elif "travel" in domain or "hotel" in subdomain or "airline" in subdomain or "car_rental" in subdomain or "travel_agency" in subdomain:
            tables["customers"] = {"columns": [
                {"name": "customer_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "first_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "last_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "email", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "phone", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "country", "type": "VARCHAR(50)", "constraints": ""},
            ]}
            tables["services"] = {"columns": [
                {"name": "service_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "name", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "category", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "price_per_unit", "type": "DECIMAL(10,2)", "constraints": ""},
                {"name": "is_available", "type": "VARCHAR(5)", "constraints": ""},
            ]}
            tables["bookings"] = {"columns": [
                {"name": "booking_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "customer_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "service_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "booking_date", "type": "DATE", "constraints": "NOT NULL"},
                {"name": "start_date", "type": "DATE", "constraints": ""},
                {"name": "end_date", "type": "DATE", "constraints": ""},
                {"name": "total_price", "type": "DECIMAL(10,2)", "constraints": ""},
                {"name": "status", "type": "VARCHAR(20)", "constraints": ""},
            ]}

        elif "gaming" in domain or "game" in subdomain or "esports" in subdomain or "mmo" in subdomain:
            tables["players"] = {"columns": [
                {"name": "player_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "username", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "email", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "level", "type": "INT", "constraints": ""},
                {"name": "total_score", "type": "INT", "constraints": ""},
                {"name": "country", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "joined_date", "type": "DATE", "constraints": ""},
            ]}
            tables["games"] = {"columns": [
                {"name": "game_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "title", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "genre", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "release_date", "type": "DATE", "constraints": ""},
                {"name": "rating", "type": "DECIMAL(3,1)", "constraints": ""},
            ]}
            tables["sessions"] = {"columns": [
                {"name": "session_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "player_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "game_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "start_time", "type": "TIMESTAMP", "constraints": ""},
                {"name": "duration_minutes", "type": "INT", "constraints": ""},
                {"name": "score", "type": "INT", "constraints": ""},
            ]}

        elif "hr" in domain or "recruitment" in subdomain or "employee" in subdomain or "training" in subdomain:
            tables["employees"] = {"columns": [
                {"name": "employee_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "first_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "last_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "email", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "department_id", "type": "INT", "constraints": ""},
                {"name": "job_title", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "salary", "type": "DECIMAL(10,2)", "constraints": ""},
                {"name": "hire_date", "type": "DATE", "constraints": ""},
            ]}
            tables["departments"] = {"columns": [
                {"name": "department_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "name", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "manager_id", "type": "INT", "constraints": ""},
                {"name": "budget", "type": "DECIMAL(12,2)", "constraints": ""},
            ]}
            tables["performance_reviews"] = {"columns": [
                {"name": "review_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "employee_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "review_date", "type": "DATE", "constraints": ""},
                {"name": "rating", "type": "INT", "constraints": ""},
                {"name": "comments", "type": "TEXT", "constraints": ""},
            ]}

        elif "food" in domain or "restaurant" in subdomain or "catering" in subdomain:
            tables["menu_items"] = {"columns": [
                {"name": "item_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "name", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "category", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "price", "type": "DECIMAL(8,2)", "constraints": "NOT NULL"},
                {"name": "is_available", "type": "VARCHAR(5)", "constraints": ""},
            ]}
            tables["orders"] = {"columns": [
                {"name": "order_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "customer_name", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "order_date", "type": "TIMESTAMP", "constraints": "NOT NULL"},
                {"name": "total_amount", "type": "DECIMAL(10,2)", "constraints": ""},
                {"name": "status", "type": "VARCHAR(20)", "constraints": ""},
            ]}
            tables["order_items"] = {"columns": [
                {"name": "order_item_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "order_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "item_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "quantity", "type": "INT", "constraints": "NOT NULL"},
                {"name": "unit_price", "type": "DECIMAL(8,2)", "constraints": ""},
            ]}

        elif "real_estate" in domain or "property" in subdomain or "listings" in subdomain or "rental" in subdomain:
            tables["properties"] = {"columns": [
                {"name": "property_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "address", "type": "VARCHAR(200)", "constraints": "NOT NULL"},
                {"name": "city", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "property_type", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "bedrooms", "type": "INT", "constraints": ""},
                {"name": "price", "type": "DECIMAL(12,2)", "constraints": ""},
                {"name": "listed_date", "type": "DATE", "constraints": ""},
                {"name": "status", "type": "VARCHAR(20)", "constraints": ""},
            ]}
            tables["agents"] = {"columns": [
                {"name": "agent_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "first_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "last_name", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "email", "type": "VARCHAR(100)", "constraints": ""},
                {"name": "phone", "type": "VARCHAR(20)", "constraints": ""},
                {"name": "commission_rate", "type": "DECIMAL(5,2)", "constraints": ""},
            ]}
            tables["transactions"] = {"columns": [
                {"name": "transaction_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "property_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "agent_id", "type": "INT", "constraints": ""},
                {"name": "sale_price", "type": "DECIMAL(12,2)", "constraints": ""},
                {"name": "transaction_date", "type": "DATE", "constraints": ""},
                {"name": "transaction_type", "type": "VARCHAR(20)", "constraints": ""},
            ]}

        elif "manufacturing" in domain or "production" in subdomain or "quality" in subdomain:
            tables["products"] = {"columns": [
                {"name": "product_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "name", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "category", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "unit_cost", "type": "DECIMAL(10,2)", "constraints": ""},
                {"name": "units_in_stock", "type": "INT", "constraints": ""},
            ]}
            tables["production_orders"] = {"columns": [
                {"name": "order_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "product_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "quantity", "type": "INT", "constraints": "NOT NULL"},
                {"name": "start_date", "type": "DATE", "constraints": ""},
                {"name": "end_date", "type": "DATE", "constraints": ""},
                {"name": "status", "type": "VARCHAR(20)", "constraints": ""},
            ]}
            tables["quality_checks"] = {"columns": [
                {"name": "check_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "order_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "check_date", "type": "DATE", "constraints": ""},
                {"name": "passed", "type": "VARCHAR(5)", "constraints": ""},
                {"name": "defects_found", "type": "INT", "constraints": ""},
                {"name": "inspector", "type": "VARCHAR(100)", "constraints": ""},
            ]}

        else:
            # Final fallback - generic but still meaningful
            tables["records"] = {"columns": [
                {"name": "record_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "name", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "category", "type": "VARCHAR(50)", "constraints": ""},
                {"name": "value", "type": "DECIMAL(10,2)", "constraints": ""},
                {"name": "created_at", "type": "TIMESTAMP", "constraints": ""},
            ]}
            tables["users"] = {"columns": [
                {"name": "user_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "username", "type": "VARCHAR(50)", "constraints": "NOT NULL"},
                {"name": "email", "type": "VARCHAR(100)", "constraints": "NOT NULL"},
                {"name": "role", "type": "VARCHAR(30)", "constraints": ""},
                {"name": "created_at", "type": "TIMESTAMP", "constraints": ""},
            ]}
            tables["transactions"] = {"columns": [
                {"name": "transaction_id", "type": "INT", "constraints": "PRIMARY KEY"},
                {"name": "user_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "record_id", "type": "INT", "constraints": "NOT NULL"},
                {"name": "amount", "type": "DECIMAL(10,2)", "constraints": ""},
                {"name": "transaction_date", "type": "TIMESTAMP", "constraints": ""},
                {"name": "status", "type": "VARCHAR(20)", "constraints": ""},
            ]}
    
    # Build schema
    schema = {
        "schema_id": schema_id,
        "name": f"{subdomain.replace('_', ' ').title()}",
        "domain": domain,
        "description": description,
        "source": "synthetic",
        "tables": tables,
        "relationships": [],
        "sample_data": {
            tname: generate_sample_rows(tname, tdef["columns"], n=5)
            for tname, tdef in tables.items()
        },
        "difficulty_levels": ["easy", "medium", "hard"],
        "sql_categories": ["select", "join", "aggregation", "subquery", "window", "cte"],
        "metadata": {
            "table_count": len(tables),
            "total_columns": sum(len(t["columns"]) for t in tables.values()),
            "has_foreign_keys": True,
            "has_numeric_columns": True,
            "has_date_columns": True,
        }
    }
    
    return schema


def generate_all_schemas():
    """
    Generate schemas for all domains.
    """
    schemas = []
    
    print(f"Generating {len(DOMAINS)} synthetic schemas...")
    print()
    
    for domain, subdomain, description in DOMAINS:
        schema = generate_schema_structure(domain, subdomain, description)
        schemas.append(schema)
        print(f"✅ {subdomain}: {schema['metadata']['table_count']} tables, {schema['metadata']['total_columns']} columns")
    
    # Save to file
    output_file = "dataset_creation/synthetic_schemas.json"
    with open(output_file, 'w') as f:
        json.dump(schemas, f, indent=2)
    
    print()
    print(f"✅ Saved {len(schemas)} schemas to {output_file}")
    print()
    print("Summary:")
    print(f"  Total schemas: {len(schemas)}")
    print(f"  Total tables: {sum(s['metadata']['table_count'] for s in schemas)}")
    print(f"  Total columns: {sum(s['metadata']['total_columns'] for s in schemas)}")
    print(f"  Domains covered: {len(set(d[0] for d in DOMAINS))}")
    
    return schemas


if __name__ == "__main__":
    print("="*60)
    print("Synthetic Schema Generator")
    print("="*60)
    print()
    
    schemas = generate_all_schemas()
