"""
Generate realistic messy datasets for Data Cleaning & Reporting Automation.
"""
import os
import pandas as pd
import numpy as np
import openpyxl

os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# -------------------------------------------------------------
# 1. Messy Sales Data (CSV)
# -------------------------------------------------------------
np.random.seed(42)

regions_raw = ["North", "north", "NORTH", "North Region", "South", "south", "SOUTH", "East", "east", "EAST", "West", "west", "WEST", None]
categories_raw = ["Electronics", "electronics", "ELECTRONICS", "Furniture", "furniture", "FURNITURE", "Office Supplies", "office supplies", "OFFICE SUPPLIES", "Clothing", "clothing"]
items_map = {
    "Electronics": ["Laptop Pro 15", "Wireless Mouse", "4K Ultra Monitor", "Noise-Cancelling Headphones", "USB-C Hub", "Smart Watch v2"],
    "Furniture": ["Ergonomic Desk Chair", "Standing Desk", "Bookshelf 5-Tier", "Conference Table", "Desk Lamp LED"],
    "Office Supplies": ["Gel Pens Box (50)", "A4 Printing Paper (Ream)", "Heavy Duty Stapler", "Sticky Notes Pack", "Whiteboard 4x3"],
    "Clothing": ["Corporate Polo T-Shirt", "Executive Blazer", "Casual Friday Hoodie", "Breathable Face Mask (10pk)"]
}
customers_raw = [
    "Rahul Sharma", "Priya Patel", "Amit Verma", "Sneha Rao", "Vikram Singh",
    "Ananya Iyer", "Rohan Gupta", "Deepika Padukone", "Suresh Menon", "Kavita Reddy",
    "John Doe", "Jane Smith", "Michael Chang", "Emily Watson", "David Miller",
    "Sarah Connor", "Robert Vance", "Lisa Kudrow", "Bruce Wayne", "Clark Kent",
    None, "   ", "Arjun Kapoor", "Meera Nair", "Karan Johar"
]
payment_methods = ["Credit Card", "credit card", "UPI", "upi", "Net Banking", "Cash on Delivery", "Debit Card", None]

rows = []
base_date = pd.Timestamp("2026-01-01")

for i in range(1, 151):
    cat_raw = np.random.choice(categories_raw)
    clean_cat = "Electronics" if "elect" in str(cat_raw).lower() else \
                "Furniture" if "furn" in str(cat_raw).lower() else \
                "Office Supplies" if "office" in str(cat_raw).lower() else "Clothing"
    item = np.random.choice(items_map[clean_cat])
    cust = np.random.choice(customers_raw)
    reg = np.random.choice(regions_raw)
    pay = np.random.choice(payment_methods)
    
    # Date formatting variations
    day_offset = np.random.randint(0, 240)
    cur_date = base_date + pd.Timedelta(days=day_offset)
    date_style = np.random.choice(["iso", "dmy", "mdy", "verbose", "invalid", "missing"])
    if date_style == "iso":
        date_str = cur_date.strftime("%Y-%m-%d")
    elif date_style == "dmy":
        date_str = cur_date.strftime("%d/%m/%Y")
    elif date_style == "mdy":
        date_str = cur_date.strftime("%m-%d-%Y")
    elif date_style == "verbose":
        date_str = cur_date.strftime("%b %d, %Y")
    elif date_style == "invalid":
        date_str = "2026-99-99" if np.random.rand() > 0.5 else "Unknown Date"
    else:
        date_str = None
        
    # Quantities & Prices with dirty formatting
    qty_val = np.random.choice([1, 2, 3, 4, 5, 8, 10, 15, -2, 0, 500, None]) # has negative, zero, outlier 500, missing
    base_price = np.random.choice([199.99, 450.0, 1250.0, 3500.0, 14999.0, 45000.0, 89900.0, -150.0, None])
    
    if base_price is not None:
        price_fmt = np.random.choice(["dollar", "rupee", "comma", "plain", "spaced"])
        if price_fmt == "dollar":
            price_str = f"${base_price:,.2f}"
        elif price_fmt == "rupee":
            price_str = f"₹ {base_price:,.2f}"
        elif price_fmt == "comma":
            price_str = f"{base_price:,.2f}"
        elif price_fmt == "spaced":
            price_str = f"   {base_price}   "
        else:
            price_str = str(base_price)
    else:
        price_str = None
        
    discount = np.random.choice(["0%", "5%", "10%", "15%", "20%", "25%", "50%", "-5%", "None", None])
    
    rows.append({
        "Order ID": f"ORD-2026-{1000 + i}",
        "Order Date": date_str,
        "Customer Name": cust,
        "Region": reg,
        "Product Category": cat_raw,
        "Item": item,
        "Quantity": qty_val,
        "Unit Price": price_str,
        "Discount %": discount,
        "Payment Method": pay
    })

sales_df = pd.DataFrame(rows)

# Inject exact duplicate rows (10 duplicates)
dup_indices = np.random.choice(len(sales_df), size=10, replace=False)
duplicates = sales_df.iloc[dup_indices].copy()
sales_df = pd.concat([sales_df, duplicates], ignore_index=True)

# Add a few completely blank rows
blank_rows = pd.DataFrame([{col: None for col in sales_df.columns} for _ in range(3)])
sales_df = pd.concat([sales_df, blank_rows], ignore_index=True)

sales_df.to_csv("data/raw/messy_sales_data.csv", index=False)
print("Created data/raw/messy_sales_data.csv with shape:", sales_df.shape)

# -------------------------------------------------------------
# 2. Messy Customer Data (Excel)
# -------------------------------------------------------------
cust_rows = []
genders_raw = ["Male", "male", "M", "MALE", "Female", "female", "F", "FEMALE", "Other", "Unknown", None]
cities_raw = ["Mumbai", "mumbai", "MUMBAI", "Delhi", "delhi", "Bengaluru", "Bangalore", "Hyderabad", "Pune", "Chennai", "Kolkata", None]
segments_raw = ["Consumer", "consumer", "Corporate", "corporate", "Home Office", "home office", None]
statuses_raw = ["Active", "active", "ACTIVE", "Inactive", "inactive", "Pending", "Suspended", None]

for i in range(1, 121):
    fn = np.random.choice(["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
                           "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Chiara", "Myra", "Riya", "Avani", "Prisha", None])
    ln = np.random.choice(["Sharma", "Verma", "Patel", "Mehta", "Iyer", "Rao", "Reddy", "Nair", "Kapoor", "Khan", "Singh", None])
    gender = np.random.choice(genders_raw)
    
    # Dirty Email
    email_style = np.random.choice(["clean", "spaces", "invalid", "missing"])
    clean_handle = f"{str(fn).lower()}.{str(ln).lower()}{np.random.randint(10, 99)}" if fn and ln else f"user{i}"
    if email_style == "clean":
        email = f"{clean_handle}@example.com"
    elif email_style == "spaces":
        email = f"  {clean_handle}@domain.org  "
    elif email_style == "invalid":
        email = f"{clean_handle}at-domain.com"
    else:
        email = None
        
    # Dirty Phone
    import random
    phone_fmt = np.random.choice(["std", "plus", "hyphen", "invalid", "missing"])
    p_num = random.randint(7000000000, 9999999999)
    if phone_fmt == "std":
        phone = f"+91 {p_num}"
    elif phone_fmt == "plus":
        phone = f"+91-{p_num}"
    elif phone_fmt == "hyphen":
        phone = f"{str(p_num)[:5]}-{str(p_num)[5:]}"
    elif phone_fmt == "invalid":
        phone = "N/A"
    else:
        phone = None
        
    income = np.random.choice(["$45,000", "₹ 7,50,000", "1200000", "  85,000.00 ", "-25000", "15000000", None])
    credit_score = np.random.choice([650, 720, 800, 590, 780, 850, -50, 9999, None])
    
    cust_rows.append({
        "Customer ID": f"CUST-{2000 + i}",
        "First Name": fn,
        "Last Name": ln,
        "Gender": gender,
        "Email Address": email,
        "Phone Number": phone,
        "City": np.random.choice(cities_raw),
        "Annual Income": income,
        "Credit Score": credit_score,
        "Customer Segment": np.random.choice(segments_raw),
        "Account Status": np.random.choice(statuses_raw),
        "Signup Date": (pd.Timestamp("2024-01-01") + pd.Timedelta(days=np.random.randint(0, 900))).strftime("%Y-%m-%d") if np.random.rand() > 0.1 else None
    })

cust_df = pd.DataFrame(cust_rows)
# Duplicate rows
cust_dups = cust_df.iloc[np.random.choice(len(cust_df), size=8, replace=False)].copy()
cust_df = pd.concat([cust_df, cust_dups], ignore_index=True)
cust_df.to_excel("data/raw/messy_customer_data.xlsx", index=False)
print("Created data/raw/messy_customer_data.xlsx with shape:", cust_df.shape)

# -------------------------------------------------------------
# 3. Messy Employee Data (CSV)
# -------------------------------------------------------------
dept_raw = ["Engineering", "engineering", "ENGINEERING", "Sales", "sales", "Marketing", "marketing", "Human Resources", "HR", "Finance", "finance", None]
emp_rows = []
for i in range(1, 101):
    emp_rows.append({
        "Emp ID": f"EMP-{5000 + i}",
        "Employee Name": f"Employee {i}",
        "Department": np.random.choice(dept_raw),
        "Job Title": np.random.choice(["Software Engineer", "Senior Developer", "Account Executive", "Marketing Lead", "HR Specialist", "Financial Analyst"]),
        "Hire Date": (pd.Timestamp("2020-01-01") + pd.Timedelta(days=np.random.randint(0, 2000))).strftime("%d-%m-%Y") if np.random.rand() > 0.08 else "Invalid Date",
        "Salary": np.random.choice(["$85,000", "₹14,50,000", " 95000 ", "120,000", "-5000", None]),
        "Performance Rating": np.random.choice([1, 2, 3, 4, 5, 4.5, 99, None]),
        "Experience (Yrs)": np.random.choice([1, 3, 5, 8, 12, 15, -1, 45, None]),
        "Location": np.random.choice(["Bangalore", "Hyderabad", "Pune", "Remote", "remote", "REMOTE", None])
    })

emp_df = pd.DataFrame(emp_rows)
emp_df = pd.concat([emp_df, emp_df.iloc[:5].copy()], ignore_index=True)
emp_df.to_csv("data/raw/messy_employee_data.csv", index=False)
print("Created data/raw/messy_employee_data.csv with shape:", emp_df.shape)

# -------------------------------------------------------------
# 4. Messy Financial Data (Excel)
# -------------------------------------------------------------
fin_rows = []
quarters = ["Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025", "Q1-2026", "Q2-2026"]
for q in quarters:
    for dept in ["Engineering", "Sales & Marketing", "Operations", "General & Admin"]:
        rev = np.random.randint(200000, 1500000)
        cost = np.random.randint(100000, int(rev * 0.8))
        fin_rows.append({
            "Fiscal Quarter": q,
            "Business Unit": dept,
            "Gross Revenue": f"${rev:,.2f}" if np.random.rand() > 0.2 else str(rev),
            "Operating Cost": f"${cost:,.2f}",
            "Marketing Spend": f"${np.random.randint(10000, 80000):,.2f}" if np.random.rand() > 0.1 else None,
            "Tax Rate %": "18%" if np.random.rand() > 0.2 else "0.18",
            "Report Status": np.random.choice(["Audited", "audited", "Draft", "draft", "Pending", None])
        })

fin_df = pd.DataFrame(fin_rows)
fin_df = pd.concat([fin_df, fin_df.iloc[:3].copy()], ignore_index=True)
fin_df.to_excel("data/raw/messy_financial_data.xlsx", index=False)
print("Created data/raw/messy_financial_data.xlsx with shape:", fin_df.shape)
print("All sample datasets generated successfully!")
