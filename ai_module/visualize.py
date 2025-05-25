import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_curve,
    auc,
)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _score_for_roc(model, X):
    """
    Return a 1-D array of scores suitable for roc_curve().
    Works with models that implement either predict_proba() or decision_function().
    """
    if hasattr(model, "predict_proba"):
        # probability of the positive class
        return model.predict_proba(X)[:, 1]
    elif hasattr(model, "decision_function"):
        return model.decision_function(X)
    else:  # fall back to hard labels (rare)
        return model.predict(X)


# ──────────────────────────────────────────────
# Individual plots
# ──────────────────────────────────────────────
def plot_classification_report(y_true, y_pred, file_path):
    report_df = pd.DataFrame(
        classification_report(y_true, y_pred, output_dict=True)
    ).transpose()

    plt.figure(figsize=(10, 6))
    sns.heatmap(
        report_df.iloc[:-1, :-1],
        annot=True,
        cmap="Blues",
        fmt=".2f",
        cbar=False,
    )
    plt.title("Classification Report")
    plt.ylabel("Classes")
    plt.xlabel("Metrics")
    plt.tight_layout()
    plt.savefig(file_path, dpi=300)
    plt.close()


def plot_confusion_matrix(y_true, y_pred, file_path):
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Negative", "Positive"],
        yticklabels=["Negative", "Positive"],
    )
    plt.title("Confusion Matrix")
    plt.ylabel("True label")
    plt.xlabel("Predicted label")
    plt.tight_layout()
    plt.savefig(file_path, dpi=300)
    plt.close()


def plot_roc_auc(y_true, y_scores, file_path):
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)

    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, lw=2, label=f"ROC curve (AUC = {roc_auc:.2f})")
    plt.plot([0, 1], [0, 1], linestyle="--", lw=2)
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Receiver-Operating-Characteristic")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(file_path, dpi=300)
    plt.close()


# ──────────────────────────────────────────────
# Public entry-point
# ──────────────────────────────────────────────
def generate_visualizations(model, X_test, y_test, output_dir="/plots"):
    """
    Create classification report, confusion matrix and (if binary) ROC-AUC plots.

    Parameters
    ----------
    model : fitted scikit-learn estimator
    X_test : array-like, shape (n_samples, n_features)
    y_test : array-like, shape (n_samples,)
    output_dir : str, default "models_trained/plots"
    """
    os.makedirs(output_dir, exist_ok=True)

    # Predictions
    y_pred = model.predict(X_test)

    # 1. Classification report
    plot_classification_report(
        y_test, y_pred, os.path.join(output_dir, "classification_report.png")
    )

    # 2. Confusion matrix
    plot_confusion_matrix(
        y_test, y_pred, os.path.join(output_dir, "confusion_matrix.png")
    )

    # 3. ROC-AUC (only for binary problems)
    if len(np.unique(y_test)) == 2:
        y_scores = _score_for_roc(model, X_test)
        plot_roc_auc(
            y_test, y_scores, os.path.join(output_dir, "roc_auc_curve.png")
        )

    print(f"✅  All visualizations saved in “{output_dir}”.")