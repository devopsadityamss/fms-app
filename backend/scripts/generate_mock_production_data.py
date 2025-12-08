import asyncio
import random
import uuid
from datetime import datetime, timedelta

from app.core.database import async_session_maker
from app.schemas.production import ProductionUnitCreate, StageCreate, TaskCreate, UnitOptionCreate
from app.crud.production import create_production_unit

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
NUM_UNITS = 5          # number of production units to create
STAGES_PER_UNIT = (3, 6)
TASKS_PER_STAGE = (2, 6)

PRACTICES = [
    ("crop", ["cereals", "vegetables", "pulses"]),
    ("dairy", ["cattle", "buffalo"]),
    ("plantation", ["fruit", "spices"]),
    ("vegetable", ["leafy", "root"]),
]

CROP_OPTIONS = ["rice", "wheat", "corn", "tomato", "potato", "onion"]
DAIRY_OPTIONS = ["cow", "buffalo"]
PLANTATION_OPTIONS = ["mango", "banana", "coconut"]
VEG_OPTIONS = ["spinach", "carrot", "cabbage"]


# ------------------------------------------------------------
# Generate stages and tasks
# ------------------------------------------------------------
def generate_stages():
    stages = []
    stage_count = random.randint(*STAGES_PER_UNIT)

    for i in range(stage_count):
        task_count = random.randint(*TASKS_PER_STAGE)
        tasks = []

        for t in range(task_count):
            completed_flag = random.random() < 0.6  # 60% tasks completed
            tasks.append(
                TaskCreate(
                    title=f"Task {t+1}",
                    order=t+1,
                    completed=completed_flag,
                    priority=random.choice(["low", "medium", "high"]),
                    due_date=datetime.utcnow() + timedelta(days=random.randint(1, 15)),
                )
            )

        stages.append(
            StageCreate(
                title=f"Stage {i+1}",
                order=i+1,
                tasks=tasks
            )
        )

    return stages


# ------------------------------------------------------------
# Select items based on farming practice
# ------------------------------------------------------------
def generate_items(practice, category):
    if practice == "crop":
        return [UnitOptionCreate(option_name=random.choice(CROP_OPTIONS))]
    if practice == "dairy":
        return [UnitOptionCreate(option_name=random.choice(DAIRY_OPTIONS))]
    if practice == "plantation":
        return [UnitOptionCreate(option_name=random.choice(PLANTATION_OPTIONS))]
    if practice == "vegetable":
        return [UnitOptionCreate(option_name=random.choice(VEG_OPTIONS))]

    return []


# ------------------------------------------------------------
# Main generator
# ------------------------------------------------------------
async def generate_mock_data(user_id: str):
    async with async_session_maker() as db:
        for i in range(NUM_UNITS):
            practice, categories = random.choice(PRACTICES)
            category = random.choice(categories)

            items = generate_items(practice, category)

            payload = ProductionUnitCreate(
                name=f"Demo Unit {i+1}",
                practice_type=practice,
                category=category,
                stages=generate_stages(),
                options=items,
                meta={"generated": True}
            )

            unit = await create_production_unit(user_id, payload, db)
            print(f"✅ Created unit {unit.id} ({unit.name})")


# ------------------------------------------------------------
# Script Entrypoint
# ------------------------------------------------------------
if __name__ == "__main__":
    print("\n=== MOCK PRODUCTION DATA GENERATOR ===")

    user_id = input("Enter Farmer User ID (UUID): ").strip()
    try:
        uuid.UUID(user_id)
    except:
        print("❌ Invalid UUID")
        exit(1)

    asyncio.run(generate_mock_data(user_id))
    print("\n🎉 Done! Mock data inserted successfully.\n")
