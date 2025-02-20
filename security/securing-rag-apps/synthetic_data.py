import json
import random
from pathlib import Path

import click
from faker import Faker
from rich.console import Console
from rich.panel import Panel


class SyntheticTextGenerator:
    def __init__(self, seed=42):
        self.fake = Faker()
        Faker.seed(seed)
        random.seed(seed)

        # Approved test data
        self.test_names = [
            "Alejandro Rosalez",
            "Ana Carolina Silva",
            "Arnav Desai",
            "Carlos Salazar",
            "Diego Ramirez",
            "Jane Doe",
            "Jane Roe",
            "John Doe",
            "John Stiles",
            "Jorge Souza",
            "Li Juan",
            "Liu Jie",
            "Márcia Oliveira",
            "María García",
            "Martha Rivera",
            "Mary Major",
            "Mateo Jackson",
            "Nikhil Jayashankar",
            "Paulo Santos",
            "Richard Roe",
            "Saanvi Sarkar",
            "Shirley Rodriguez",
            "Sofía Martínez",
            "Wang Xiulan",
            "Zhang Wei",
        ]

        self.test_emails = [
            "alejandro@example.com",
            "ana@example.com",
            "arnav@example.com",
            "carlos@example.com",
            "diego@example.com",
            "jane@example.com",
            "john@example.com",
            "jorge@example.com",
            "li@example.com",
            "liu@example.com",
            "marcia@example.com",
            "maria@example.com",
            "martha@example.com",
            "mary@example.com",
            "mateo@example.com",
            "nikhil@example.com",
            "paulo@example.com",
            "richard@example.com",
            "saanvi@example.com",
            "shirley@example.com",
            "sofia@example.com",
            "wang@example.com",
            "zhang@example.com",
        ]

        # Generate compliant phone numbers
        self.phone_numbers = [f"(206) 555-{str(i).zfill(4)}" for i in range(100, 200)]

        # Test credit card
        self.test_credit_card = {
            "number": "1234-5678-1234-5678",
            "cvv": "123",
            "exp": f"{random.randint(1, 12)}/{random.randint(2024, 2030)}",
        }

        # Medical conditions library
        self.conditions = [
            "Hypertension",
            "Type 2 Diabetes",
            "Asthma",
            "Osteoarthritis",
            "Major Depressive Disorder",
            "Generalized Anxiety Disorder",
            "Hyperlipidemia",
            "GERD",
            "Obesity",
            "Sleep Apnea",
            "Hypothyroidism",
            "Chronic Migraine",
            "Fibromyalgia",
            "Coronary Artery Disease",
            "Chronic Kidney Disease",
        ]

        # Medications library
        self.medications = [
            "Lisinopril",
            "Metformin",
            "Sertraline",
            "Levothyroxine",
            "Omeprazole",
            "Atorvastatin",
            "Amlodipine",
            "Metoprolol",
            "Gabapentin",
            "Hydrochlorothiazide",
            "Furosemide",
            "Escitalopram",
            "Albuterol",
            "Fluticasone",
            "Pantoprazole",
        ]

        # Templates for various sections
        self.chief_complaints = [
            "chronic lower back pain",
            "recurring headaches",
            "difficulty sleeping",
            "chest discomfort",
            "anxiety and depression",
            "shortness of breath",
            "joint pain",
            "digestive issues",
        ]

        self.medical_history_templates = [
            "Patient has a history of {condition1} diagnosed in {year1}. "
            + "Previously treated for {condition2} in {year2}. "
            + "Family history significant for {family_condition}.",
            "No significant past medical history until {year1} when diagnosed with {condition1}. "
            + "Developed {condition2} in {year2}. "
            + "Currently managing both conditions with medication.",
            "Complex medical history including {condition1} ({year1}), {condition2} ({year2}), "
            + "and ongoing management of {condition3}.",
        ]

        self.financial_record_templates = [
            "Client meeting summary for {date}: Discussed retirement planning with {name} (SSN: {ssn}). "
            + "Current portfolio value: ${portfolio_value}. Primary concerns include college funding for children "
            + "and mortgage refinancing. Contact: {phone}, {email}. Home address: {address}.",
            "Loan application review - {date}: Applicant {name} (DOB: {dob}, SSN: {ssn}) "
            + "seeking ${loan_amount} home equity loan. Current property address: {address}. "
            + "Annual income: ${income}. Credit score: {credit_score}.",
            "Investment advisory notes - {date}: Client {name} (Account #{account_number}) "
            + "requested portfolio reallocation. Contact info: {phone}, {email}. "
            + "Current balance: ${portfolio_value}. Discussed tax implications of proposed changes.",
        ]

        self.medication_templates = [
            "{drug_name} {dose} {frequency}",
            "{drug_name} {dose} taken {frequency} for {condition}",
            "{drug_name} {frequency}, last renewed on {date}",
        ]

    def get_random_condition(self):
        return random.choice(self.conditions)

    def get_random_medication(self):
        return random.choice(self.medications)

    def get_random_person(self):
        """Get a random person's information from the test data"""
        name = random.choice(self.test_names)
        email = random.choice(self.test_emails)
        phone = random.choice(self.phone_numbers)
        return {"name": name, "email": email, "phone": phone}

    def generate_medical_note(self):
        person = self.get_random_person()
        patient = {
            "name": person["name"],
            "dob": self.fake.date_of_birth(minimum_age=18, maximum_age=90).strftime(
                "%m/%d/%Y"
            ),
            "mrn": f"MRN-{self.fake.random_number(digits=8, fix_len=True)}",
            "ssn": f"XXX-XX-{random.randint(1000, 9999)}",  # Partially masked SSN
            "phone": person["phone"],
            "email": person["email"],
            "address": f"{self.fake.street_address()}, {self.fake.city()}, {self.fake.state_abbr()} {self.fake.zipcode()}",
        }

        note = f"""
MEDICAL NOTE
Date: {self.fake.date_between(start_date="-1y", end_date="today").strftime("%m/%d/%Y")}
Provider: Dr. {self.get_random_person()["name"]}
Institution: {self.fake.company()} Medical Center

PATIENT INFORMATION
Name: {patient["name"]}
DOB: {patient["dob"]}
MRN: {patient["mrn"]}
SSN: {patient["ssn"]}
Contact: {patient["phone"]}, {patient["email"]}
Address: {patient["address"]}

CHIEF COMPLAINT
Patient presents with {random.choice(self.chief_complaints)}.

HISTORY OF PRESENT ILLNESS
{self._generate_present_illness()}

PAST MEDICAL HISTORY
{
            random.choice(self.medical_history_templates).format(
                condition1=random.choice(self.conditions),
                condition2=random.choice(self.conditions),
                condition3=random.choice(self.conditions),
                family_condition=random.choice(self.conditions),
                year1=str(random.randint(1990, 2020)),
                year2=str(random.randint(1990, 2020)),
            )
        }

CURRENT MEDICATIONS
{self._generate_medications()}

ASSESSMENT AND PLAN
{self._generate_assessment_plan()}
"""
        return note, patient

    def generate_financial_record(self):
        person = self.get_random_person()
        client = {
            "name": person["name"],
            "dob": self.fake.date_of_birth(minimum_age=25, maximum_age=75).strftime(
                "%m/%d/%Y"
            ),
            "ssn": f"XXX-XX-{random.randint(1000, 9999)}",  # Partially masked SSN
            "phone": person["phone"],
            "email": person["email"],
            "address": f"{self.fake.street_address()}, {self.fake.city()}, {self.fake.state_abbr()} {self.fake.zipcode()}",
            "account_number": f"ACC-{self.fake.random_number(digits=8, fix_len=True)}",
            "credit_card": self.test_credit_card,
        }

        record = random.choice(self.financial_record_templates).format(
            date=self.fake.date_between(start_date="-6m", end_date="today").strftime(
                "%m/%d/%Y"
            ),
            name=client["name"],
            ssn=client["ssn"],
            phone=client["phone"],
            email=client["email"],
            address=client["address"],
            portfolio_value=f"{random.randint(100000, 2000000):,}",
            loan_amount=f"{random.randint(50000, 500000):,}",
            income=f"{random.randint(60000, 250000):,}",
            credit_score=random.randint(620, 850),
            account_number=client["account_number"],
            dob=client["dob"],
        )

        return record, client

    def _generate_present_illness(self):
        return (
            f"Patient reports {self.fake.sentence(nb_words=20)} "
            + f"Symptoms began {random.choice(['approximately', 'about'])} "
            + f"{random.choice(['one week ago', 'two weeks ago', 'a month ago', 'three months ago'])}. "
            + f"{self.fake.sentence(nb_words=15)}"
        )

    def _generate_medications(self):
        medications = []
        for _ in range(random.randint(2, 5)):
            template = random.choice(self.medication_templates)
            medications.append(
                template.format(
                    drug_name=self.get_random_medication(),
                    dose=f"{random.choice(['50mg', '100mg', '200mg', '500mg'])}",
                    frequency=random.choice(
                        ["daily", "twice daily", "three times daily", "as needed"]
                    ),
                    condition=self.get_random_condition(),
                    date=self.fake.date_between(
                        start_date="-6m", end_date="today"
                    ).strftime("%m/%d/%Y"),
                )
            )
        return "\n".join([f"- {med}" for med in medications])

    def _generate_assessment_plan(self):
        return (
            f"ASSESSMENT:\n{self.fake.sentence(nb_words=20)}\n\n"
            + f"PLAN:\n1. {self.fake.sentence(nb_words=10)}\n"
            + f"2. {self.fake.sentence(nb_words=10)}\n"
            + f"3. Follow up in {random.choice(['1 week', '2 weeks', '1 month', '3 months'])}"
        )


def generate_dataset(num_records=10, seed=42):
    """Generate a dataset of synthetic medical notes and financial records"""
    generator = SyntheticTextGenerator(seed=seed)

    dataset = {"medical_notes": [], "financial_records": []}

    for _ in range(num_records):
        # Generate medical note
        note, patient = generator.generate_medical_note()
        dataset["medical_notes"].append({"text": note, "metadata": patient})

        # Generate financial record
        record, client = generator.generate_financial_record()
        dataset["financial_records"].append({"text": record, "metadata": client})

    return dataset


def save_dataset(dataset, filename_prefix="synthetic_dataset"):
    """Save the dataset to JSON and text files"""
    TARGET_DIR = Path("data")
    TARGET_DIR.mkdir(exist_ok=True)

    # Save complete dataset with metadata
    json_filename = TARGET_DIR.joinpath(f"{filename_prefix}.json")
    with open(json_filename, "w") as f:
        json.dump(dataset, f, indent=2)

    # Save just the medical notes as text
    MED_DIR = TARGET_DIR.joinpath("medical")
    if not MED_DIR.exists():
        MED_DIR.mkdir(exist_ok=True)
    # text_filename = MED_DIR.joinpath(f"{filename_prefix}_medical_notes.txt")

    for idx, item in enumerate(dataset["medical_notes"]):
        text_filename = MED_DIR.joinpath(f"pii_medical_{idx}.txt")
        _ = text_filename.write_text(item["text"], encoding="utf-8")

    # Save just the financial records as text
    FIN_DIR = TARGET_DIR.joinpath("financial")
    if not FIN_DIR.exists():
        FIN_DIR.mkdir(exist_ok=True)

    for idx, item in enumerate(dataset["financial_records"]):
        text_filename = FIN_DIR.joinpath(f"pii_financial_{idx}.txt")
        _ = text_filename.write_text(item["text"], encoding="utf-8")


@click.group()
@click.option("--seed", default=42, help="Random seed for reproducibility")
@click.pass_context
def cli(ctx, seed):
    """Synthetic Data Generator for Medical and Financial Records

    This tool generates synthetic medical notes and financial records for testing purposes.
    All data is artificially created and any resemblance to real persons is coincidental.
    """
    ctx.ensure_object(dict)
    ctx.obj["seed"] = seed
    ctx.obj["console"] = Console()


@cli.command()
@click.option("--count", "-n", default=10, help="Number of records to generate")
@click.option(
    "--output-prefix", "-o", default="synthetic_dataset", help="Prefix for output files"
)
@click.option(
    "--preview/--no-preview", default=False, help="Preview generated records in console"
)
@click.pass_context
def generate(ctx, count, output_prefix, preview):
    """Generate synthetic medical and financial records"""
    dataset = generate_dataset(num_records=count, seed=ctx.obj["seed"])
    save_dataset(dataset, filename_prefix=output_prefix)
    console = ctx.obj["console"]

    if preview:
        console.print(Panel.fit("Example Medical Note", style="blue"))
        console.print(dataset["medical_notes"][0]["text"])
        console.print("\n")
        console.print(Panel.fit("Example Financial Record", style="green"))
        console.print(dataset["financial_records"][0]["text"])

    console.print(f"\n[green]Successfully generated {count} records!")
    console.print("Data files saved in data/ folder.")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.pass_context
def view(ctx, file_path):
    """View contents of a previously generated dataset"""
    with open(file_path, "r") as f:
        data = json.load(f)

    console = ctx.obj["console"]
    console.print("Dataset contains:")
    console.print(f"- {len(data['medical_notes'])} medical notes")
    console.print(f"- {len(data['financial_records'])} financial records")

    if click.confirm("Would you like to see a sample?"):
        console.print(Panel.fit("Sample Medical Note", style="blue"))
        console.print(data["medical_notes"][0]["text"])
        console.print("\n")
        console.print(Panel.fit("Sample Financial Record", style="green"))
        console.print(data["financial_records"][0]["text"])


if __name__ == "__main__":
    cli(obj={})
