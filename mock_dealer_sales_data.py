import pandas as pd
import random
import datetime

countries = ["Ghana", "Nigeria", "Kenya", "Uganda", "Senegal", "CIV"]
product_classifications = [
    "Local Trade",
    "Dealer Marketplace",
    "Imports",
    "Repossessed Assets",
    "Equity Release"
]
lead_sources = ["Autochek App", "Dealer Referral", "Walk-in", "Website"]
banks = ["Access Bank", "GTBank", "UBA", "Zenith Bank"]
channels = [
    "Local Trade Finance",
    "Marketplace",
    "Cash Imports",
    "Repossessed Assets",
    "Equity Release"
]
dealers = [
    ("AutoKing Motors", "D001"),
    ("Prime Auto Ltd", "D002"),
    ("SpeedWheels", "D003"),
    ("Elite Cars", "D004"),
    ("DriveHub", "D005")
]
ams = [
    ("Regina Essien", "regina.essien@autochek.africa"),
    ("Samuel Schmidgall", "samuel.schmidgall@autochek.africa"),
    ("Solomon Annag-Johnson", "solomon.aj@autochek.africa")
]

data = []
for i in range(1, 51):  # Generate 50 mock records
    dealer_name, dealer_id = random.choice(dealers)
    am_name, am_email = random.choice(ams)
    record = {
        "transaction_id": f"T{i:03d}",
        "country": random.choice(countries),
        "fulfillment_date": (datetime.date(2025, 1, 1)
                             + datetime.timedelta(days=random.randint(0, 300))),
        "gmv_in_dollar": round(random.uniform(2000, 20000), 2),
        "Product_Classification": random.choice(product_classifications),
        "lead_source": random.choice(lead_sources),
        "Loan_ID": f"LN{i:04d}",
        "Financing_Bank": random.choice(banks),
        "Channel": random.choice(channels),
        "Dealer_Source_Name": dealer_name,
        "Dealer_Source_id": dealer_id,
        "Is_this_a_Reversal": random.choice(["No", "Yes"]),
        "sourcedata": am_email,
        "new_am": am_name
    }
    data.append(record)

df = pd.DataFrame(data)
df.to_csv("dealer_sales_mock.csv", index=False)
print("Mock dealer sales data generated successfully as dealer_sales_mock.csv!")
