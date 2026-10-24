"""Give a category to products whose source does not send one (Lazada, Shopee).

Every statistic is computed inside one category, so imported products need a
category too. Tiki products of the same search already have one, so they are
the training data of a small text classifier:

    product name -> TF-IDF of character n-grams -> logistic regression -> category

Character n-grams cope with spelling variants ("tai nghe", "tainghe", "TWS").
Only confident predictions are kept; the rest stay "Chưa phân loại".
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline

from analysis.cleaning import UNKNOWN_CATEGORY, normalize_text

MIN_EXAMPLES = 3       # a category needs at least 3 labelled products to be learned
MIN_CONFIDENCE = 0.5   # below this probability the category stays unknown


def train(labelled):
    """Train on products with a known category.

    Returns (model, cross-validated accuracy), or (None, None) when there are
    fewer than two categories with enough examples.
    """
    counts = labelled["category"].value_counts()
    labelled = labelled[labelled["category"].isin(counts[counts >= MIN_EXAMPLES].index)]
    if labelled["category"].nunique() < 2:
        return None, None

    names = labelled["name"].map(normalize_text)
    model = make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4)),
        LogisticRegression(max_iter=1000),
    )
    folds = min(5, labelled["category"].value_counts().min())
    accuracy = cross_val_score(model, names, labelled["category"], cv=folds).mean()
    model.fit(names, labelled["category"])
    return model, accuracy


def predict(model, names):
    """Most likely category of each name, or UNKNOWN_CATEGORY when unsure."""
    probabilities = model.predict_proba(names.map(normalize_text))
    best = model.classes_[probabilities.argmax(axis=1)]
    return np.where(probabilities.max(axis=1) >= MIN_CONFIDENCE, best, UNKNOWN_CATEGORY)
