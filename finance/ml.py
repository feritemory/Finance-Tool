"""Lokaler, offline lernender Klassifikator für die Ausgaben-Kategorisierung.

Der Klassifikator ergänzt die Stichwort-Regeln: Er lernt aus den bereits
(per Regel oder manuell) kategorisierten Ausgaben und verallgemeinert auf neue,
ähnliche Buchungstexte. So sinkt der Anteil "Sonstiges" mit der Zeit von selbst.

Technik: TF-IDF über Wort- UND Zeichen-n-Gramme (robust gegen deutsche
Komposita und den verrauschten Banktext) + logistische Regression. Das Modell
wird lokal unter data/model.pkl gespeichert. scikit-learn ist optional – ohne
das Paket bleibt einfach die Regel-Kategorisierung aktiv.
"""

from __future__ import annotations

import os
import re

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "model.pkl"
)

# Ab dieser Wahrscheinlichkeit wird eine ML-Vorhersage übernommen.
DEFAULT_THRESHOLD = 0.60
# Mindestanzahl an Trainingsbeispielen, damit sich Training lohnt.
MIN_SAMPLES = 25


def sklearn_available() -> bool:
    try:
        import sklearn  # noqa: F401
        import joblib    # noqa: F401
        return True
    except ImportError:
        return False


def make_text(counterparty: str, description: str = "", booking_text: str = "") -> str:
    """Baut den Eingabetext für das Modell aus den Bankfeldern."""
    s = " ".join(p for p in (counterparty, description, booking_text) if p).lower()
    s = re.sub(r"\d{3,}", " ", s)              # lange Ziffernfolgen (Referenzen) raus
    s = re.sub(r"\d{1,2}[.,]\d{2}", " ", s)    # Beträge/Datumsreste
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _build_pipeline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline

    features = FeatureUnion([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2),
                                 min_df=1, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                 min_df=1, sublinear_tf=True)),
    ])
    clf = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced")
    return Pipeline([("features", features), ("clf", clf)])


def train(samples: list[tuple[str, str, float]]) -> dict:
    """Trainiert das Modell.

    ``samples``: Liste aus (text, kategorie, gewicht). Rückgabe: Metriken.
    Wirft RuntimeError, wenn scikit-learn fehlt oder zu wenige Daten vorliegen.
    """
    if not sklearn_available():
        raise RuntimeError(
            "scikit-learn ist nicht installiert. Bitte einmalig ausführen:\n"
            "    pip install scikit-learn"
        )
    import joblib

    samples = [s for s in samples if s[0].strip()]
    texts = [s[0] for s in samples]
    labels = [s[1] for s in samples]
    weights = [s[2] for s in samples]

    n = len(texts)
    classes = sorted(set(labels))
    if n < MIN_SAMPLES or len(classes) < 2:
        raise RuntimeError(
            f"Zu wenige Trainingsdaten ({n} Beispiele, {len(classes)} Kategorien). "
            "Kategorisiere zuerst mehr Buchungen (Regeln + manuelle Korrekturen), "
            "dann lässt sich das Modell sinnvoll trainieren."
        )

    pipe = _build_pipeline()

    # Genauigkeit per Kreuzvalidierung schätzen (nur wenn genügend Daten je Klasse).
    accuracy = None
    from collections import Counter
    per_class = Counter(labels)
    if min(per_class.values()) >= 3 and n >= 40:
        try:
            from sklearn.model_selection import cross_val_score
            k = min(5, min(per_class.values()))
            scores = cross_val_score(pipe, texts, labels, cv=k)
            accuracy = float(scores.mean())
        except Exception:  # noqa: BLE001
            accuracy = None

    pipe.fit(texts, labels, clf__sample_weight=weights)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(pipe, MODEL_PATH)

    return {
        "n_samples": n,
        "n_classes": len(classes),
        "classes": classes,
        "accuracy": accuracy,
    }


def load_model():
    """Lädt das trainierte Modell oder gibt None zurück (kein Modell / kein sklearn)."""
    if not os.path.exists(MODEL_PATH) or not sklearn_available():
        return None
    try:
        import joblib
        return joblib.load(MODEL_PATH)
    except Exception:  # noqa: BLE001
        return None


def predict(model, text: str) -> tuple[str, float]:
    """Liefert (kategorie, wahrscheinlichkeit) für einen Text."""
    if not text.strip():
        return "", 0.0
    proba = model.predict_proba([text])[0]
    idx = int(proba.argmax())
    return str(model.classes_[idx]), float(proba[idx])


def model_exists() -> bool:
    return os.path.exists(MODEL_PATH)


def delete_model() -> None:
    if os.path.exists(MODEL_PATH):
        os.remove(MODEL_PATH)
