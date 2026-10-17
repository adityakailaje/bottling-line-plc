PROGRAM PRG_Mirror
  VAR
    I_Button AT %IX100.0 : BOOL;
    Q_Lamp AT %QX100.0 : BOOL;
  END_VAR

  Q_Lamp := I_Button;
END_PROGRAM


PROGRAM PRG_Analog
  VAR
    I_TankLevel_raw AT %IW100 : INT;
    Q_PumpSpeed_raw AT %QW100 : INT;
    I_Heartbeat AT %IX101.3 : BOOL;
  END_VAR
  VAR
    Level_pct : REAL;
  END_VAR

  Q_PumpSpeed_raw := I_TankLevel_raw / 2;
  Level_pct := INT_TO_REAL(I_TankLevel_raw) * 100.0 / 32767.0;
END_PROGRAM


CONFIGURATION Config0

  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#50ms,PRIORITY := 0);
    PROGRAM instance0 WITH task0 : PRG_Mirror;
    PROGRAM instance1 WITH task0 : PRG_Analog;
  END_RESOURCE
END_CONFIGURATION
