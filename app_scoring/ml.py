# -*- coding: utf-8 -*-
"""
Validation scientifique du modele de risque (pur Python, sans dependance).

On genere des donnees SYNTHETIQUES etiquetees (decrochage oui/non) selon un
processus generatif inspire de la recherche ABC (l'absenteisme est le facteur
le plus predictif), puis on ENTRAINE une regression logistique par descente de
gradient. On evalue ensuite avec des metriques reelles : AUC, matrice de
confusion, precision/rappel/F1. Cela permet de comparer les poids APPRIS aux
poids fixes a la main (50/30/20) et de fournir des metriques reproductibles.
"""
import json
import math
import random
from pathlib import Path

METRICS_PATH = Path(__file__).resolve().parent / "model_metrics.json"


def _sigmoid(z):
    if z < -60:
        return 0.0
    if z > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def generate_dataset(n, seed=42):
    """Genere n eleves synthetiques + label decrochage (0/1)."""
    rng = random.Random(seed)
    X, y = [], []
    for _ in range(n):
        absences = rng.uniform(0, 100)
        grade_drop = rng.uniform(0, 20)
        disciplinary = rng.randint(0, 6)
        a = absences / 100.0
        g = grade_drop / 20.0
        d = min(disciplinary / 5.0, 1.0)
        # Processus generatif "verite terrain" : absences > notes > discipline + bruit
        logit = -3.2 + 4.6 * a + 2.4 * g + 1.4 * d + rng.gauss(0, 0.6)
        label = 1 if rng.random() < _sigmoid(logit) else 0
        X.append([a, g, d])
        y.append(label)
    return X, y


def _standardize(X):
    cols = list(zip(*X))
    means = [sum(c) / len(c) for c in cols]
    stds = []
    for c, m in zip(cols, means):
        var = sum((v - m) ** 2 for v in c) / len(c)
        stds.append(math.sqrt(var) or 1.0)
    Xs = [[(row[k] - means[k]) / stds[k] for k in range(len(row))] for row in X]
    return Xs, means, stds


def train_logistic(X, y, lr=0.3, epochs=3000):
    """Regression logistique par descente de gradient. w = [biais, w_abs, w_grade, w_disc]."""
    n, dim = len(X), len(X[0])
    w = [0.0] * (dim + 1)
    for _ in range(epochs):
        grads = [0.0] * (dim + 1)
        for xi, yi in zip(X, y):
            z = w[0] + sum(w[k + 1] * xi[k] for k in range(dim))
            err = _sigmoid(z) - yi
            grads[0] += err
            for k in range(dim):
                grads[k + 1] += err * xi[k]
        for j in range(dim + 1):
            w[j] -= lr * grads[j] / n
    return w


def _predict(w, xi):
    return _sigmoid(w[0] + sum(w[k + 1] * xi[k] for k in range(len(xi))))


def _auc(scores, labels):
    """AUC via la statistique de Mann-Whitney."""
    pos = [s for s, l in zip(scores, labels) if l == 1]
    neg = [s for s, l in zip(scores, labels) if l == 0]
    if not pos or not neg:
        return 0.5
    wins = 0.0
    for p in pos:
        for ng in neg:
            wins += 1.0 if p > ng else 0.5 if p == ng else 0.0
    return wins / (len(pos) * len(neg))


def evaluate_and_save(n=1200, seed=42):
    X, y = generate_dataset(n, seed)
    split = int(n * 0.75)
    Xtr, ytr = X[:split], y[:split]
    Xte, yte = X[split:], y[split:]

    Xtr_s, means, stds = _standardize(Xtr)
    w = train_logistic(Xtr_s, ytr)

    # Test (standardise avec les stats d'entrainement)
    Xte_s = [[(row[k] - means[k]) / stds[k] for k in range(len(row))] for row in Xte]
    scores = [_predict(w, xi) for xi in Xte_s]

    auc = _auc(scores, yte)

    # Matrice de confusion au seuil 0.5
    TP = FP = TN = FN = 0
    for s, l in zip(scores, yte):
        pred = 1 if s >= 0.5 else 0
        if pred == 1 and l == 1: TP += 1
        elif pred == 1 and l == 0: FP += 1
        elif pred == 0 and l == 0: TN += 1
        else: FN += 1
    acc = (TP + TN) / len(yte)
    precision = TP / (TP + FP) if (TP + FP) else 0.0
    recall = TP / (TP + FN) if (TP + FN) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    # Importance relative APPRISE (|coef standardise| normalise a 100)
    abs_coefs = [abs(w[1]), abs(w[2]), abs(w[3])]
    tot = sum(abs_coefs) or 1.0
    learned = [round(c / tot * 100) for c in abs_coefs]

    result = {
        "n_total": n, "n_train": len(ytr), "n_test": len(yte),
        "auc": round(auc, 3),
        "accuracy": round(acc, 3), "precision": round(precision, 3),
        "recall": round(recall, 3), "f1": round(f1, 3),
        "confusion": {"TP": TP, "FP": FP, "TN": TN, "FN": FN},
        "learned_importance": {"absences": learned[0], "grades": learned[1], "discipline": learned[2]},
        "configured_weights": {"absences": 50, "grades": 30, "discipline": 20},
        "threshold": 0.5,
    }
    METRICS_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def load_metrics():
    try:
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None
