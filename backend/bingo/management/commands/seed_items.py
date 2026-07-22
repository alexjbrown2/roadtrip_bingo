from django.core.management.base import BaseCommand

from bingo.models import Item

# Image filenames correspond to PNGs in frontend/public/assets/.
# Add more entries here as new images are dropped into that folder,
# then re-run this command (safe to re-run any time).
ITEMS = [
    {"text": "Cow", "image": "cow.png", "difficulty": "easy"},
    {"text": "Horse", "image": "horse.png", "difficulty": "easy"},
    {"text": "Barn", "image": "barn.png", "difficulty": "easy"},
    {"text": "Tree", "image": "tree.png", "difficulty": "easy"},
    {"text": "Cloud", "image": "cloud.png", "difficulty": "easy"},
    {"text": "Stop Sign", "image": "stopsign.png", "difficulty": "easy"},
    {"text": "Traffic Light", "image": "stoplight.png", "difficulty": "easy"},
    {"text": "Dump Truck", "image": "dumptruck.png", "difficulty": "easy"},
    {"text": "Yield Sign", "image": "yieldsign.png", "difficulty": "medium"},
    {"text": "Pedestrian Crossing Sign", "image": "pedestriansign.png", "difficulty": "medium"},
    {"text": "Fire Truck", "image": "firetruck.png", "difficulty": "hard"},
    {"text": "Airplane", "image": "plane.png", "difficulty": "hard"},
    {"text": "Dinosaur", "image": "dinosaur.png", "difficulty": "easy"},
    {"text": "Garbage Truck", "image": "garbagetruck.png", "difficulty": "easy"},
    {"text": "Red Car", "image": "redcar.png", "difficulty": "easy"},
    {"text": "Yellow Car", "image": "yellowcar.png", "difficulty": "easy"},
    {"text": "Moon", "image": "moon.png", "difficulty": "medium"},
    {"text": "Motorcycle", "image": "motorcycle.png", "difficulty": "medium"},
    {"text": "Police Car", "image": "policecar.png", "difficulty": "medium"},
    {"text": "Police Motorcycle", "image": "policemotorcycle.png", "difficulty": "medium"},
    {"text": "Sports Car", "image": "sportscar.png", "difficulty": "medium"},
    {"text": "Blue Car", "image": "bluecar.png", "difficulty": "hard"},
    {"text": "Cybertruck", "image": "cybertruck.png", "difficulty": "hard"},
    {"text": "Green Car", "image": "greencar.png", "difficulty": "hard"},
    {"text": "Cone", "image": "cone.png", "difficulty": "easy"},
    {"text": "Golf Course", "image": "golfcourse.png", "difficulty": "easy"},
    {"text": "Pond", "image": "pond.png", "difficulty": "easy"},
    {"text": "Speed Limit 65", "image": "speedlimit65.png", "difficulty": "easy"},
    {"text": "Water Tower", "image": "watertower.png", "difficulty": "easy"},
    {"text": "Wind Turbine", "image": "windturbine.png", "difficulty": "easy"},
    {"text": "Wooden Fence", "image": "woodenfence.png", "difficulty": "easy"},
    {"text": "Billboard", "image": "billboard.png", "difficulty": "medium"},
    {"text": "Broken Down Car", "image": "brokendowncar.png", "difficulty": "medium"},
    {"text": "Hay Bale", "image": "haybale.png", "difficulty": "medium"},
    {"text": "Mini Cooper", "image": "minicooper.png", "difficulty": "medium"},
    {"text": "Speed Limit 70", "image": "speedlimit70.png", "difficulty": "medium"},
    {"text": "Tow Truck", "image": "towtruck.png", "difficulty": "medium"},
    {"text": "Bicycle", "image": "bicycle.png", "difficulty": "hard"},
    {"text": "Bridge", "image": "bridge.png", "difficulty": "hard"},
    {"text": "Car Carrier", "image": "carcarrier.png", "difficulty": "hard"},
    {"text": "Graffiti", "image": "graffiti.png", "difficulty": "hard"},
    {"text": "Hotel", "image": "hotel.png", "difficulty": "hard"},
    {"text": "Luggage on Car", "image": "luggageoncar.png", "difficulty": "hard"},
    {"text": "Burger King", "image": "burgerking.png", "difficulty": "easy"},
    {"text": "Chick-fil-A", "image": "chickfila.png", "difficulty": "easy"},
    {"text": "Walmart", "image": "walmart.png", "difficulty": "easy"},
    {"text": "Sheetz", "image": "sheetz.png", "difficulty": "medium"},
    {"text": "Target", "image": "target.png", "difficulty": "medium"},
    {"text": "Visible Spare Tire", "image": "visiblesparetire.png", "difficulty": "medium"},
    {"text": "Arby's", "image": "arbys.png", "difficulty": "hard"},
    {"text": "McDonald's", "image": "mcdonalds.png", "difficulty": "hard"},
    {"text": "Wawa", "image": "wawa.png", "difficulty": "hard"},
]


class Command(BaseCommand):
    help = "Seed the database with the curated road-trip bingo items (image + difficulty)."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for entry in ITEMS:
            item, was_created = Item.objects.update_or_create(
                image_filename=entry["image"],
                defaults={"text": entry["text"], "difficulty": entry["difficulty"]},
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created} new item(s), updated {updated}; {len(ITEMS)} total in list."
            )
        )
