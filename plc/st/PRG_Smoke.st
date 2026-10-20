Q_BeaconGreen := I_EStop_OK AND I_Heartbeat;
Q_BeaconRed := NOT I_EStop_OK;

Level_pct := INT_TO_REAL(I_TankLevel_raw) * 100.0 / 32767.0;
Err := 70.0 - Level_pct;
Pump_pct := LIMIT(0.0, 3.0 * Err, 100.0);

Q_PumpSpeed_raw := REAL_TO_INT(Pump_pct * 327.67);