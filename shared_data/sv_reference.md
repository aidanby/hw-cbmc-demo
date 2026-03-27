# SystemVerilog Assertion Quick Reference

## Running EBMC

```bash
ebmc <file.sv> --bound <N>            # check up to N clock steps
ebmc <file.sv> --bound <N> --module <top>  # specify top module
```

Exit codes: `0` = all PROVED, `10` = at least one REFUTED

## SystemVerilog Assertions (SVA)

### Immediate assertions (combinational, no clock)
```systemverilog
assert final (<condition>);           // check at end of simulation
```

### Concurrent assertions (clocked)
```systemverilog
assert property (@(posedge clk) <property>);
// With label:
p_mycheck: assert property (@(posedge clk) <property>);
```

### Implication operators
```systemverilog
cond |-> result   // overlapping: if cond, then result at SAME cycle
cond |=> result   // non-overlapping: if cond, then result at NEXT cycle
```

### Common temporal operators
```systemverilog
$past(sig)        // value of sig one cycle ago
$past(sig, N)     // value of sig N cycles ago
##1 sig           // sig must be true 1 cycle later
##[1:3] sig       // sig must be true 1 to 3 cycles later
```

### Common patterns
```systemverilog
// Reset clears output
p_reset: assert property (@(posedge clk) reset |=> out == 0);

// Counter increments when not at max
p_inc: assert property (@(posedge clk) !reset && count < MAX
                        |=> count == $past(count) + 1);

// Output stable when enable is low
p_hold: assert property (@(posedge clk) !en |=> out == $past(out));

// FSM never reaches invalid state
p_valid: assert property (@(posedge clk) state inside {S0, S1, S2, S3});
```

## NuSMV / NuXMV

```smv
MODULE main
VAR
  x : 0..15;
ASSIGN
  init(x) := 0;
  next(x) := x + 1;     -- increment each step

LTLSPEC G (x < 16);     -- always less than 16
LTLSPEC G (x >= 0);     -- always non-negative
INVARSPEC x < 16;        -- invariant: always less than 16
```

### NuSMV temporal operators
- `G p` — globally (always)
- `F p` — finally (eventually)
- `X p` — next state
- `p U q` — p until q
- `next(x)` — next value of variable x

## Common bugs and fixes

| Bug | Symptom | Fix |
|-----|---------|-----|
| Wrong reset polarity | Counter doesn't reset when reset=1 | Change `!reset` → `reset` (or vice versa) |
| Off-by-one in wrap | BCD counter wraps at wrong value | Change `count == 15` → `count == 9` |
| Wrong shift direction | Shift goes wrong way | Change `>> 1` → `<< 1` (or vice versa) |
| Missing enable check | Register updates when disabled | Add `if (enable)` guard |
| Wrong FSM transition | State gets stuck | Fix `next_state` assignment for that state |
| Wrong increment step | Counter increments by 2 instead of 1 | Change `+ 2` → `+ 1` |
