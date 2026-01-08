"""
Seed script to populate canonical C1/C2 taxonomy
"""
from datetime import datetime, timedelta
import random
from sqlmodel import Session, select
from backend.models import Category1, Category2, Expense
from backend.database import engine


# Canonical taxonomy
TAXONOMY = {
    "Food": ["Eat Outside", "Groceries", "Office Food", "Snacks", "Beverages"],
    "Transport": ["Scooty Petrol", "Maintenance", "Parking", "Cab/Auto", "Public Transport"],
    "Health & Fitness": ["Gym Membership", "Trainer", "Protein Powder", "Supplements", "Skincare", "Doctor/Medical"],
    "Education & Career": ["Courses", "ChatGPT/AI Tools", "Books", "Certifications", "Workshops"],
    "Home & Living": ["Cooking Supplies", "Utilities", "Rent", "Maintenance", "Household Items"],
    "Family & Relationships": ["Parents Support", "Medical for Family", "Gifts", "Festivals", "Occasions"],
    "Lifestyle": ["Shopping", "Entertainment", "Cafes", "Hobbies", "Self-care"],
    "Subscriptions & Tools": ["Streaming", "Cloud Services", "Software", "Productivity Apps"],
    "Travel": ["Transport", "Stay", "Food (Travel)", "Local Travel", "Activities"],
    "Miscellaneous": ["One-off Expenses", "Unplanned", "Unknown"]
}


def seed_database():
    """
    Seed the database with canonical taxonomy and sample expenses
    Idempotent - won't duplicate if already seeded
    """
    with Session(engine) as session:
        # Check if already seeded
        existing_c1 = session.exec(select(Category1)).first()
        if existing_c1:
            print("Database already seeded. Skipping...")
            return {"message": "Database already seeded", "status": "skipped"}
        
        print("Seeding database with canonical taxonomy...")
        
        # Create C1 and C2 categories
        c1_map = {}
        c2_list = []
        
        for c1_name, c2_names in TAXONOMY.items():
            c1 = Category1(name=c1_name, active=True)
            session.add(c1)
            session.commit()
            session.refresh(c1)
            c1_map[c1_name] = c1
            
            for c2_name in c2_names:
                c2 = Category2(name=c2_name, c1_id=c1.id, active=True)
                session.add(c2)
                c2_list.append((c1.id, c2))
            
            session.commit()
        
        print(f"Created {len(c1_map)} C1 categories and {len(c2_list)} C2 subcategories")
        
        # Create sample expenses for the last 3 months
        print("Creating sample expenses...")
        sample_expenses = []
        payment_modes = ["Cash", "Card", "UPI", "Net Banking"]
        need_vs_want = ["Need", "Want", "Neutral"]
        
        # Generate 50 sample expenses
        for i in range(50):
            days_ago = random.randint(0, 90)
            expense_date = datetime.utcnow() - timedelta(days=days_ago)
            
            # Pick random C1 and then random C2 under it
            c1_name = random.choice(list(TAXONOMY.keys()))
            c1 = c1_map[c1_name]
            c2_names = TAXONOMY[c1_name]
            c2_name = random.choice(c2_names)
            
            # Find the C2 object
            c2 = session.exec(
                select(Category2).where(
                    Category2.name == c2_name,
                    Category2.c1_id == c1.id
                )
            ).first()
            
            amount = round(random.uniform(50, 5000), 2)
            
            expense = Expense(
                date=expense_date,
                amount=amount,
                c1_id=c1.id,
                c2_id=c2.id,
                payment_mode=random.choice(payment_modes),
                notes=f"Sample expense {i+1}",
                person=random.choice(["Self", "Family", None]),
                need_vs_want=random.choice(need_vs_want),
                deleted=False
            )
            sample_expenses.append(expense)
            session.add(expense)
        
        session.commit()
        print(f"Created {len(sample_expenses)} sample expenses")
        
        return {
            "message": "Database seeded successfully",
            "status": "success",
            "c1_count": len(c1_map),
            "c2_count": len(c2_list),
            "sample_expenses": len(sample_expenses)
        }


if __name__ == "__main__":
    from backend.database import create_db_and_tables
    create_db_and_tables()
    result = seed_database()
    print(result)

