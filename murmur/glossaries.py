"""Optional vocabulary packs. They bias recognition and fix the spelling/casing afterwards."""

DE_TAX = [
    "DATEV", "ELSTER", "ELStAM", "Steuerberater", "Steuerberaterin", "Steuerberatungskanzlei", "Mandant", "Mandantin",
    "Mandanten", "Kanzlei", "Vollmacht", "Steuerbescheid", "Einspruch", "Einspruchsfrist", "Fristverlängerung",
    "Betriebsprüfung", "Außenprüfung", "Steuererklärung", "Feststellungserklärung", "Umsatzsteuer",
    "Umsatzsteuervoranmeldung", "Umsatzsteuer-Identifikationsnummer", "Vorsteuer", "Vorsteuerabzug",
    "Einkommensteuer", "Körperschaftsteuer", "Gewerbesteuer", "Lohnsteuer", "Kapitalertragsteuer",
    "Grunderwerbsteuer", "Grundsteuer", "Erbschaftsteuer", "Schenkungsteuer", "Kirchensteuer",
    "Solidaritätszuschlag", "Steuernummer", "Steuerfestsetzung", "Vorauszahlung", "Nachzahlung", "Erstattung",
    "Säumniszuschlag", "Verspätungszuschlag", "Abgabenordnung", "Finanzamt", "Finanzgericht", "Bundesfinanzhof",
    "BFH", "BMF", "BMF-Schreiben", "EStG", "KStG", "UStG", "GewStG", "HGB", "BilMoG", "GoBD", "E-Rechnung",
    "XRechnung", "ZUGFeRD", "Kleinunternehmerregelung", "Reverse-Charge", "innergemeinschaftliche Lieferung",
    "Bilanz", "Jahresabschluss", "Gewinn- und Verlustrechnung", "Einnahmenüberschussrechnung", "Abschreibung",
    "AfA", "Sonderabschreibung", "Anlagevermögen", "Umlaufvermögen", "Rückstellung",
    "Rechnungsabgrenzungsposten", "Betriebsvermögen", "Privatvermögen", "Betriebsausgaben", "Werbungskosten",
    "Sonderausgaben", "außergewöhnliche Belastungen", "Gesellschafter", "Gesellschafterversammlung",
    "Gesellschafter-Geschäftsführer", "Gewinnausschüttung", "verdeckte Gewinnausschüttung", "Organschaft",
    "Entnahme", "Einlage", "GmbH", "UG", "GbR", "OHG", "KG", "Wirtschaftsprüfer", "Lohnabrechnung",
    "Sozialversicherung", "Minijob", "Kassenführung", "Buchführung", "Buchhaltung", "Kontenrahmen", "SKR03",
    "SKR04", "Einheitswert", "Betriebsstätte", "Verrechnungspreise", "Umwandlung", "Verschmelzung",
]

# Words that are also ordinary words/units in lower case: never "fix" their casing.
AMBIGUOUS = {"KG", "UG", "AO", "FG"}


def pack_terms(cfg):
    return list(DE_TAX) if cfg["glossary_tax"] else []


def prompt_terms(cfg):
    """User terms first, then the pack (the recognition prompt is short, so order matters)."""
    seen, out = set(), []
    for t in list(cfg["terms"]) + pack_terms(cfg):
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def casing_terms(cfg):
    return [t for t in prompt_terms(cfg) if t not in AMBIGUOUS]
