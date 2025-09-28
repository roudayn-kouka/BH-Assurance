"""
Tunisian names utility for generating realistic Tunisian names for individuals and companies.
"""

import random
from typing import Dict, Tuple


# Tunisian first names (male and female)
TUNISIAN_FIRST_NAMES_MALE = [
    "Mohamed", "Ahmed", "Ali", "Mehdi", "Amine", "Karim", "Omar", "Youssef", 
    "Ramzi", "Saif", "Nabil", "Rami", "Fares", "Sami", "Walid", "Tarek",
    "Malek", "Bilel", "Wissem", "Hatem", "Chadi", "Marwan", "Aymen", "Zied",
    "Khalil", "Farid", "Hedi", "Seif", "Ghazi", "Slim", "Adel", "Fadi",
    "Montassar", "Wassim", "Houssem", "Oussama", "Bassem", "Maher", "Chaker", "Sofien"
]

TUNISIAN_FIRST_NAMES_FEMALE = [
    "Fatma", "Aicha", "Salma", "Ines", "Nour", "Yasmine", "Rim", "Dorra",
    "Sonia", "Amina", "Leila", "Mariem", "Nesrine", "Sabrine", "Widad", "Emna",
    "Chiraz", "Hela", "Raoudha", "Mouna", "Jihene", "Samia", "Najet", "Olfa",
    "Azza", "Manel", "Khadija", "Sihem", "Farah", "Chaima", "Rania", "Donia",
    "Meriem", "Souad", "Lamia", "Raja", "Asma", "Hana", "Nadia", "Lilia"
]

# Tunisian family names
TUNISIAN_LAST_NAMES = [
    "Ben Ali", "Trabelsi", "Jemaa", "Hadj", "Karoui", "Bouzid", "Mejri", "Sassi",
    "Bouazizi", "Gharbi", "Kallel", "Ben Salah", "Chaibi", "Belkhiria", "Ouali", "Marzouk",
    "Ben Amor", "Jouini", "Khelil", "Brahem", "Chebbi", "Mzoughi", "Ben Youssef", "Rebhi",
    "Ghanmi", "Dridi", "Karray", "Hammami", "Ben Fredj", "Bouhali", "Chaabane", "Ben Abdallah",
    "Nouira", "Belaid", "Khemiri", "Bouslama", "Rezgui", "Hamdi", "Souissi", "Ayari",
    "Ben Othman", "Chouikha", "Talbi", "Bouraoui", "Mannai", "Skhiri", "Ben Hmida", "Jrad"
]

# Tunisian company names and types
TUNISIAN_COMPANY_TYPES = [
    "SARL", "SA", "SUARL", "SNC", "SCS", "Société", "Entreprise", "Ets"
]

TUNISIAN_BUSINESS_SECTORS = [
    "Technologie", "Commerce", "Services", "Construction", "Agriculture", "Tourisme",
    "Textile", "Agroalimentaire", "Transport", "Consulting", "Finance", "Médical"
]

TUNISIAN_BUSINESS_WORDS = [
    "Tunis", "Carthage", "Medina", "Sousse", "Sfax", "Bizerte", "Monastir", "Mahdia",
    "Développement", "Innovation", "Solutions", "Expertise", "Excellence", "Qualité",
    "Moderne", "Avenir", "Progress", "Elite", "Premier", "Suprême", "Royal", "Golden",
    "Mediterranean", "Maghreb", "Africa", "International", "Global", "Digital",
    "Tech", "Pro", "Plus", "Max", "Star", "Top", "Best", "New", "Future"
]

TUNISIAN_COMPANY_NAMES = [
    "Ooredoo Tunisie", "Tunisie Télécom", "STEG", "SONEDE", "Banque Centrale de Tunisie",
    "Banque de l'Habitat", "Amen Bank", "Attijari Bank", "Société Générale Tunisie",
    "Monoprix Tunisie", "Carrefour Tunisie", "Géant Tunisie", "Magasin Général",
    "Poulina Group", "Loukil Group", "SIMPAR", "Groupe Chakira", "SOTUMAG",
    "Tunisair", "Nouvelair", "Carthage Cement", "Les Ciments de Bizerte"
]


def generate_tunisian_individual_name() -> Dict[str, str]:
    """Generate a random Tunisian individual name with first and last name."""
    # Randomly choose male or female
    if random.choice([True, False]):
        first_name = random.choice(TUNISIAN_FIRST_NAMES_MALE)
    else:
        first_name = random.choice(TUNISIAN_FIRST_NAMES_FEMALE)
    
    last_name = random.choice(TUNISIAN_LAST_NAMES)
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}"
    }


def generate_tunisian_company_name() -> Dict[str, str]:
    """Generate a random Tunisian company name."""
    # 30% chance to use a real company name
    if random.random() < 0.3:
        company_name = random.choice(TUNISIAN_COMPANY_NAMES)
        company_type = ""  # Real companies already include type
    else:
        # Generate a synthetic company name
        sector = random.choice(TUNISIAN_BUSINESS_SECTORS)
        location_or_word = random.choice(TUNISIAN_BUSINESS_WORDS)
        company_type = random.choice(TUNISIAN_COMPANY_TYPES)
        
        # Various patterns for company names
        patterns = [
            f"{location_or_word} {sector}",
            f"{sector} {location_or_word}",
            f"{location_or_word} {random.choice(['Tech', 'Pro', 'Plus', 'Solutions'])}",
            f"{random.choice(['Société', 'Entreprise'])} {location_or_word}",
            f"{location_or_word} & {random.choice(['Associés', 'Partners', 'Fils'])}",
        ]
        
        base_name = random.choice(patterns)
        company_name = f"{base_name} {company_type}" if company_type not in ["Société", "Entreprise"] else base_name
    
    # Generate contact person name
    contact_person = generate_tunisian_individual_name()
    
    return {
        "company_name": company_name,
        "contact_person": contact_person["full_name"],
        "contact_first_name": contact_person["first_name"],
        "contact_last_name": contact_person["last_name"]
    }


def generate_tunisian_phone_number() -> str:
    """Generate a random Tunisian phone number."""
    # Tunisian mobile prefixes: 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99
    mobile_prefixes = [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99]
    prefix = random.choice(mobile_prefixes)
    number = f"{random.randint(100, 999)}{random.randint(100, 999)}"
    return f"+216 {prefix} {number[:3]} {number[3:]}"


def generate_tunisian_email(name_info: Dict[str, str], is_company: bool = False) -> str:
    """Generate a realistic Tunisian email address."""
    domains = [
        "gmail.com", "yahoo.fr", "hotmail.com", "outlook.com", "hotmail.fr",
        "tunisie.com", "topnet.tn", "planet.tn", "gnet.tn", "laposte.net"
    ]
    
    if is_company:
        # Company email
        company_name = name_info.get("company_name", "company")
        # Clean company name for email
        clean_name = company_name.lower().replace(" ", "").replace("&", "").replace("-", "")
        clean_name = "".join(c for c in clean_name if c.isalnum())[:15]  # Limit length
        
        email_patterns = [
            f"contact@{clean_name}.com.tn",
            f"info@{clean_name}.tn",
            f"admin@{clean_name}.com",
            f"{clean_name}@{random.choice(domains[:5])}",  # Use more professional domains
        ]
        return random.choice(email_patterns)
    else:
        # Individual email
        first_name = name_info.get("first_name", "user").lower()
        last_name = name_info.get("last_name", "user").lower().replace(" ", "")
        
        email_patterns = [
            f"{first_name}.{last_name}@{random.choice(domains)}",
            f"{first_name}{last_name}@{random.choice(domains)}",
            f"{first_name}_{last_name}@{random.choice(domains)}",
            f"{first_name}{random.randint(10, 99)}@{random.choice(domains)}",
            f"{last_name}.{first_name}@{random.choice(domains)}"
        ]
        return random.choice(email_patterns)


def generate_tunisian_fiscal_id(is_company: bool = False) -> str:
    """Generate a realistic Tunisian fiscal ID."""
    if is_company:
        # Tunisian company tax ID format: typically starts with letters followed by numbers
        prefixes = ["TN", "FR", "AR", "SF", "TU", "BZ", "MH", "SS", "KB", "JE"]
        prefix = random.choice(prefixes)
        numbers = f"{random.randint(10000000, 99999999)}{random.randint(100, 999)}"
        return f"{prefix}{numbers}"
    else:
        # Individual tax ID - simpler format
        return f"{random.randint(10000000, 19999999)}"


# Test function
if __name__ == "__main__":
    print("=== INDIVIDUAL NAMES ===")
    for _ in range(5):
        person = generate_tunisian_individual_name()
        email = generate_tunisian_email(person)
        phone = generate_tunisian_phone_number()
        fiscal_id = generate_tunisian_fiscal_id(False)
        print(f"Name: {person['full_name']}")
        print(f"Email: {email}")
        print(f"Phone: {phone}")
        print(f"Fiscal ID: {fiscal_id}")
        print()
    
    print("=== COMPANY NAMES ===")
    for _ in range(5):
        company = generate_tunisian_company_name()
        email = generate_tunisian_email(company, True)
        phone = generate_tunisian_phone_number()
        fiscal_id = generate_tunisian_fiscal_id(True)
        print(f"Company: {company['company_name']}")
        print(f"Contact: {company['contact_person']}")
        print(f"Email: {email}")
        print(f"Phone: {phone}")
        print(f"Fiscal ID: {fiscal_id}")
        print()
