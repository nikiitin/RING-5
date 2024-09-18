# ARGS for tests
# 1. CSV path
# 2. Number of variables to select
# 3. Variables to select
# Test case 01 args
args_test_config_abbrev <- c(
  "--args",
  "tests/testthat/mock/sort/output/sort_test_case_config_abbrev.csv",
  "config_description_abbrev",
  "7",
  "CPUtest_BinSfx.htm.fallbacklock_LV_ED_CRcdab_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_FWDW1_D1_EVFwd_maxFwd4_CTV1_Prio_no_prio_FCSabort_Allow_Fwd_no_write_in_flight_Rtry64_Pflt",
  "CPUtest_BinSfx.htm.fallbacklock_LV_ED_CRrl_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_Rtry12_Pflt",
  "CPUtest_BinSfx.htm.fallbacklock_LV_ED_CRrw_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_Rtry6_Pflt",
  "CPUtest_BinSfx.htm.fallbacklock_LV_ED_CRrl_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_FWDWN_DM_EVFwd_maxFwd16_CTV50_Prio_numeric_FCSabort_Allow_Fwd_no_write_in_flight_Rtry32_Pflt",
  "CPUtest_BinSfx.htm.fallbacklock_LV_ED_CRrl_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_FWDnaive_EVFwd_maxFwd8_CTV50_MVAL16_Rtry2_Pflt",
  "CPUtest_BinSfx.htm.powertm_LV_ED_CRrwp_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_Rtry2_Pflt",
  "CPUtest_BinSfx.htm.powertm_LV_ED_CRrlp_RSL0Ev_RSPrec_L0Repl_L1Repl_RldStale_DwnG_FWDWN_DM_EVFwd_maxFwd4_CTV50_Prio_numeric_FCSabort_Allow_Fwd_no_write_in_flight_Rtry1_Pflt")