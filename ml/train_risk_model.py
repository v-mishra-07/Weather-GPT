"""
train_risk_model.py - Synthetic Dataset Generator & Random Forest Model Trainer for WeatherGPT

================================================================================
CRITICAL DISCLAIMER:
This model is trained exclusively on SYNTHETIC METEOROLOGICAL DATA designed for
prototyping, hackathon demonstrations (SIH26068), and API architecture validation.
It is NOT a certified, clinically or scientifically validated numerical weather
prediction or disaster management model. In real weather emergencies, always consult
official meteorological authorities (such as the IMD / NDMA).
================================================================================

Features (9 features in strict positional order expected by predict_service.py):
1. temperature       (float, Celsius)
2. humidity          (float, Relative Humidity percentage, 0-100)
3. rainfall_mm       (float, Recent rainfall amount in mm)
4. wind_speed_kmh    (float, Wind speed in km/h)
5. rain_probability  (float, Precipitation probability percentage, 0-100)
6. cloud_cover       (float, Cloud cover percentage, 0-100)
7. visibility_km     (float, Visibility range in km)
8. precipitation_mm  (float, Total precipitation in mm)
9. uv_index          (float, Ultraviolet radiation index)

Target Classes:
- 0 = Low Risk    (Fair, dry, mild winds, good visibility)
- 1 = Medium Risk (Overcast, rain showers, moderate wind, reduced visibility)
- 2 = High Risk   (Heavy downpour, high winds, near-zero visibility, storm conditions)
"""

import os
import pathlib
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Ensure reproducibility
RANDOM_STATE = 42

FEATURE_NAMES = [
    "temperature",
    "humidity",
    "rainfall_mm",
    "wind_speed_kmh",
    "rain_probability",
    "cloud_cover",
    "visibility_km",
    "precipitation_mm",
    "uv_index",
]

TARGET_NAMES = ["Low", "Medium", "High"]


def generate_synthetic_weather_data(samples_per_class: int = 500, random_state: int = RANDOM_STATE):
    """
    Generate synthetic weather observations for 3 distinct risk categories.
    Uses realistic meteorological correlation patterns with controlled Gaussian noise.
    """
    rng = np.random.default_rng(random_state)
    
    # ── CLASS 0: LOW RISK (Clear, dry, calm) ───────────────────────────
    n0 = samples_per_class
    c0_temp = rng.normal(loc=26.0, scale=4.0, size=n0)
    c0_humidity = rng.normal(loc=42.0, scale=8.0, size=n0)
    c0_rainfall = rng.exponential(scale=0.1, size=n0)
    c0_wind = rng.normal(loc=11.0, scale=4.0, size=n0)
    c0_rain_prob = rng.uniform(low=0.0, high=22.0, size=n0)
    c0_clouds = rng.uniform(low=0.0, high=30.0, size=n0)
    c0_visibility = rng.normal(loc=11.0, scale=2.0, size=n0)
    c0_precip = c0_rainfall * rng.uniform(0.8, 1.2, size=n0)
    c0_uv = rng.normal(loc=6.5, scale=1.5, size=n0)
    
    X0 = np.column_stack([
        c0_temp, c0_humidity, c0_rainfall, c0_wind, c0_rain_prob,
        c0_clouds, c0_visibility, c0_precip, c0_uv
    ])
    y0 = np.zeros(n0, dtype=int)
    
    # ── CLASS 1: MEDIUM RISK (Showers, gusty, overcast) ─────────────────
    n1 = samples_per_class
    c1_temp = rng.normal(loc=28.0, scale=4.0, size=n1)
    c1_humidity = rng.normal(loc=74.0, scale=7.0, size=n1)
    c1_rainfall = rng.gamma(shape=3.0, scale=3.5, size=n1)  # ~5-20 mm
    c1_wind = rng.normal(loc=35.0, scale=8.0, size=n1)
    c1_rain_prob = rng.uniform(low=45.0, high=75.0, size=n1)
    c1_clouds = rng.uniform(low=60.0, high=88.0, size=n1)
    c1_visibility = rng.normal(loc=5.5, scale=1.2, size=n1)
    c1_precip = c1_rainfall * rng.uniform(0.9, 1.1, size=n1)
    c1_uv = rng.normal(loc=3.0, scale=1.0, size=n1)
    
    X1 = np.column_stack([
        c1_temp, c1_humidity, c1_rainfall, c1_wind, c1_rain_prob,
        c1_clouds, c1_visibility, c1_precip, c1_uv
    ])
    y1 = np.ones(n1, dtype=int)
    
    # ── CLASS 2: HIGH RISK (Torrential rain, gale winds, severe storm) ──
    n2 = samples_per_class
    c2_temp = rng.normal(loc=30.0, scale=5.0, size=n2)
    c2_humidity = rng.normal(loc=92.0, scale=4.5, size=n2)
    c2_rainfall = rng.gamma(shape=5.0, scale=12.0, size=n2)  # ~40-120 mm
    c2_wind = rng.normal(loc=75.0, scale=12.0, size=n2)
    c2_rain_prob = rng.uniform(low=80.0, high=100.0, size=n2)
    c2_clouds = rng.uniform(low=88.0, high=100.0, size=n2)
    c2_visibility = rng.uniform(low=0.4, high=2.5, size=n2)
    c2_precip = c2_rainfall * rng.uniform(0.95, 1.05, size=n2)
    c2_uv = rng.uniform(low=0.0, high=1.8, size=n2)
    
    X2 = np.column_stack([
        c2_temp, c2_humidity, c2_rainfall, c2_wind, c2_rain_prob,
        c2_clouds, c2_visibility, c2_precip, c2_uv
    ])
    y2 = np.full(n2, fill_value=2, dtype=int)
    
    # Concatenate all rows
    X = np.vstack([X0, X1, X2])
    y = np.concatenate([y0, y1, y2])
    
    # Post-process physical boundary constraints
    X[:, 0] = np.clip(X[:, 0], -10.0, 52.0)  # temp
    X[:, 1] = np.clip(X[:, 1], 10.0, 100.0)  # humidity
    X[:, 2] = np.clip(X[:, 2], 0.0, 300.0)   # rainfall_mm
    X[:, 3] = np.clip(X[:, 3], 0.0, 160.0)   # wind_speed_kmh
    X[:, 4] = np.clip(X[:, 4], 0.0, 100.0)   # rain_probability
    X[:, 5] = np.clip(X[:, 5], 0.0, 100.0)   # cloud_cover
    X[:, 6] = np.clip(X[:, 6], 0.1, 20.0)    # visibility_km
    X[:, 7] = np.clip(X[:, 7], 0.0, 300.0)   # precipitation_mm
    X[:, 8] = np.clip(X[:, 8], 0.0, 14.0)    # uv_index
    
    # Round to 2 decimal places for clean representation
    X = np.round(X, 2)
    
    return X, y


def train_and_save_model(model_save_path: pathlib.Path):
    """
    Generate synthetic data, split into train/test, fit RandomForest,
    print evaluation metrics, and serialize to .pkl using joblib.
    """
    print("=" * 60)
    print("1. Generating synthetic training data (1,500 samples)...")
    X, y = generate_synthetic_weather_data(samples_per_class=500, random_state=RANDOM_STATE)
    print(f"   Generated dataset shape: X={X.shape}, y={y.shape}")
    print(f"   Class distribution: Low(0)={np.sum(y == 0)}, Medium(1)={np.sum(y == 1)}, High(2)={np.sum(y == 2)}")
    
    print("\n2. Splitting dataset into train (80%) and test (20%)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
    )
    print(f"   Training set: {X_train.shape[0]} samples | Testing set: {X_test.shape[0]} samples")
    
    print("\n3. Training RandomForestClassifier...")
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)
    
    print("\n4. Evaluating model on unseen test set...")
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"   Accuracy Score: {acc * 100:.2f}%")
    print("\n   Classification Report:")
    print(classification_report(y_test, y_pred, target_names=TARGET_NAMES))
    
    # Ensure target directory exists
    model_save_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"5. Saving trained model artifact to:\n   {model_save_path}")
    joblib.dump(clf, model_save_path)
    print(f"   Saved artifact size: {os.path.getsize(model_save_path):,} bytes")
    
    print("\n6. Verifying model re-loading and sample inference...")
    loaded_model = joblib.load(model_save_path)
    
    # Test 3 benchmark vectors
    sample_low = np.array([[25.0, 40.0, 0.0, 10.0, 5.0, 15.0, 12.0, 0.0, 7.0]])
    sample_med = np.array([[28.0, 75.0, 8.0, 35.0, 60.0, 75.0, 5.0, 8.0, 3.0]])
    sample_high = np.array([[31.0, 95.0, 55.0, 80.0, 95.0, 95.0, 1.0, 55.0, 0.5]])
    
    pred_low = loaded_model.predict(sample_low)[0]
    pred_med = loaded_model.predict(sample_med)[0]
    pred_high = loaded_model.predict(sample_high)[0]
    
    print(f"   Sample Low input  -> Predicted Class {pred_low} ({TARGET_NAMES[pred_low]})")
    print(f"   Sample Med input  -> Predicted Class {pred_med} ({TARGET_NAMES[pred_med]})")
    print(f"   Sample High input -> Predicted Class {pred_high} ({TARGET_NAMES[pred_high]})")
    
    assert pred_low == 0, f"Expected 0, got {pred_low}"
    assert pred_med == 1, f"Expected 1, got {pred_med}"
    assert pred_high == 2, f"Expected 2, got {pred_high}"
    print("\n[SUCCESS] Model verified and ready for /api/predict inference!")
    print("=" * 60)
    return clf


if __name__ == "__main__":
    target_dir = pathlib.Path(__file__).parent
    target_file = target_dir / "weather_risk_model.pkl"
    train_and_save_model(target_file)
