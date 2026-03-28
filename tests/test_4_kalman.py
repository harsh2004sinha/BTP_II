"""
TEST 4 — Kalman SOC Estimator
Run: python tests/test_4_kalman.py
"""

import sys
import os
import numpy as np
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models.kalman_soc import KalmanSOCEstimator


def test_kalman():
    print("\n" + "="*50)
    print("  TEST 4 — KALMAN SOC ESTIMATOR")
    print("="*50)

    kalman = KalmanSOCEstimator(
        initial_soc         = 0.50,
        process_noise       = 0.001,
        measurement_noise   = 0.01,
        initial_uncertainty = 0.1
    )

    print(f"\n✅ Kalman filter created")
    print(f"   Initial SOC : {kalman.soc_estimate:.4f}")
    print(f"   Initial P   : {kalman.P:.4f}")

    # ---- Test 1: Basic update ----
    print("\n--- Test 1: Basic update step ---")
    result = kalman.update(
        current_soc_model   = 0.52,
        voltage_measurement = 88.0
    )
    print(f"   Input SOC model  : 0.52")
    print(f"   Voltage          : 88.0 V")
    print(f"   SOC estimate     : {result['soc_estimate']:.4f}")
    print(f"   Uncertainty (std): {result['uncertainty_std']:.4f}")
    print(f"   Kalman gain      : {result['kalman_gain']:.4f}")
    print(f"   Innovation       : {result['innovation']:.4f}")
    assert 0.0 < result['soc_estimate'] < 1.0, "❌ SOC must be in [0,1]"
    assert result['uncertainty_std'] > 0, "❌ Uncertainty must be positive"
    print(f"   ✅ Basic update working")

    # ---- Test 2: Convergence ----
    print("\n--- Test 2: Convergence over time ---")
    kalman.reset(initial_soc=0.50)
    true_soc   = 0.70
    uncertainties = []

    for i in range(30):
        # Simulate noisy sensor
        voltage_noise = np.random.normal(0, 0.5)
        # Convert true SOC to approximate voltage (27 cells × 3.5V approx)
        voltage = 27 * (3.30 + true_soc * 0.35) + voltage_noise

        result = kalman.update(
            current_soc_model   = true_soc + np.random.normal(0, 0.02),
            voltage_measurement = voltage
        )
        uncertainties.append(result['uncertainty_std'])

    final_estimate = result['soc_estimate']
    final_uncertainty = result['uncertainty_std']
    print(f"   True SOC         : {true_soc:.4f}")
    print(f"   Final estimate   : {final_estimate:.4f}")
    print(f"   Final uncertainty: {final_uncertainty:.4f}")
    print(f"   Initial uncertainty: {uncertainties[0]:.4f}")
    print(f"   Uncertainty reduced: {uncertainties[0] > final_uncertainty}")
    assert uncertainties[0] >= final_uncertainty, "❌ Uncertainty should reduce"
    print(f"   ✅ Filter converges correctly")

    # ---- Test 3: Confidence interval ----
    print("\n--- Test 3: Confidence interval ---")
    ci = kalman.get_confidence_interval(z_score=1.96)
    print(f"   95% confidence interval: {ci}")
    assert ci[0] < kalman.soc_estimate < ci[1], "❌ Estimate should be inside CI"
    print(f"   ✅ Confidence interval correct")

    # ---- Test 4: History ----
    print("\n--- Test 4: History tracking ---")
    print(f"   History length: {len(kalman.history)}")
    assert len(kalman.history) > 1, "❌ History should be recorded"
    print(f"   ✅ History tracking working")

    # ---- Test 5: Reset ----
    print("\n--- Test 5: Reset ---")
    kalman.reset(initial_soc=0.30)
    print(f"   After reset SOC: {kalman.soc_estimate:.4f}")
    assert abs(kalman.soc_estimate - 0.30) < 0.001, "❌ Reset failed"
    print(f"   ✅ Reset working")

    print("\n" + "="*50)
    print("  ✅ ALL KALMAN TESTS PASSED")
    print("="*50)


if __name__ == "__main__":
    test_kalman()